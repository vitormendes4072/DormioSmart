"""O alinhamento entre os dois punhos é por ID, e o bootstrap é por participante.

Os dois testes aqui cobrem os dois jeitos de errar esta análise:

  1. alinhar por POSIÇÃO em vez de por ID — o ncl010 não tem punho direito,
     então a partir dele as duas listas ficam deslocadas e a comparação passa
     a confrontar participantes diferentes, silenciosamente;
  2. tratar as 53 gravações como independentes — infla o N efetivo e estreita
     o IC, porque os dois punhos de um participante são a mesma noite.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from experimentos._lados import (                                   # noqa: E402
    alinhar_por_sujeito, bootstrap_agregado, bootstrap_pareado_intra_sujeito,
)


def _metricas(sujeitos, valores, metrica="kappa"):
    """O mínimo da forma de `MetricasAgregadas.dict()` que estas funções leem."""
    return {"sujeitos": list(sujeitos),
            "por_sujeito": {metrica: list(map(float, valores))}}


def test_alinha_por_id_e_nao_por_posicao():
    # O 'b' existe só à esquerda — como o ncl010 no Newcastle. Alinhar por
    # posição casaria a=1 com a=1, b=2 com c=3, c=3 com d=4: tudo deslocado.
    esq = _metricas(["a", "b", "c", "d"], [0.1, 0.2, 0.3, 0.4])
    dir_ = _metricas(["a", "c", "d"], [0.15, 0.35, 0.45])

    ve, vd, comuns = alinhar_por_sujeito(esq, dir_, "kappa")
    assert comuns == ["a", "c", "d"], "não descartou o participante sem par"
    np.testing.assert_allclose(ve, [0.1, 0.3, 0.4])
    np.testing.assert_allclose(vd, [0.15, 0.35, 0.45])
    # Se tivesse alinhado por posição, a diferença média seria outra.
    assert abs(float(np.mean(vd - ve)) - 0.05) < 1e-12


def test_nan_de_um_lado_derruba_o_par_inteiro():
    """Especificidade indefinida num lado invalida o PAR, não só aquele lado.

    Manter o outro lado do par transformaria a diferença pareada numa
    comparação entre grupos diferentes para aquele participante.
    """
    esq = _metricas(["a", "b", "c"], [0.1, float("nan"), 0.3])
    dir_ = _metricas(["a", "b", "c"], [0.2, 0.25, 0.35])
    ve, vd, comuns = alinhar_por_sujeito(esq, dir_, "kappa")
    assert comuns == ["a", "c"] and ve.size == vd.size == 2


def test_empilhar_gravacoes_estreita_o_ic_indevidamente():
    """O número errado tem de ser mesmo mais estreito — é o ponto da demonstração.

    Com forte correlação intra-participante entre os dois punhos, empilhar as
    2N gravações finge ter o dobro de informação independente. O IC encolhe
    por volta de 1/√2 sem que nenhuma evidência nova tenha entrado.
    """
    rng = np.random.default_rng(7)
    n = 40
    efeito_do_participante = rng.normal(0.30, 0.18, n)     # variância ENTRE participantes
    esquerdo = efeito_do_participante + rng.normal(0, 0.01, n)
    direito = efeito_do_participante + rng.normal(0, 0.01, n)

    esq = _metricas([f"s{i:02d}" for i in range(n)], esquerdo)
    dir_ = _metricas([f"s{i:02d}" for i in range(n)], direito)

    correto = bootstrap_agregado(esquerdo, seed=1)
    empilhado = bootstrap_agregado(np.concatenate([esquerdo, direito]), seed=1)

    larg_correto = correto["ic95_alto"] - correto["ic95_baixo"]
    larg_empilhado = empilhado["ic95_alto"] - empilhado["ic95_baixo"]
    assert empilhado["n"] == 2 * correto["n"]
    assert larg_empilhado < larg_correto * 0.85, (
        "empilhar não estreitou o IC — o cenário do teste não reproduz o problema")

    # E o pareado intra-participante é MAIS estreito que os dois, porque
    # remove a variância entre participantes em vez de fingir que ela não
    # existe. Estreito pelo motivo certo.
    par = bootstrap_pareado_intra_sujeito(esq, dir_, "kappa", seed=1)
    assert par["n_participantes"] == n
    assert (par["ic95_alto"] - par["ic95_baixo"]) < larg_empilhado
    assert not par["significativo"], "não deveria achar efeito onde não há"


def test_detecta_efeito_de_lado_quando_ele_existe():
    """Contraprova: com um deslocamento real, o pareado tem de acusar."""
    rng = np.random.default_rng(11)
    n = 26
    participante = rng.normal(0.30, 0.18, n)
    esquerdo = participante + 0.05 + rng.normal(0, 0.02, n)
    direito = participante + rng.normal(0, 0.02, n)

    par = bootstrap_pareado_intra_sujeito(
        _metricas([f"s{i:02d}" for i in range(n)], esquerdo),
        _metricas([f"s{i:02d}" for i in range(n)], direito),
        "kappa", seed=1)
    assert par["significativo"] and par["ic95_baixo"] > 0
    assert abs(par["delta_medio"] - 0.05) < 0.02
