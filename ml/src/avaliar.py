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

__all__ = [
    "Metricas", "avaliar_epoca", "split_por_sujeito",
    "MetricasAgregadas", "avaliar_por_sujeito",
]


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


#: Métricas de `Metricas.dict()` para as quais faz sentido agregar entre
#: sujeitos. Fora daqui ficam contagens (`n`, `vp`...) que não são médias.
_METRICAS_AGREGAVEIS = (
    "acuracia", "sensibilidade", "especificidade", "kappa", "f1_sono", "f1_vigilia",
)


@dataclass
class MetricasAgregadas:
    """Métricas calculadas SEPARADAMENTE por sujeito, depois agregadas.

    Por que por sujeito e não pool: com LOSO, cada sujeito contribui um número
    de épocas diferente — uma noite curta e uma longa não são a mesma
    "unidade" de evidência — e o pool esconde a variância ENTRE sujeitos, que
    é exatamente o dado que falta para distinguir "o modelo é assim" de "deu
    azar na amostra" quando N é pequeno (ver ML-DATASETS-E-PLANO.md, o alerta
    que motivou este módulo).

    `desvio_padrao` é o desvio-padrão amostral ENTRE sujeitos (não o erro
    padrão da média, e não o desvio dentro de um sujeito). `ic95_baixo`/`alto`
    vêm de bootstrap percentil sobre os sujeitos — reamostra sujeitos com
    reposição, recalcula a média a cada reamostra — de propósito sem assumir
    normalidade: kappa por sujeito é limitado e às vezes bimodal (um sujeito
    sem nenhuma época de vigília no fold de teste dá especificidade
    indefinida, não um valor baixo).
    """
    n_sujeitos: int
    n_bootstrap: int
    media: dict[str, float]
    desvio_padrao: dict[str, float]
    ic95_baixo: dict[str, float]
    ic95_alto: dict[str, float]
    n_valido: dict[str, int]           # quantos sujeitos NÃO deram NaN nessa métrica
    por_sujeito: dict[str, np.ndarray]  # métrica -> (n_sujeitos,), na ordem de `sujeitos`
    sujeitos: tuple[str, ...]

    def dict(self) -> dict:
        d = asdict(self)
        d["por_sujeito"] = {k: v.tolist() for k, v in self.por_sujeito.items()}
        return d

    def resumo(self, metrica: str) -> str:
        """`"0.408 [0.352, 0.461] (dp=0.187, n=92)"` — para tabela/log."""
        return (
            f"{self.media[metrica]:.3f} "
            f"[{self.ic95_baixo[metrica]:.3f}, {self.ic95_alto[metrica]:.3f}] "
            f"(dp={self.desvio_padrao[metrica]:.3f}, n={self.n_valido[metrica]})"
        )


def avaliar_por_sujeito(
    y_verdadeiro: np.ndarray,
    y_predito: np.ndarray,
    id_sujeito: np.ndarray,
    metricas: tuple[str, ...] = _METRICAS_AGREGAVEIS,
    n_bootstrap: int = 2000,
    seed: int = 0,
) -> MetricasAgregadas:
    """`avaliar_epoca` rodado uma vez por sujeito, depois agregado com IC.

    Sujeitos cuja métrica sai NaN (ex.: especificidade sem nenhuma época de
    vigília no fold) são excluídos da média/IC dessa métrica especificamente,
    e contados em `n_valido` — nunca silenciosamente tratados como zero, o
    que inflaria ou deflacionaria a média sem aviso.
    """
    ids = np.asarray(id_sujeito, dtype=object)
    y = np.asarray(y_verdadeiro, dtype=int)
    p = np.asarray(y_predito, dtype=int)
    sujeitos = tuple(sorted(set(ids.tolist())))

    brutos: dict[str, list[float]] = {m: [] for m in metricas}
    for s in sujeitos:
        mask = ids == s
        d = avaliar_epoca(y[mask], p[mask]).dict()
        for chave in metricas:
            brutos[chave].append(d[chave])

    por_sujeito = {k: np.array(v, dtype=float) for k, v in brutos.items()}
    rng = np.random.default_rng(seed)

    media, desvio, ic_baixo, ic_alto, n_valido = {}, {}, {}, {}, {}
    for chave, arr in por_sujeito.items():
        finito = arr[~np.isnan(arr)]
        n_valido[chave] = int(finito.size)
        if finito.size == 0:
            media[chave] = desvio[chave] = ic_baixo[chave] = ic_alto[chave] = float("nan")
            continue
        media[chave] = float(np.mean(finito))
        desvio[chave] = float(np.std(finito, ddof=1)) if finito.size > 1 else 0.0
        if finito.size > 1:
            reamostras = rng.choice(finito, size=(n_bootstrap, finito.size), replace=True)
            medias_boot = reamostras.mean(axis=1)
            ic_baixo[chave] = float(np.percentile(medias_boot, 2.5))
            ic_alto[chave] = float(np.percentile(medias_boot, 97.5))
        else:
            ic_baixo[chave] = ic_alto[chave] = media[chave]

    return MetricasAgregadas(
        n_sujeitos=len(sujeitos), n_bootstrap=n_bootstrap,
        media=media, desvio_padrao=desvio,
        ic95_baixo=ic_baixo, ic95_alto=ic_alto, n_valido=n_valido,
        por_sujeito=por_sujeito, sujeitos=sujeitos,
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
