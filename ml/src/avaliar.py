"""Métricas por época e por noite.

Acurácia sozinha não diz nada aqui, porque a classe é desbalanceada: a maior
parte de uma noite de PSG é sono. Por isso toda saída deste módulo traz
**especificidade** ao lado — é a métrica onde a actigrafia falha, sempre, e é o
teste de honestidade do trabalho.

Convenção: 1 = sono (positivo), 0 = vigília.
  sensibilidade = fração das épocas de SONO identificadas como sono
  especificidade = fração das épocas de VIGÍLIA identificadas como vigília
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np

__all__ = ["Metricas", "avaliar_epoca", "split_por_sujeito"]


@dataclass
class Metricas:
    n: int
    n_sono: int
    n_vigilia: int
    prevalencia_sono: float
    acuracia: float
    sensibilidade: float
    especificidade: float
    kappa: float
    f1_sono: float
    f1_vigilia: float
    vp: int
    vn: int
    fp: int
    fn: int

    def dict(self) -> dict:
        return asdict(self)


def avaliar_epoca(y_verdadeiro: np.ndarray, y_predito: np.ndarray) -> Metricas:
    y = np.asarray(y_verdadeiro, dtype=int)
    p = np.asarray(y_predito, dtype=int)
    if y.shape != p.shape:
        raise ValueError("y e predição com formatos diferentes")

    vp = int(np.count_nonzero((y == 1) & (p == 1)))
    vn = int(np.count_nonzero((y == 0) & (p == 0)))
    fp = int(np.count_nonzero((y == 0) & (p == 1)))
    fn = int(np.count_nonzero((y == 1) & (p == 0)))
    n = vp + vn + fp + fn

    def div(a, b):
        return float(a) / float(b) if b else float("nan")

    acc = div(vp + vn, n)
    sens = div(vp, vp + fn)
    espec = div(vn, vn + fp)

    # Kappa de Cohen — corrige o acaso. É a métrica que a literatura de sono usa
    # para comparar, e é justamente a que o baseline trivial não consegue
    # inflar: "sempre dormindo" tem kappa exatamente 0.
    po = acc
    pe = div((vp + fn) * (vp + fp) + (vn + fp) * (vn + fn), n * n)
    kappa = div(po - pe, 1.0 - pe) if not np.isnan(pe) and abs(1.0 - pe) > 1e-12 else float("nan")

    prec_s, rec_s = div(vp, vp + fp), sens
    f1_s = div(2 * prec_s * rec_s, prec_s + rec_s) if (prec_s + rec_s) else float("nan")
    prec_v, rec_v = div(vn, vn + fn), espec
    f1_v = div(2 * prec_v * rec_v, prec_v + rec_v) if (prec_v + rec_v) else float("nan")

    return Metricas(
        n=n, n_sono=vp + fn, n_vigilia=vn + fp,
        prevalencia_sono=div(vp + fn, n),
        acuracia=acc, sensibilidade=sens, especificidade=espec,
        kappa=kappa, f1_sono=f1_s, f1_vigilia=f1_v,
        vp=vp, vn=vn, fp=fp, fn=fn,
    )


def split_por_sujeito(id_sujeito: np.ndarray):
    """Leave-one-subject-out. Gera (sujeito, mascara_treino, mascara_teste).

    **Por SUJEITO, nunca por época.** Épocas da mesma noite são altamente
    correlacionadas; embaralhar por época infla a acurácia de forma espetacular
    e falsa. É o erro mais comum da literatura de wearables, e é silencioso.
    """
    ids = np.asarray(id_sujeito, dtype=object)
    for s in sorted(set(ids.tolist())):
        teste = ids == s
        yield s, ~teste, teste
