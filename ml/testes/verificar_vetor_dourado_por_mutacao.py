#!/usr/bin/env python3
"""Verificação por mutação do vetor dourado (DATA-07c).

── POR QUE ISTO EXISTE ──────────────────────────────────────────────────

Um teste de paridade que nunca reprovou não provou nada. É perfeitamente
possível escrever um vetor dourado que passa sobre features erradas — basta a
referência ter o mesmo defeito que a implementação, ou a tolerância ser larga
demais, ou o arquivo dourado se regravar sozinho a cada execução (o que ele
**fazia**: `test_gravar_vetor_dourado` gravava e conferia que o arquivo
existia, o que nunca falha). O resultado é o pior possível: o relatório verde
que se queria ver, sem a garantia que ele afirma.

Este script sabota a implementação de propósito, de um jeito por vez, e confere
que a suíte ACUSA cada sabotagem. É o mesmo instrumento que
`web-app/tests/rls/verificar_por_mutacao.py` aplica ao RLS, pela mesma razão.

Rodar depois de toda mudança em `src/features.py`, na geradora de casos ou nas
tolerâncias. O custo é de dezenas de segundos.

── O QUE CADA SABOTAGEM REPRESENTA ──────────────────────────────────────

As quatro classes que o `DATA-07c` pediu, mais as que apareceram ao escrever:

  erro de sinal ............ sinal_no_produto_interno, d_angulo_vizinho_errado
  ordem de operações ....... ordem_normaliza_antes_de_promediar
  condição de borda ........ borda_primeira_epoca, clip_removido
  filtro sem inicialização . filtro_liga_do_zero
  estimador trocado ........ mediana_por_componente, g_ref_so_do_comeco
  unidade .................. radianos_em_vez_de_graus
  regressão já vivida ...... mag_din_volta_para_l1, enmo_sem_retificador

── USO ──────────────────────────────────────────────────────────────────

    cd ml
    python testes/verificar_vetor_dourado_por_mutacao.py

    # um só, para investigar
    python testes/verificar_vetor_dourado_por_mutacao.py --apenas clip_removido

A sabotagem é aplicada por substituição textual numa CÓPIA da árvore, em /tmp.
O repositório não é tocado.
"""
import argparse
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

AQUI = pathlib.Path(__file__).resolve().parent
ML = AQUI.parent

FEATURES = pathlib.Path("src/features.py")
DOURADO = pathlib.Path("testes/test_vetor_dourado.py")
CASOS = pathlib.Path("testes/dourado_casos.py")

# ---------------------------------------------------------------------
# Os sabotadores.
#
# `de`/`para` é uma substituição textual — tem de casar EXATAMENTE uma vez, e o
# script confere isso. Uma sabotagem que não aplicou é um sabotador quebrado,
# não uma suíte que não acusa: a distinção custou um diagnóstico errado na
# suíte de RLS e está tratada aqui desde o começo.
#
# `minimo` é quantos testes devem cair, no mínimo — não o número exato, senão
# acrescentar teste novo quebraria este script por motivo errado. O que importa
# é que NÃO seja zero, e que o teste NOMEADO em `exige` esteja entre os que
# caem, para que a suíte não acuse por acidente.
# ---------------------------------------------------------------------
SABOTADORES = {
    # --- erro de sinal ------------------------------------------------
    "sinal_no_produto_interno": dict(
        descricao="arccos(-g·g') em vez de arccos(g·g') — ângulo complementar",
        arquivo=FEATURES,
        de='    c = np.clip(np.sum(u * v, axis=-1), -1.0, 1.0)',
        para='    c = np.clip(-np.sum(u * v, axis=-1), -1.0, 1.0)',
        minimo=3,
        exige="test_deriva_lenta_separa_as_duas_features",
    ),
    "d_angulo_vizinho_errado": dict(
        descricao="d_angulo compara com a época SEGUINTE, não com a anterior",
        arquivo=FEATURES,
        de="""    d = np.zeros(u.shape[0], dtype=float)
    if u.shape[0] > 1:
        d[1:] = _angulo_entre(u[1:], u[:-1])""",
        para="""    d = np.zeros(u.shape[0], dtype=float)
    if u.shape[0] > 1:
        d[:-1] = _angulo_entre(u[:-1], u[1:])""",
        minimo=2,
        exige="test_primeira_epoca_tem_d_angulo_zero_por_definicao",
    ),
    # --- ordem de operações -------------------------------------------
    "ordem_normaliza_antes_de_promediar": dict(
        descricao="ĝ = média das direções, em vez de direção da média",
        arquivo=FEATURES,
        de="        g_media[i] = grav.mean(axis=0)",
        para="        g_media[i] = unitario(grav).mean(axis=0)",
        minimo=1,
        exige="test_dourado_do_dispositivo_confere_com_o_arquivo",
    ),
    # --- condição de borda --------------------------------------------
    "borda_primeira_epoca": dict(
        descricao="d_angulo[0] recebe a inclinação em vez de 0",
        arquivo=FEATURES,
        de="""    d = np.zeros(u.shape[0], dtype=float)
    if u.shape[0] > 1:
        d[1:] = _angulo_entre(u[1:], u[:-1])
    return inclinacao, d""",
        para="""    d = np.zeros(u.shape[0], dtype=float)
    if u.shape[0] > 1:
        d[1:] = _angulo_entre(u[1:], u[:-1])
    d[0] = inclinacao[0]
    return inclinacao, d""",
        minimo=1,
        exige="test_primeira_epoca_tem_d_angulo_zero_por_definicao",
    ),
    "clip_removido": dict(
        descricao="arccos sem clip — NaN quando dois ĝ são idênticos",
        arquivo=FEATURES,
        de='    c = np.clip(np.sum(u * v, axis=-1), -1.0, 1.0)',
        para='    c = np.sum(u * v, axis=-1)',
        minimo=1,
        # Medido: o produto interno só passa de 1,0 no caso de ÉPOCA ÚNICA do
        # dispositivo (1,0000000000000002). Nas sequências nunca passa, e o caso
        # `uma_epoca` cai exatamente em 1,0 por arredondamento. Por isso o
        # `exige` aponta para um teste que força a condição, e não para um caso
        # que a encontraria por sorte.
        exige="test_angulo_entre_vetores_paralelos_nao_e_nan",
    ),
    # --- filtro sem inicialização em regime ---------------------------
    "filtro_liga_do_zero": dict(
        descricao="biquad do firmware sem inicialização em regime permanente",
        arquivo=DOURADO,
        de="""        x1 = x2 = v[0]
        y1 = y2 = v[0]""",
        para="""        x1 = x2 = 0.0
        y1 = y2 = 0.0""",
        minimo=3,
        # ⚠️ Quem acusa é a paridade INTRA-ÉPOCA, não a de `ĝ`. Medido: o filtro
        # frio move `mag_din_media` em 460 % e move `ĝ` em só 0,0355 grau —
        # dentro da tolerância angular de 0,25. A razão é que `ĝ` é a média de
        # 960 amostras, e uma média abafa um transiente curto no começo da
        # janela; `mag_din_media` sente amostra por amostra.
        # Consequência: a paridade de `ĝ` NÃO cobre inicialização de filtro. As
        # duas verificações não são redundantes, e é por isso que ambas existem.
        exige="test_paridade_python_firmware",
    ),
    # --- estimador trocado --------------------------------------------
    "mediana_por_componente": dict(
        descricao="ĝ_ref por mediana eixo a eixo, em vez da geométrica",
        arquivo=FEATURES,
        de="    u = _unitario(np.asarray(g_epocas, dtype=float))\n    y = u.mean(axis=0)",
        para=("    u = _unitario(np.asarray(g_epocas, dtype=float))\n"
              "    return _unitario(np.median(u, axis=0))\n"
              "    y = u.mean(axis=0)"),
        minimo=1,
        exige="test_sequencias_tambem_sao_invariantes_a_rotacao",
    ),
    "g_ref_so_do_comeco": dict(
        descricao="ĝ_ref estimado só nas 5 primeiras épocas (o acumulador incremental)",
        arquivo=FEATURES,
        de="    u_ref = direcao_referencia(g_epocas)",
        para="    u_ref = direcao_referencia(g_epocas[:5])",
        minimo=1,
        exige="test_dourado_das_sequencias_confere_com_o_arquivo",
    ),
    # --- unidade -------------------------------------------------------
    "radianos_em_vez_de_graus": dict(
        descricao="ângulos devolvidos em radianos",
        arquivo=FEATURES,
        de="    return np.degrees(np.arccos(c))",
        para="    return np.arccos(c)",
        minimo=3,
        exige="test_faixa_de_viradas_cobre_as_faixas_do_estudo_do_buffer",
    ),
    # --- regressões que o projeto já viveu -----------------------------
    "mag_din_volta_para_l1": dict(
        descricao="mag_din_media volta à norma L1 (a SMA clássica)",
        arquivo=FEATURES,
        de="        X[i, 3] = np.linalg.norm(din, axis=1).mean()",
        para="        X[i, 3] = np.abs(din).sum(axis=1).mean()",
        minimo=2,
        exige="test_features_invariantes_a_rotacao",
    ),
    "enmo_sem_retificador": dict(
        descricao="ENMO sem o max(., 0)",
        arquivo=FEATURES,
        de="        enmo = np.maximum(np.linalg.norm(a, axis=1) - 1.0, 0.0)",
        para="        enmo = np.linalg.norm(a, axis=1) - 1.0",
        minimo=2,
        exige="test_paridade_python_firmware",
    ),
    # --- a tolerância como alvo ---------------------------------------
    # Não sabota a fórmula: sabota a RÉGUA. Se afrouxar a tolerância não fizer
    # nenhum teste cair, é porque nada estava conferindo o piso — e a
    # derivação das tolerâncias era decorativa.
    "tolerancia_angular_frouxa": dict(
        descricao="tolerância angular afrouxada para 2 graus (acima da decisão de 1)",
        arquivo=DOURADO,
        de="TOL_ANGULO_GRAUS = 0.25",
        para="TOL_ANGULO_GRAUS = 2.0",
        minimo=1,
        exige="test_as_tolerancias_ainda_cercam_o_piso",
    ),
}

# ---------------------------------------------------------------------
# Pontos cegos CONHECIDOS. Entram aqui em vez de serem omitidos: um
# instrumento honesto declara o que não pega. Estes são verificados ao
# contrário — se algum passar a ser detectado, o script avisa, porque aí o
# registro abaixo ficou desatualizado.
# ---------------------------------------------------------------------
PONTOS_CEGOS = {
    "p_frac_limiar_inclusivo": dict(
        descricao="p_frac usa >= em vez de > no limiar",
        arquivo=FEATURES,
        de="np.linalg.norm(din, axis=1) > limiar_p_frac_g",
        para="np.linalg.norm(din, axis=1) >= limiar_p_frac_g",
        porque=("a diferença só aparece se alguma amostra cair EXATAMENTE no "
                "limiar, o que em float64 sobre sinal contínuo tem medida zero. "
                "Não é defeito da suíte: é uma distinção que nenhum dado de "
                "teste sintético consegue exercitar. O lado C++ precisa copiar "
                "o `>` do contrato por leitura, não por teste."),
    ),
}


def _aplicar(arvore: pathlib.Path, sab: dict) -> str | None:
    """Aplica a substituição. Devolve mensagem de erro, ou None se deu certo."""
    alvo = arvore / sab["arquivo"]
    texto = alvo.read_text(encoding="utf-8")
    ocorrencias = texto.count(sab["de"])
    if ocorrencias != 1:
        return (f"SABOTADOR QUEBRADO: o trecho casou {ocorrencias} vezes em "
                f"{sab['arquivo']} (esperado exatamente 1). O codigo mudou "
                f"debaixo do sabotador — conserte o sabotador, nao a suite.")
    alvo.write_text(texto.replace(sab["de"], sab["para"]), encoding="utf-8")
    return None


def _arvore_temporaria(temporario: str) -> pathlib.Path:
    """Copia só o necessário. `ml/dados` tem 52 GB e não pode entrar."""
    arvore = pathlib.Path(temporario) / "ml"
    arvore.mkdir()
    for sub in ("src", "testes"):
        shutil.copytree(
            ML / sub, arvore / sub,
            ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache", "*.pyc"),
        )
    shutil.copy2(ML / "pytest.ini", arvore / "pytest.ini")
    return arvore


def rodar(nome: str, sab: dict, esperar_deteccao: bool = True):
    """Aplica um sabotador numa cópia da árvore e devolve (ok, resumo)."""
    with tempfile.TemporaryDirectory(prefix=f"mut-dourado-{nome}-") as temporario:
        arvore = _arvore_temporaria(temporario)

        erro = _aplicar(arvore, sab)
        if erro:
            return False, erro

        processo = subprocess.run(
            [sys.executable, "-m", "pytest", "testes/test_vetor_dourado.py",
             "-q", "--no-header", "-p", "no:cacheprovider"],
            cwd=arvore,
            env={**os.environ, "DORMIO_REGRAVAR_DOURADO": ""},
            capture_output=True,
            text=True,
        )
        saida = processo.stdout + processo.stderr

        caidos = [
            linha.split("::")[-1].split()[0].split("[")[0]
            for linha in saida.splitlines()
            if linha.startswith("FAILED")
        ]
        erros_de_coleta = [
            linha for linha in saida.splitlines()
            if linha.startswith("ERROR") or "error at setup of" in linha.lower()
        ]
        if erros_de_coleta and not caidos:
            return False, ("SABOTADOR QUEBRADO: a suite nao chegou a rodar. "
                           "Primeira linha: " + erros_de_coleta[0][:160])

        if not esperar_deteccao:
            if caidos:
                return False, (f"PONTO CEGO VIROU DETECTADO ({len(caidos)} testes "
                               f"caíram: {', '.join(sorted(set(caidos))[:4])}). "
                               f"Boa notícia — atualize o registro de PONTOS_CEGOS.")
            return True, "nao detectado, como registrado"

        if not caidos:
            return False, "NENHUM teste caiu — a suite nao acusa esta sabotagem"
        unicos = sorted(set(caidos))
        if len(caidos) < sab["minimo"]:
            return False, (f"caíram {len(caidos)}, esperado >= {sab['minimo']}: "
                           + ", ".join(unicos[:6]))
        exigido = sab.get("exige")
        if exigido and not any(exigido == c for c in caidos):
            return False, (f"{len(caidos)} testes caíram, mas `{exigido}` NAO "
                           f"estava entre eles — a suite pode estar acusando por "
                           f"acidente. Caíram: {', '.join(unicos[:6])}")
        return True, f"{len(caidos)} testes caíram ({len(unicos)} distintos)"


def principal():
    analisador = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    analisador.add_argument("--apenas", help="roda um sabotador só, pelo nome")
    argumentos = analisador.parse_args()

    # Confere primeiro que a suíte passa SEM sabotagem. Sem isso, "todos
    # detectados" poderia significar apenas que tudo já estava quebrado.
    print("Referencia (sem sabotagem): ", end="", flush=True)
    processo = subprocess.run(
        [sys.executable, "-m", "pytest", "testes/test_vetor_dourado.py",
         "-q", "--no-header", "-p", "no:cacheprovider"],
        cwd=ML, env={**os.environ, "DORMIO_REGRAVAR_DOURADO": ""},
        capture_output=True, text=True,
    )
    if processo.returncode != 0:
        print("FALHOU\n")
        print("A suite nao passa nem sem sabotagem. Conserte isso primeiro — "
              "senao os sabotadores nao dizem nada.\n")
        print(processo.stdout[-3000:])
        return 1
    print("passa\n")

    escolhidos = dict(SABOTADORES)
    cegos = dict(PONTOS_CEGOS)
    if argumentos.apenas:
        todos = {**SABOTADORES, **PONTOS_CEGOS}
        if argumentos.apenas not in todos:
            print(f"ERRO: sabotador '{argumentos.apenas}' nao existe. Opcoes:\n  "
                  + "\n  ".join(todos), file=sys.stderr)
            return 2
        escolhidos = ({argumentos.apenas: SABOTADORES[argumentos.apenas]}
                      if argumentos.apenas in SABOTADORES else {})
        cegos = ({argumentos.apenas: PONTOS_CEGOS[argumentos.apenas]}
                 if argumentos.apenas in PONTOS_CEGOS else {})

    falhas = []
    for nome, sab in escolhidos.items():
        print(f"  {nome:38s} ", end="", flush=True)
        ok, resumo = rodar(nome, sab)
        print(("[detectado]     " if ok else "[NAO DETECTADO] ") + resumo)
        if not ok:
            falhas.append((nome, sab["descricao"], resumo))

    if cegos:
        print("\n  pontos cegos registrados (espera-se que NAO sejam detectados):")
        for nome, sab in cegos.items():
            print(f"  {nome:38s} ", end="", flush=True)
            ok, resumo = rodar(nome, sab, esperar_deteccao=False)
            print(("[cego, como registrado] " if ok else "[MUDOU] ") + resumo)
            if not ok:
                falhas.append((nome, sab["descricao"], resumo))

    print()
    if falhas:
        print(f"REGRESSAO: {len(falhas)} sabotagem(ns) com resultado inesperado:\n")
        for nome, descricao, resumo in falhas:
            print(f"  · {nome}: {descricao}\n    {resumo}")
        print("\nIsto vem antes de qualquer outro trabalho: o vetor dourado esta "
              "afirmando uma garantia que ele nao verifica.")
        return 1

    total = len(escolhidos) + len(cegos)
    print(f"OK: {len(escolhidos)} de {len(escolhidos)} sabotagens detectadas; "
          f"{len(cegos)} ponto(s) cego(s) confirmado(s). {total} mutacoes no total.")
    return 0


if __name__ == "__main__":
    raise SystemExit(principal())
