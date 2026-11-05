"""Confere as evidências publicadas da investigação ML-16 sem treinar."""
import argparse
import json
from pathlib import Path
import sys

ML = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ML))
from ferramentas.comparar_reproducao import comparar, hash_texto

PADRAO = ML / 'experimentos/saida/ml16'
HISTORICOS = ML / 'experimentos/saida'
NOMES = {
    'piloto_cabeca': 'ml02_wearanize_cabeca_aec203907e6f_20260914T222839Z.json',
    'piloto_pulso': 'ml02_wearanize_pulso_aec203907e6f_20260914T222928Z.json',
    'sint_11a': 'ml02_sintetico_aec203907e6f_20260911T022308Z.json',
    'sint_11b': 'ml02_sintetico_aec203907e6f_20260911T022721Z.json',
    'sint_14a': 'ml02_sintetico_aec203907e6f_20260914T033035Z.json',
    'sint_14b': 'ml02_sintetico_aec203907e6f_20260914T040706Z.json',
    'ablacao': 'ml03b_ablacao_aec203907e6f_20260915T223235Z.json',
}


def ler(p):
    return json.loads(p.read_text(encoding='utf-8'))


def escopo_primeiro_sintetico(d, novo=False):
    campos = ('dataset', 'hash_config', 'seed', 'n_epocas', 'n_sujeitos',
              'prevalencia_sono', 'config', 'validacao')
    r = {k: d[k] for k in campos}
    aliases = {'1a_cole_kripke_substituto': '1a_cole_kripke_escala_arbitraria',
               '1b_sadeh_substituto': '1b_sadeh_escala_arbitraria'}
    chaves = ('0_sempre_dormindo', '1a_cole_kripke_substituto', '1b_sadeh_substituto',
              '2_regressao_logistica_loso', '4_logistica_mais_suavizacao')
    r['resultados'] = {k: d['resultados'][aliases.get(k, k) if novo else k] for k in chaves}
    return r


def auditar(pasta=PADRAO, historicos=HISTORICOS):
    casos = []
    def caso(nome, referencia, arquivo, antes, depois, f1_esperados=3, escopo='arquivo completo'):
        dif = comparar(antes, depois)
        f1 = [d for d in dif if '.f1_' in d['caminho']]
        outras = [d for d in dif if '.f1_' not in d['caminho']]
        ok = not outras and len(f1) == f1_esperados and all(
            d.get('antes_nan') and d.get('depois') == 0 for d in f1)
        casos.append({'caso': nome, 'referencia': referencia.name,
                      'referencia_sha256_utf8_lf': hash_texto(referencia),
                      'novo': arquivo.name, 'novo_sha256_utf8_lf': hash_texto(arquivo),
                      'escopo': escopo, 'reproduzido': ok,
                      'diferencas_f1': f1, 'outras_diferencas': outras})

    for nome in ('piloto_cabeca', 'piloto_pulso'):
        ref, novo = historicos / NOMES[nome], pasta / 'resultados' / (nome + '.json')
        caso(nome, ref, novo, ler(ref), ler(novo))
    novo = pasta / 'resultados/sint_legacy.json'
    for nome in ('sint_11a', 'sint_11b'):
        ref = historicos / NOMES[nome]
        a, b = ler(ref), ler(novo)
        if nome == 'sint_11a':
            a, b = escopo_primeiro_sintetico(a), escopo_primeiro_sintetico(b, novo=True)
        caso(nome, ref, novo, a, b, escopo='cinco métodos publicados, com aliases explícitos' if nome == 'sint_11a' else 'arquivo completo')
    novo = pasta / 'resultados/sint_atual.json'
    for nome in ('sint_14a', 'sint_14b'):
        ref = historicos / NOMES[nome]
        caso(nome, ref, novo, ler(ref), ler(novo))
    ref, novo = historicos / NOMES['ablacao'], pasta / 'resultados/sem_scaler_8_threads.json'
    caso('sem_scaler_8_threads', ref, novo, ler(ref)['item2_sem_scaler'],
         ler(novo)['item2_sem_scaler'], f1_esperados=0, escopo='nove células completas do item 2')

    ref = historicos / NOMES['sint_11b']
    controles = []
    for nome in ('sint_so_l1', 'sint_so_mediana'):
        p = pasta / 'resultados' / (nome + '.json')
        dif = [d for d in comparar(ler(ref), ler(p)) if '.f1_' not in d['caminho']]
        controles.append({'controle': nome, 'sha256_utf8_lf': hash_texto(p),
                          'n_diferencas_fora_f1': len(dif), 'nao_reproduz_isoladamente': bool(dif)})

    ctrl = pasta / 'controle_threads.json'
    reduzido = ler(ctrl)
    original = ler(historicos / NOMES['ablacao'])['item2_sem_scaler']
    ml15 = ler(next((historicos / 'ml15/resultados').glob('ml03b_ablacao*.json')))['item2_sem_scaler']
    thread_ok = []
    for r in reduzido:
        esperado = 'historico' if r['threads'] == 8 else 'ml15'
        n = 0
        referencias_validas = True
        for teste, valores in r['testes'].items():
            chave = r['treino'] + '->' + teste
            i = original[chave]['sujeitos'].index(r['sujeito'])
            for metrica, v in valores.items():
                referencias_validas &= v['historico'] == original[chave]['por_sujeito'][metrica][i]
                referencias_validas &= v['ml15'] == ml15[chave]['por_sujeito'][metrica][i]
                n += abs(v['atual'] - v[esperado]) <= 1e-10
        thread_ok.append({'threads': r['threads'], 'treino': r['treino'],
                          'n_metricas_iguais': n, 'n_metricas': 9,
                          'n_iter': r['n_iter'], 'avisos': r['avisos'], 'referencias_validas': referencias_validas})
    sem = ler(novo)
    combinacoes = {(r['threads'], r['treino']) for r in reduzido}
    esperadas = {(t, b) for t in (1, 8) for b in ('cabeca', 'cabeca_e4', 'pulso')}
    return {'item': 'ML-16', 'concluido': all(c['reproduzido'] for c in casos)
            and all(c['nao_reproduz_isoladamente'] for c in controles)
            and len(thread_ok) == 6 and combinacoes == esperadas
            and all(c['n_metricas_iguais'] == 9 and c['referencias_validas']
                    and c['n_iter'] == 300 and c['avisos'] == 1 for c in thread_ok)
            and sem['threads'] == 8 and len(sem['item2_sem_scaler']) == 9
            and all(v['n_sujeitos'] == 92 for v in sem['item2_sem_scaler'].values()),
            'casos': casos, 'controles_features': controles, 'controle_threads': thread_ok,
            'controle_threads_sha256_utf8_lf': hash_texto(ctrl),
            'manifesto_sha256_utf8_lf': hash_texto(pasta / 'manifesto.json'),
            'threads_reexecucao_completa': sem['threads'],
            'n_sujeitos_por_celula': {k: v['n_sujeitos'] for k, v in sem['item2_sem_scaler'].items()}}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--pasta', type=Path, default=PADRAO)
    ap.add_argument('--conferir', action='store_true')
    args = ap.parse_args()
    resultado = auditar(args.pasta)
    if not resultado['concluido']:
        print('DIVERGÊNCIA: a evidência não satisfaz os controles da ML-16')
        return 1
    destino = args.pasta / 'comparacao.json'
    if args.conferir:
        if ler(destino) != resultado:
            print('DIVERGÊNCIA: relatório ou fonte mudou')
            return 1
    else:
        destino.write_text(json.dumps(resultado, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    print('OK — sete comparações históricas e controles da ML-16 conferidos')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
