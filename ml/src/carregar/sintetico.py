"""Gerador sintético com a MESMA estrutura de uma gravação real.

=============================================================================
PARA QUE SERVE — e para que NÃO serve
=============================================================================
Serve para **exercitar o pipeline** quando o Newcastle não está em disco:
reamostragem, janelamento, features, split por sujeito, baselines, métricas.
Se o código roda daqui até o fim, ele roda no dado real trocando o carregador.

**NÃO serve como resultado.** Nenhum número produzido sobre dado sintético é
achado científico, e nada daqui vai para o TCC como medição. Os experimentos
marcam a origem no log de métricas exatamente para que isso não se confunda.

=============================================================================
COMO O SINAL É CONSTRUÍDO — e por que assim
=============================================================================
O gerador não tenta ser "realista" no sentido cosmético. Ele reproduz **a
propriedade do domínio que decide o desempenho**: uma fração grande da vigília
é **vigília quieta** — pessoa deitada, imóvel, acordada — que é *fisicamente
indistinguível* de sono para um acelerômetro (§0.3 do ML-DATASETS-E-PLANO.md).

É isso que faz a especificidade da actigrafia ficar entre 33% e 80% em toda a
literatura. Um gerador que ignorasse isso produziria um pipeline que "funciona"
maravilhosamente e mentiria sobre o problema.

Cada gravação recebe uma **orientação de montagem aleatória** (rotação fixa do
referencial do sensor). Isso é de propósito: é o teste de que as features são
mesmo invariantes à orientação. Se alguma não for, aparece como variância entre
sujeitos que não deveria existir.
"""

from __future__ import annotations

import numpy as np

from .base import Gravacao

__all__ = ["gerar_sinteticos"]


def _rotacao_aleatoria(rng: np.random.Generator) -> np.ndarray:
    """Matriz de rotação 3x3 uniforme (via QR de uma matriz gaussiana)."""
    q, r = np.linalg.qr(rng.normal(size=(3, 3)))
    q = q @ np.diag(np.sign(np.diag(r)))
    if np.linalg.det(q) < 0:
        q[:, 0] *= -1
    return q


def gerar_sinteticos(
    n_sujeitos: int,
    horas_por_noite: float,
    taxa_origem_hz: float,
    fracao_sono: float,
    fracao_vigilia_quieta: float,
    ruido_mg: float,
    epoca_s: float,
    seed: int,
) -> list[Gravacao]:
    rng = np.random.default_rng(seed)
    n_epocas = int(round(horas_por_noite * 3600.0 / epoca_s))
    n_por_epoca = int(round(epoca_s * taxa_origem_hz))
    sigma = ruido_mg / 1000.0

    gravacoes: list[Gravacao] = []
    for s in range(n_sujeitos):
        # --- rótulos: um bloco de sono com despertares ---------------------
        y = np.ones(n_epocas, dtype=int)
        n_vig = int(round((1.0 - fracao_sono) * n_epocas))
        # Vigília concentrada nas pontas (adormecer/acordar) + despertares no meio
        n_ponta = max(1, int(n_vig * 0.6))
        y[:n_ponta // 2] = 0
        y[-(n_ponta - n_ponta // 2):] = 0
        restante = n_vig - n_ponta
        while restante > 0:
            dur = int(rng.integers(1, 6))
            ini = int(rng.integers(n_ponta, n_epocas - n_ponta - dur))
            dur = min(dur, restante)
            y[ini:ini + dur] = 0
            restante -= dur

        # --- quais épocas de vigília são "vigília quieta" -------------------
        idx_vig = np.flatnonzero(y == 0)
        quietas = rng.random(idx_vig.size) < fracao_vigilia_quieta
        eh_quieta = np.zeros(n_epocas, dtype=bool)
        eh_quieta[idx_vig[quietas]] = True

        # --- amplitude de movimento por época ------------------------------
        # sono: baixa, com picos ocasionais (viradas)
        # vigília ativa: alta
        # vigília quieta: BAIXA — igual a sono. É o ponto.
        amp = np.where(y == 1, rng.gamma(1.5, 0.010, n_epocas), rng.gamma(3.0, 0.045, n_epocas))
        amp[eh_quieta] = rng.gamma(1.5, 0.010, int(eh_quieta.sum()))
        viradas = rng.random(n_epocas) < 0.04
        amp[viradas] += rng.gamma(2.0, 0.06, int(viradas.sum()))

        # --- orientação de montagem, fixa por gravação ---------------------
        R = _rotacao_aleatoria(rng)
        g_atual = R @ np.array([0.0, 0.0, 1.0])

        n_total = n_epocas * n_por_epoca
        t = np.arange(n_total, dtype=float) / taxa_origem_hz
        a = np.empty((n_total, 3), dtype=float)

        for i in range(n_epocas):
            fatia = slice(i * n_por_epoca, (i + 1) * n_por_epoca)
            # virada de postura: gira o vetor gravidade
            if viradas[i]:
                eixo = rng.normal(size=3)
                eixo /= np.linalg.norm(eixo)
                ang = np.radians(rng.uniform(15, 60))
                K = np.array([[0, -eixo[2], eixo[1]],
                              [eixo[2], 0, -eixo[0]],
                              [-eixo[1], eixo[0], 0]])
                Rv = np.eye(3) + np.sin(ang) * K + (1 - np.cos(ang)) * (K @ K)
                g_atual = Rv @ g_atual
            # movimento: banda 0,3–3,5 Hz (faixa dominante do movimento humano)
            tt = np.arange(n_por_epoca) / taxa_origem_hz
            mov = np.zeros((n_por_epoca, 3))
            for _ in range(3):
                f = rng.uniform(0.3, 3.5)
                fase = rng.uniform(0, 2 * np.pi)
                dir_ = rng.normal(size=3)
                dir_ /= np.linalg.norm(dir_)
                mov += np.outer(np.sin(2 * np.pi * f * tt + fase), dir_)
            mov *= amp[i] / 3.0
            a[fatia] = g_atual + mov + rng.normal(0.0, sigma, (n_por_epoca, 3))

        gravacoes.append(
            Gravacao(
                id_sujeito=f"sin{s:03d}",
                t=t,
                a=a,
                rotulos=y,
                t0_rotulo=0.0,
                epoca_rotulo_s=epoca_s,
                meta={
                    "fonte": "sintetico",
                    "AVISO": "dado sintético — não é medição, não é achado",
                    "taxa_origem_hz": taxa_origem_hz,
                    "fracao_vigilia_quieta": fracao_vigilia_quieta,
                },
            )
        )
    return gravacoes
