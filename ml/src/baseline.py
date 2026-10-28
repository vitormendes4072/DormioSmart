"""Baselines do ML-02. Medidos ANTES de qualquer modelo aprendido.

=============================================================================
POR QUE ESTE ARQUIVO VEM PRIMEIRO
=============================================================================
Numa noite de PSG a esmagadora maioria das épocas é sono. O classificador
degenerado **"sempre dormindo"** — que ignora o sensor por completo — já acerta
a fração de sono da noite, tipicamente 85–90%.

Dá para provar isso a partir dos números publicados, sem acesso aos dados:

    acurácia = p·sensibilidade + (1−p)·especificidade
    p = (acurácia − especificidade) / (sensibilidade − especificidade)

  Li et al. (2025), MotionWatch8 : p = 87,8% · publicada 87,3% → −0,5 pt
  Walch et al. (2019), Apple Watch: p = 91,0% · publicada 90,0% → −1,0 pt

Nos dois casos, o classificador que **não olha o sensor** tem acurácia
ligeiramente MAIOR que o método publicado. Dois estudos independentes,
aparelhos e populações diferentes, mesmo resultado.

Se este baseline não for reportado, todos os outros números mentem. Um TCC que
publicar "89% de acurácia" sem ele ao lado publica um número que a banca refuta
em trinta segundos, com uma linha de aritmética.

=============================================================================
DECISÃO TÉCNICA 3 — Cole-Kripke e Sadeh precisam de *counts*, que não temos
=============================================================================
Os dois algoritmos nasceram sobre **activity counts** de Actiwatch: um inteiro
por época produzido pelo firmware proprietário do fabricante, por um algoritmo
não publicado. **Não há função pública que converta aceleração de um MPU6050
(ou de um GENEActiv) em counts de Actiwatch** — é exatamente a armadilha que o
§3 do ML-DATASETS-E-PLANO.md descreve para o MESA.

Como resolvemos, e o que isso custa em honestidade:

  Calculamos um **substituto de contagem** documentado — passa-banda em
  0,25–3 Hz (a faixa a que o Actiwatch responde), retificação e integração por
  época, multiplicado por uma escala arbitrária.

  ⚠️ **Isto NÃO é "Cole-Kripke".** É *"Cole-Kripke aplicado a um substituto de
  contagem derivado de aceleração bruta"*. A diferença importa e deve ir para o
  texto do TCC assim, com estas palavras. Os limiares publicados dos dois
  algoritmos dependem da escala dos counts do fabricante; com outra escala, o
  ponto de operação muda. Por isso a escala é um parâmetro do config, e por
  isso reportamos os dois algoritmos **junto com o trivial**, que não depende
  de escala nenhuma.

  A rota honesta para calibrar a escala, quando houver dado real: ajustar
  `escala_contagem` para que a distribuição do substituto reproduza a
  distribuição de counts publicada numa base que tenha as duas coisas.
  Enquanto isso não existir, **o trivial é o baseline que vale**.

Segunda diferença declarada: Cole-Kripke e Sadeh foram publicados em épocas de
**1 minuto**. Rodamos em **30 s**, porque é a resolução dos rótulos de PSG.
É a mesma escolha do código de referência de Walch et al. (`sleep_classifiers`),
e está declarada aqui em vez de escondida.

Referências dos algoritmos:
  Cole, R. J.; Kripke, D. F.; Gruen, W.; Mullaney, D. J.; Gillin, J. C. (1992).
    *Automatic sleep/wake identification from wrist activity.* Sleep 15(5), 461–469.
  Sadeh, A.; Sharkey, K. M.; Carskadon, M. A. (1994). *Activity-based sleep-wake
    identification.* Sleep 17(3), 201–207.
  ⚠️ Autoria e páginas conferidas na lista de referências de Paquet, Kawinska &
  Carrier (2007) para Cole-Kripke; **abrir os artigos antes de citar no TCC**
  (METODOLOGIA.md: sugestão de busca ≠ citação).
"""

from __future__ import annotations

import numpy as np
from scipy.signal import butter, filtfilt

__all__ = [
    "sempre_dormindo",
    "substituto_de_contagem",
    "cole_kripke",
    "sadeh",
    "fracao_implicada_de_sono",
    "calibrar_escala",
]


def sempre_dormindo(n: int) -> np.ndarray:
    """O baseline degenerado: responde "sono" para tudo. Não olha o sensor."""
    return np.ones(int(n), dtype=int)


def fracao_implicada_de_sono(acuracia: float, sensibilidade: float, especificidade: float) -> float:
    """`p` implicado por um trio publicado — a conta do §0.2.

    É o que permite comparar um artigo com o baseline trivial sem ter os dados
    dele. A identidade é aritmética exata, não aproximação.
    """
    den = sensibilidade - especificidade
    if abs(den) < 1e-12:
        return float("nan")
    return float((acuracia - especificidade) / den)


def substituto_de_contagem(
    a_epocas: np.ndarray,
    fs: float,
    banda_hz: tuple[float, float] = (0.25, 3.0),
    escala: float = 100.0,
) -> np.ndarray:
    """Substituto de *activity count* por época. Ver DECISÃO TÉCNICA 3.

    a_epocas : (n_epocas, n_amostras, 3) em g.
    """
    a_epocas = np.asarray(a_epocas, dtype=float)
    n_ep, n_am, _ = a_epocas.shape
    nyq = fs / 2.0
    lo, hi = banda_hz
    hi = min(hi, 0.99 * nyq)
    b, aa = butter(2, [lo / nyq, hi / nyq], btype="band")

    contagens = np.zeros(n_ep, dtype=float)
    for i in range(n_ep):
        s = np.linalg.norm(a_epocas[i], axis=1)
        s = s - s.mean()
        if s.shape[0] > 3 * max(len(aa), len(b)):
            s = filtfilt(b, aa, s)
        contagens[i] = np.abs(s).mean() * escala
    return contagens


def cole_kripke(contagens: np.ndarray, limiar: float = 1.0) -> np.ndarray:
    """Cole-Kripke (1992) sobre o substituto de contagem. 1 = sono, 0 = vigília.

    Forma e pesos da equação original (versão de 1 min reponderada):
        D = P * (w-4*A-4 + w-3*A-3 + w-2*A-2 + w-1*A-1 + w0*A0 + w+1*A+1 + w+2*A+2)
    D < limiar  ->  sono.
    """
    c = np.asarray(contagens, dtype=float)
    n = c.shape[0]
    P = 0.00001
    pesos = {-4: 404, -3: 598, -2: 326, -1: 441, 0: 1408, 1: 508, 2: 350}
    D = np.zeros(n, dtype=float)
    for d, w in pesos.items():
        idx = np.clip(np.arange(n) - d, 0, n - 1)
        D += w * c[idx]
    D *= P
    return (D < limiar).astype(int)


def sadeh(contagens: np.ndarray, limiar: float = 0.0) -> np.ndarray:
    """Sadeh (1994) sobre o substituto de contagem. 1 = sono, 0 = vigília.

        PS = 7.601 − 0.065*MEAN_W5 − 1.08*NAT − 0.056*SD_LAST6 − 0.703*LOG_ACT
    PS > limiar -> sono.

    Vetorizado: a versão com laço em Python tornava a calibração da DECISÃO 4
    (busca em grade × dobras × algoritmos) inviável em tempo.
    """
    c = np.asarray(contagens, dtype=float)
    n = c.shape[0]
    if n == 0:
        return np.zeros(0, dtype=int)

    def _janelas(x, antes, depois):
        ext = np.pad(x, (antes, depois), mode="edge")
        return np.lib.stride_tricks.sliding_window_view(ext, antes + depois + 1)

    jan11 = _janelas(c, 5, 5)            # centrada, 11 épocas
    jan6 = _janelas(c, 5, 0)             # só passado, 6 épocas

    media_w5 = jan11.mean(axis=1)
    nat = ((jan11 >= 50) & (jan11 < 100)).sum(axis=1).astype(float)
    sd6 = jan6.std(axis=1)
    log_act = np.log1p(c)

    ps = 7.601 - 0.065 * media_w5 - 1.08 * nat - 0.056 * sd6 - 0.703 * log_act
    return (ps > limiar).astype(int)


# =============================================================================
# DECISÃO TÉCNICA 4 — a escala do substituto tem de ser calibrada, e só no treino
# =============================================================================
# Rodando com uma escala arbitrária, Cole-Kripke e Sadeh **degeneram para
# "sempre dormindo"**: acurácia 87,3%, especificidade 0,0%, kappa 0,000.
# Isso não é falha dos algoritmos — é a consequência direta da DECISÃO TÉCNICA 3.
# Os limiares publicados foram ajustados à escala de counts do Actiwatch, e o
# nosso substituto sai ~2 ordens de grandeza abaixo dela.
#
# Deixar assim seria um baseline inútil (e enganoso: pareceria que os algoritmos
# clássicos "não funcionam"). Fingir uma escala seria pior. A saída honesta é
# **calibrar um único parâmetro**, e calibrá-lo onde é legítimo:
#
#   - um parâmetro só: o fator de escala;
#   - ajustado **exclusivamente nos sujeitos de treino** de cada dobra;
#   - o sujeito de teste nunca participa da calibração;
#   - os limiares dos algoritmos ficam nos valores PUBLICADOS, intocados.
#
# Assim o baseline é real e o split continua limpo. O experimento reporta as
# duas versões — a degenerada e a calibrada — porque a degeneração é, ela
# própria, evidência de que counts proprietários não se reproduzem a partir de
# aceleração bruta. É o argumento do §3 do ML-DATASETS-E-PLANO.md, demonstrado.
# =============================================================================

def calibrar_escala(
    contagens_treino: np.ndarray,
    y_treino: np.ndarray,
    algoritmo,
    escalas=None,
) -> float:
    """Fator de escala que maximiza o kappa no TREINO. Um parâmetro, só.

    `algoritmo` é `cole_kripke` ou `sadeh`.
    """
    from .avaliar import avaliar_epoca

    if escalas is None:
        escalas = np.logspace(0, 4, 41)  # 1 a 10 000
    c = np.asarray(contagens_treino, dtype=float)
    y = np.asarray(y_treino, dtype=int)

    melhor_k, melhor_e = -np.inf, 1.0
    for e in escalas:
        k = avaliar_epoca(y, algoritmo(c * e)).kappa
        if np.isfinite(k) and k > melhor_k:
            melhor_k, melhor_e = k, float(e)
    return melhor_e
