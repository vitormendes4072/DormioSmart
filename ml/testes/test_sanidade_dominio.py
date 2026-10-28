"""Sanidade do domínio: o ENMO de sono separa do de vigília?

Para que serve
--------------
Se as distribuições não se separam minimamente, **o problema está no pipeline,
não no travesseiro** — e é melhor descobrir isso antes de acusar o hardware.

O que este teste NÃO é
----------------------
Não é validação. Roda sobre dado sintético (ver `src/carregar/sintetico.py`),
onde a separação é construída de propósito. Ele verifica que o pipeline
**transporta** a separação que existe na entrada — não que ela exista no
travesseiro real. Quem responde isso é o `VIA-01`, na bancada.
"""

from __future__ import annotations

import numpy as np
import pytest

from src.carregar import carregar
from src.configuracao import carregar_config
from src.features import NOMES_FEATURES


@pytest.fixture(scope="module")
def conj():
    cfg = carregar_config()
    cfg.sintetico = dict(cfg.sintetico)
    cfg.sintetico["n_sujeitos"] = 4        # o suficiente, e rápido
    return carregar("sintetico", cfg)


def test_estrutura_do_conjunto(conj):
    n_janelas = 5                          # contexto ±2
    assert conj.X.shape[1] == len(NOMES_FEATURES) * n_janelas
    assert conj.X.shape[0] == conj.y.shape[0] == conj.id_sujeito.shape[0]
    assert set(np.unique(conj.y).tolist()) <= {0, 1}
    assert not np.isnan(conj.X).any(), "feature com NaN — o pipeline vazou"


def test_prevalencia_realista(conj):
    """A maior parte de uma noite é sono. Se não for, o gerador quebrou — e é
    esta prevalência que torna o baseline trivial tão forte."""
    assert 0.75 < conj.y.mean() < 0.95


def test_enmo_de_sono_menor_que_de_vigilia(conj):
    """A separação existe e o pipeline a transporta."""
    i = NOMES_FEATURES.index("enmo_media")   # janela central (deslocamento 0)
    enmo = conj.X[:, i]
    sono, vig = enmo[conj.y == 1], enmo[conj.y == 0]
    assert np.median(sono) < np.median(vig), (
        "ENMO mediano do sono não é menor que o da vigília — verifique o "
        "alinhamento rótulo/sinal antes de qualquer outra coisa"
    )
    # Tamanho de efeito (d de Cohen). Modesto de propósito: metade da vigília é
    # vigília QUIETA, que é indistinguível de sono por construção — é o ponto.
    dp = np.sqrt((sono.var() + vig.var()) / 2)
    d = abs(np.mean(vig) - np.mean(sono)) / dp
    assert d > 0.3, f"separação fraca demais (d de Cohen = {d:.2f})"


def test_vigilia_quieta_e_indistinguivel(conj):
    """A propriedade central do domínio, verificada e não assumida.

    A sobreposição entre as distribuições tem de ser GRANDE. Se este teste
    falhar por sobreposição pequena demais, o dado sintético ficou otimista e
    os baselines medidos sobre ele são otimistas junto.
    """
    i = NOMES_FEATURES.index("enmo_media")
    enmo = conj.X[:, i]
    sono, vig = enmo[conj.y == 1], enmo[conj.y == 0]
    p90_sono = np.percentile(sono, 90)
    frac_vig_abaixo = float(np.mean(vig < p90_sono))
    assert frac_vig_abaixo > 0.30, (
        f"só {frac_vig_abaixo:.0%} da vigília cai na faixa do sono — o gerador "
        "está otimista demais em relação ao domínio real"
    )


def test_split_por_sujeito_nao_vaza(conj):
    """Nenhum sujeito aparece nos dois lados. O erro mais comum da área."""
    from src.avaliar import split_por_sujeito
    for s, tr, te in split_por_sujeito(conj.id_sujeito):
        assert not (tr & te).any(), "máscaras de treino e teste se sobrepõem"
        assert set(conj.id_sujeito[tr].tolist()).isdisjoint(
            set(conj.id_sujeito[te].tolist())
        ), f"sujeito {s} vazou entre treino e teste"


def test_baseline_trivial_e_forte(conj):
    """O resultado que protege o trabalho: "sempre dormindo" acerta muito."""
    from src.avaliar import avaliar_epoca
    from src.baseline import sempre_dormindo
    m = avaliar_epoca(conj.y, sempre_dormindo(len(conj)))
    assert m.acuracia > 0.75, "o trivial deveria ser forte — verifique a prevalência"
    assert m.especificidade == 0.0
    assert m.kappa == pytest.approx(0.0, abs=1e-9), (
        "kappa do trivial tem de ser exatamente 0: ele não concorda com nada "
        "além do acaso. É por isso que kappa é a métrica que ele não infla."
    )
