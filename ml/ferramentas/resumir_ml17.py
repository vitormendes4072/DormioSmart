"""Exporta somente resumos/evidências derivadas, sem caminhos locais ou IDs."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ML = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ML))

from ferramentas import rodar_ml17  # noqa: E402
from ferramentas.comparar_ml17 import comparar_rodada, carregar_f1, comparar_celula, efeitos  # noqa: E402
from ferramentas.conferir_predicoes_ml17 import conferir as conferir_predicoes, conferir_repeticao  # noqa: E402


ARQUIVOS = ('comparacao.json', 'f1_complementar.json', 'efeitos.json', 'censo.json',
            'lados_intra_sujeito.json', 'verificacao_predicoes.json')
CAMPOS_DELTA = ('n_total', 'n_pares', 'n_invalidos_antes', 'n_invalidos_depois',
                'media', 'desvio', 'minimo', 'maximo', 'max_abs', 'ic95')


def delta_publico(d):
    return {k: d[k] for k in CAMPOS_DELTA}


def comparacao_publica(dados):
    return {celula: {met: dict(antes=d['antes'], depois=d['depois'],
                    resumo_antes={k: d['resumo_antes'][k] for k in ('desvio', 'n_valido', 'ic95')},
                    resumo_depois={k: d['resumo_depois'][k] for k in ('desvio', 'n_valido', 'ic95')},
                    delta=delta_publico(d['delta']))
                    for met, d in metricas.items()} for celula, metricas in dados.items()}


def conferir_evidencia(pasta, cache=None, censo=None):
    """Caminhos explícitos após realocação; manifesto original permanece intacto."""
    if (cache is None) != (censo is None):
        raise ValueError('realocação exige --cache e --censo juntos')
    if cache is None:
        return rodar_ml17.conferir(pasta)
    m = json.loads((pasta / 'manifesto.json').read_text(encoding='utf-8'))
    executor = Path(rodar_ml17.__file__).read_bytes()
    hashes_executor = {hashlib.sha256(executor).hexdigest(),
                       hashlib.sha256(executor.replace(b'\r\n', b'\n')).hexdigest()}
    if rodar_ml17.sha(censo) != m['censo_sha256'] or m['executor_sha256'] not in hashes_executor:
        raise ValueError('censo/executor mudou depois do congelamento')
    for nome, entrada in m['fontes'].items():
        for arq, digest in entrada['arquivos'].items():
            if rodar_ml17.sha(pasta / nome / arq) != digest:
                raise ValueError('fonte da execução mudou: ' + arq)
    for arq, digest in m['cache_sha256'].items():
        if rodar_ml17.sha(cache / arq) != digest:
            raise ValueError('cache da execução mudou: ' + arq)
    return dict(m, cache=str(cache), censo=str(censo))


def validar_sem_notas(dados, chave=''):
    """Protege o limite de publicação; não demonstra anonimato dos dados de origem."""
    proibidos = {'por_participante', 'por_sujeito', 'por_sujeito_sem_ids', 'sujeitos',
                 'ids', 'indice_max_abs', 'sujeito_mais_discrepante', 'filepath'}
    if isinstance(dados, dict):
        for k, v in dados.items():
            if k in proibidos:
                raise ValueError('campo individual/privado na publicação: ' + k)
            validar_sem_notas(v, k)
    elif isinstance(dados, list):
        if chave != 'ic95' and any(isinstance(v, (int, float)) or v is None for v in dados):
            raise ValueError('vetor numérico fora de IC agregado: ' + chave)
        for v in dados:
            validar_sem_notas(v, chave)


def ambiente_publico(estado):
    campos = ('user_api', 'internal_api', 'num_threads', 'prefix', 'version',
              'threading_layer', 'architecture')
    pools = [{k: p[k] for k in campos if k in p} for p in estado['pools']]
    pools.sort(key=lambda p: json.dumps(p, sort_keys=True))
    return dict(python=estado['python'], bibliotecas=estado['bibliotecas'], pools=pools)


def exportar(pasta, saida, executor_ref, cache=None, censo=None):
    m = conferir_evidencia(pasta, cache, censo)
    executor_ref = subprocess.check_output(['git', 'rev-parse', executor_ref], text=True).strip()
    arquivo = subprocess.check_output(['git', 'show', f'{executor_ref}:ml/ferramentas/rodar_ml17.py'])
    normalizado = lambda b: hashlib.sha256(b.replace(b'\r\n', b'\n')).hexdigest()
    executor_lf = normalizado((ML / 'ferramentas/rodar_ml17.py').read_bytes())
    if normalizado(arquivo) != executor_lf:
        raise ValueError('commit do executor não corresponde ao que rodou')
    saida.mkdir(parents=True, exist_ok=True)
    def gravar(nome, d):
        validar_sem_notas(d)
        (saida / nome).write_text(json.dumps(d, indent=2, allow_nan=False) + '\n', encoding='utf-8', newline='\n')
    gravar('comparacao.json', comparacao_publica(comparar_rodada(pasta)))
    a, b = (carregar_f1(pasta, v) for v in ('antes', 'depois'))
    gravar('f1_complementar.json', comparacao_publica({k: comparar_celula(a[k], b[k]) for k in a}))
    gravar('efeitos.json', {v: {k: {met: delta_publico(d) for met, d in linha.items()}
                              for k, linha in celulas.items()} for v, celulas in efeitos(pasta).items()})
    censo = json.loads(Path(m['censo']).read_text(encoding='utf-8'))
    resumo_censo = {}
    for nome, linhas in censo.items():
        resumo_censo[nome] = []
        for v in linhas:
            resumo = {k: valor for k, valor in v.items() if k != 'por_sujeito_sem_ids'}
            resumo['maior_fracao_por_participante'] = max(
                p['vetor_alterado'] / p['n_epocas'] for p in v['por_sujeito_sem_ids'])
            resumo_censo[nome].append(resumo)
    gravar('censo.json', resumo_censo)
    lados = {}
    for versao in ('antes', 'depois'):
        r = json.loads((pasta / versao / 'ml/experimentos/saida/ml17_rodada/lados.json').read_text(encoding='utf-8'))
        lados[versao] = {}
        for braco, configs in r['resultados'].items():
            for config, dados in configs.items():
                lados[versao][braco + '/' + config] = {
                    tipo: {met: {k: v for k, v in info.items() if k != 'sujeito_mais_discrepante'}
                           for met, info in dados[tipo].items()}
                    for tipo in ('c_efeito_do_lado_intra_sujeito', 'd_INCORRETO_empilhado')}
    gravar('lados_intra_sujeito.json', lados)
    verificacao = conferir_predicoes(pasta)
    verificacao['controle_repeticao_newcastle'] = conferir_repeticao(pasta)
    gravar('verificacao_predicoes.json', verificacao)
    estados, ambientes = {}, []
    for versao in ('antes', 'depois'):
        for grupo in ('newcastle', 'walch_principal', 'walch_todos', 'lados', 'otimizacoes'):
            e = json.loads((pasta / f'{versao}_{grupo}.json').read_text(encoding='utf-8'))
            ambientes.append(ambiente_publico(e))
            estados[versao + '/' + grupo] = {
                k: e[k] for k in ('status', 'segundos', 'utc_inicio', 'utc_fim', 'codigo',
                                 'hash_entradas', 'n_avisos', 'n_capturas', 'avisos_por_tipo')}
    fontes_analise = ('censo_contexto_ml17.py', 'comparar_ml17.py', 'conferir_predicoes_ml17.py',
                      'resumir_ml17.py', 'auditar_resumos_ml17.py')
    if any(a != ambientes[0] for a in ambientes):
        raise ValueError('ambientes das execuções diferem')
    analise_commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
    hashes = {}
    for n in fontes_analise:
        hashes[n] = normalizado((ML / 'ferramentas' / n).read_bytes())
        blob = subprocess.check_output(['git', 'show', f'{analise_commit}:ml/ferramentas/{n}'])
        if normalizado(blob) != hashes[n]:
            raise ValueError('commit de análise não corresponde ao fonte: ' + n)
    manifesto = dict(codigo={v: r['commit'] for v, r in m['fontes'].items()},
                     fontes_git=m['fontes'], executor_commit=executor_ref,
                     executor_sha256=m['executor_sha256'], executor_sha256_utf8_lf=executor_lf,
                     analise_commit=analise_commit, censo_integral_local_sha256=m['censo_sha256'],
                     caches_total=len(m['cache_sha256']),
                     caches_agregado_sha256=hashlib.sha256(json.dumps(m['cache_sha256'], sort_keys=True).encode()).hexdigest(),
                     ambiente=ambientes[0], ambientes_identicos=True, execucoes=estados,
                     fontes_analise_sha256_utf8_lf=hashes,
                     arquivos_publicos_sha256_utf8_lf={n: normalizado((saida / n).read_bytes()) for n in ARQUIVOS},
                     atribuicao_wearanize_oa=dict(
                         colecao='https://doi.org/10.34973/xrmf-5726',
                         colecao_primaria='https://doi.org/10.34973/j6jf-9e62',
                         artigo='https://doi.org/10.1093/sleepadvances/zpaf094',
                         licenca_do_pacote='https://creativecommons.org/licenses/by/4.0/',
                         alteracoes='Métricas calculadas pelo projeto; comparação de contexto global e segmentado.',
                         uso='Pesquisa científica, sem tentativa de identificação; créditos completos na coleção.'),
                     privacidade='Somente agregados; notas e índices individuais, predições/rótulos ficam locais.')
    gravar('manifesto.json', manifesto)
    print('Exportadas 69 celulas, F1, efeitos, censo, punhos, verificacao e manifesto.')


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--pasta', type=Path, required=True)
    ap.add_argument('--saida', type=Path, required=True)
    ap.add_argument('--executor-ref', default='11fa375')
    ap.add_argument('--cache', type=Path, help='cache realocado, conferido pelos hashes originais')
    ap.add_argument('--censo', type=Path, help='censo realocado, conferido pelo hash original')
    args = ap.parse_args()
    exportar(args.pasta, args.saida, args.executor_ref, args.cache, args.censo)


if __name__ == '__main__':
    main()
