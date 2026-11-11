"""Contrato dos consumidores reais; as três comparações globais são deliberadas."""
import ast
from collections import Counter
from pathlib import Path

import pytest


ML = Path(__file__).resolve().parents[1]
EXCECOES = {
    ('experimentos/ml12_validacao_aninhada.py', 'preparar',
     'empilhar_contexto(Xn, CONTEXTO)'): 'controle negativo ML-12',
    ('ferramentas/rodada_reproducao.py', 'processar',
     "empilhar_contexto(b['X'][b['id'] == s], cfg.contexto_epocas)"): 'reprodução histórica ML-15',
    ('ferramentas/censo_contexto_ml17.py', 'contar',
     'empilhar_contexto(X, janela)'): 'antes global do censo',
}


def fontes_consumidoras():
    return {p.relative_to(ML).as_posix(): p.read_text(encoding='utf-8-sig')
            for pasta in ('src', 'experimentos', 'ferramentas')
            for p in (ML / pasta).rglob('*.py')}


def chamadas(fonte):
    arvore = ast.parse(fonte)
    pais = {filho: pai for pai in ast.walk(arvore) for filho in ast.iter_child_nodes(pai)}
    nomes = {'empilhar_contexto'} | {
        a.asname or a.name for no in ast.walk(arvore) if isinstance(no, ast.ImportFrom)
        for a in no.names if a.name == 'empilhar_contexto'}
    for no in ast.walk(arvore):
        if not isinstance(no, ast.Call):
            continue
        if not ((isinstance(no.func, ast.Name) and no.func.id in nomes) or
                (isinstance(no.func, ast.Attribute) and no.func.attr == 'empilhar_contexto')):
            continue
        ancestrais = []
        pai = pais.get(no)
        while pai is not None:
            ancestrais.append(pai)
            pai = pais.get(pai)
        funcoes = [a.name for a in ancestrais if isinstance(a, (ast.FunctionDef, ast.AsyncFunctionDef))]
        # A recursão interna da primitiva recebe um único segmento. O contrato
        # abaixo é de todos os consumidores, não da implementação da primitiva.
        if 'empilhar_contexto' in funcoes:
            continue
        yield no, funcoes[0] if funcoes else '', pais.get(no)


def conferir(fontes):
    usadas = Counter()
    erros = []
    for caminho, fonte in fontes.items():
        for no, funcao, pai in chamadas(fonte):
            chave = (caminho, funcao, ast.unparse(no))
            if chave in EXCECOES:
                if caminho.endswith('ml12_validacao_aninhada.py'):
                    assert isinstance(pai, ast.IfExp) and pai.orelse is no
                    assert ast.unparse(pai.test) == 'por_sujeito'
                elif caminho.endswith('censo_contexto_ml17.py'):
                    assert isinstance(pai, ast.Assign) and ast.unparse(pai.targets[0]) == 'antes'
                else:
                    assert isinstance(pai, ast.ListComp) and pai.elt is no
                usadas[chave] += 1
                continue
            kw = next((k for k in no.keywords if k.arg == 'segmentos'), None)
            if kw is None or (isinstance(kw.value, ast.Constant) and kw.value.value is None):
                erros.append(f'{caminho}:{no.lineno}: exige segmentos= explícito e não None')
    assert not erros, '\n'.join(erros)
    # O censo entra só na segunda PR. Nenhuma exceção inteira por arquivo.
    esperadas = {k: 1 for k in EXCECOES if k[0] in fontes}
    assert usadas == esperadas, f'exceções globais alteradas: {usadas!r}'


def test_todos_consumidores_exigem_segmentos():
    conferir(fontes_consumidoras())


@pytest.mark.parametrize('caminho,funcao,quantidade', [
    ('experimentos/ml03b_otimizacoes.py', 'main', 6),
    ('experimentos/ml04_validacao_externa.py', 'lados', 2),
    ('experimentos/ml02_baselines.py', '_processar_unificado', 1),
    ('experimentos/ml11_ablacao_features.py', 'avaliar', 1),
    ('experimentos/quantizacao_features.py', 'avaliar', 1),
])
def test_cada_sabotagem_dos_cinco_consumidores_e_detectada(caminho, funcao, quantidade):
    fontes = fontes_consumidoras()
    alvos = [no.lineno for no, f, _ in chamadas(fontes[caminho]) if f == funcao]
    assert len(alvos) == quantidade
    for linha in alvos:
        for sabotagem in ('omitir', 'None'):
            arvore = ast.parse(fontes[caminho])
            no = next(n for n in ast.walk(arvore) if isinstance(n, ast.Call) and n.lineno == linha
                      and isinstance(n.func, ast.Name) and n.func.id == 'empilhar_contexto'
                      and any(k.arg == 'segmentos' for k in n.keywords))
            if sabotagem == 'omitir':
                no.keywords = [k for k in no.keywords if k.arg != 'segmentos']
            else:
                next(k for k in no.keywords if k.arg == 'segmentos').value = ast.Constant(None)
            mutantes = dict(fontes, **{caminho: ast.unparse(arvore)})
            # Executa a mesma guarda sobre a fonte real alterada, uma chamada
            # de cada vez; nenhuma avaliação ou treino recomposto no teste.
            with pytest.raises(AssertionError, match=caminho + r':\d+: exige segmentos='):
                conferir(mutantes)
