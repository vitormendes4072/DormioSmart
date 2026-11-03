"""Testes do carregador da coorte de Walch et al. (2019) — ML-06.

Como os do Wearanize+, estes testes FABRICAM arquivos no formato real em vez de
ler o dataset (2,2 GB, fora do git): cada armadilha documentada em
`src/carregar/walch.py`, medida nos 31 arquivos em 2026-11-03, tem aqui um caso
que a reproduz.

⚠️ O que estes testes NÃO provam: que o carregador funciona no dado real. Isso
foi conferido à parte, sujeito a sujeito, e está no diário (03/11).
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from src.carregar import processar_gravacoes
from src.carregar.walch import (
    carregar_walch,
    epocas_sem_dado,
    ler_movimento,
    rotulos_binarios,
)
from src.configuracao import carregar_config


def _escrever(pasta: Path, sid: str, t: np.ndarray, codigos: np.ndarray,
              ordem: np.ndarray | None = None) -> None:
    (pasta / "motion").mkdir(parents=True, exist_ok=True)
    (pasta / "labels").mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(int(sid) % 1000)
    a = rng.normal(0.0, 0.02, size=(t.shape[0], 3))
    a[:, 2] -= 1.0
    linhas = np.column_stack([t, a])
    if ordem is not None:
        linhas = linhas[ordem]
    np.savetxt(pasta / "motion" / f"{sid}_acceleration.txt", linhas, fmt="%.7f")
    rot = np.column_stack([np.arange(codigos.shape[0]) * 30, codigos])
    np.savetxt(pasta / "labels" / f"{sid}_labeled_sleep.txt", rot, fmt="%d")


def _grade(ini: float, fim: float, fs: float) -> np.ndarray:
    return np.arange(ini, fim, 1.0 / fs)


# ── ARMADILHA 2: códigos de rótulo ───────────────────────────────────────

def test_n4_e_rem_sao_sono_vigilia_e_zero_e_resto_e_nao_pontuado():
    y = rotulos_binarios(np.array([0, 1, 2, 3, 4, 5, -1, 7]))
    assert y.tolist() == [0, 1, 1, 1, 1, 1, -1, -1]


# ── ARMADILHA 3: tempo fora de ordem e repetido ──────────────────────────

def test_movimento_sai_ordenado_e_sem_tempo_repetido(tmp_path):
    t = np.array([0.0, 0.02, 0.04, 0.04, 0.06])
    ordem = np.array([0, 2, 1, 3, 4])            # fora de ordem, e 0.04 repetido
    _escrever(tmp_path, "1000", t, np.array([0]), ordem=ordem)
    tl, a = ler_movimento(tmp_path / "motion" / "1000_acceleration.txt")
    assert tl.tolist() == [0.0, 0.02, 0.04, 0.06]
    assert a.shape == (4, 3)


# ── ARMADILHA 4: época sem dado ──────────────────────────────────────────

def test_epoca_com_lacuna_maior_que_um_segundo_fica_sem_dado():
    # Lacuna de 2 s em 40–42, e o movimento para aos 100 s.
    t = np.concatenate([_grade(0, 40, 50), _grade(42, 100, 50)])
    sem = epocas_sem_dado(t, 0.0, 4)
    assert sem.tolist() == [False, True, False, True]   # a 4ª (90–120) não tem fim coberto


def test_lacuna_curta_nao_derruba_a_epoca():
    t = np.concatenate([_grade(0, 40, 50), _grade(40.5, 60, 50)])  # 0,5 s
    assert epocas_sem_dado(t, 0.0, 2).tolist() == [False, False]


# ── ARMADILHAS 1, 4 e 5 no carregador inteiro ────────────────────────────

def test_recorta_a_janela_e_marca_as_epocas_sem_dado(tmp_path):
    # Movimento desde −3 dias; para aos 120 s e só volta depois dos rótulos —
    # o caso do 7749105, em miniatura.
    t = np.concatenate([_grade(-259200, -259100, 50), _grade(-100, 120, 50),
                        _grade(400, 500, 50)])
    _escrever(tmp_path, "7749105", t, np.array([0, 2, 4, 5, 2, 0, 2, 2]))
    (g,) = list(carregar_walch(tmp_path))
    assert g.t.min() >= -60.0 and g.t.max() <= 8 * 30 + 60      # MARGEM_S
    assert g.t0_rotulo == 0.0
    assert g.rotulos.tolist() == [0, 1, 1, 1, -1, -1, -1, -1]
    assert g.meta["epocas_sem_dado"] == 4


def test_exclui_sujeito_abaixo_da_taxa_minima(tmp_path):
    _escrever(tmp_path, "5383425", _grade(0, 120, 10), np.array([0, 2, 2, 0]))
    _escrever(tmp_path, "1066528", _grade(0, 120, 50), np.array([0, 2, 2, 0]))
    ids = [g.id_sujeito for g in carregar_walch(tmp_path, taxa_minima_hz=32.0)]
    assert ids == ["1066528"]
    ids_todos = sorted(g.id_sujeito for g in carregar_walch(tmp_path))
    assert ids_todos == ["1066528", "5383425"]


def test_pasta_vazia_diz_onde_baixar(tmp_path):
    with pytest.raises(FileNotFoundError, match="physionet"):
        list(carregar_walch(tmp_path))


# ── O que importa de verdade: nenhuma época inventada chega às features ──

def test_lacuna_longa_nao_vira_epoca_no_conjunto(tmp_path):
    """Sem a máscara, `reamostrar` interpolaria a lacuna e `fatiar_epocas`
    aceitaria as épocas dela: sinal inventado, rótulo verdadeiro."""
    t = np.concatenate([_grade(-60, 300, 50), _grade(900, 1260, 50)])
    codigos = np.array([2] * 40)          # 40 épocas = 1200 s
    _escrever(tmp_path, "1000", t, codigos)
    cfg = carregar_config()
    conj = processar_gravacoes(carregar_walch(tmp_path), cfg)
    # Com dado: 0–300 s (10 épocas) e 900–1200 s (10 épocas). Nada entre elas.
    assert len(conj) == 20
