"""Autocalibração do acelerômetro pela gravidade (CAL-03), referência em Python.

O erro que este módulo existe para corrigir
-------------------------------------------
Um acelerômetro real tem, em cada eixo, um desvio (lê `+o` com zero de entrada)
e um erro de escala (lê `s·x` em vez de `x`), e os dois andam com a
temperatura. Parado, ele deveria ler a gravidade, 1 g, em qualquer posição; no
Moto E7 lê de 0,991 a 1,020 g conforme a posição (diário, 10/11 iv). O ENMO,
`max(‖a‖ − 1, 0)`, enxerga esse erro como movimento quando ‖a‖ > 1 — 18,7 mg
parado com a tela para baixo — e esconde o movimento pequeno quando ‖a‖ < 1.

O método
--------
O de van Hees et al. (2014), o do GGIR: as épocas paradas são pontos que
deveriam estar sobre a esfera de raio 1 g. A cada iteração, cada ponto
calibrado é projetado na esfera (o "alvo"), e por eixo se ajusta, por mínimos
quadrados, a reta que leva o ponto bruto ao alvo:

    calibrado_k = desvio_k + escala_k · bruto_k + coef_temp_k · (T − T_ref)

até o erro parar de cair.

O que difere do GGIR, e por quê
-------------------------------
O GGIR recusa calibrar sem pontos espalhados pela esfera (cada eixo com
valores além de ±0,3 g dos dois lados). Um celular no colchão fica deitado:
`x` e `y` perto de zero a noite toda, e só `z` muda de lado — quando muda.
Recusar seria não calibrar nunca. Aqui cada eixo usa só o que os pontos
identificam:

  completo   o eixo passou de +0,3 g e de −0,3 g: desvio e escala.
  desvio     passou de 0,3 g de um lado só: só o desvio (escala = 1). Desvio e
             escala não se separam com um lado só, mas o desvio sozinho põe a
             norma em 1 g naquela posição, que é o que o ENMO precisa.
  fixo       nunca passou de 0,3 g: o eixo fica como está. Com o eixo perto de
             zero, o erro dele quase não mexe na norma (10 mg de desvio num
             eixo a 0 g mudam a norma em 0,05 mg).

A temperatura só entra com faixa de pelo menos `FAIXA_MINIMA_TEMPERATURA_C`
entre os pontos: com menos, o coeficiente ajustaria ruído e seria extrapolado
para noites mais frias ou mais quentes.

E a calibração só é aceita se o erro depois for menor que antes e menor que
`ERRO_MAXIMO_ACEITO_G` — o mesmo 0,01 g do GGIR. Recusada, nada é corrigido:
uma estimativa ruim não pode piorar o dado.

Este módulo é a referência. O núcleo C++ (`firmware/nucleo/calibracao.cpp`) faz
a mesma conta, e `testes/test_dourado_calibracao.py` grava o dourado que os
dois conferem.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

__all__ = [
    "LIMIAR_PARADO_G", "LADO_MINIMO_G", "FAIXA_MINIMA_TEMPERATURA_C",
    "PONTOS_MINIMOS", "ERRO_MAXIMO_ACEITO_G", "ITERACOES_MAXIMAS", "TOLERANCIA",
    "Calibracao", "aplicar", "desfazer", "estimar",
]

#: Época parada: `mag_din_media` abaixo disto. É o critério da bancada da
#: etapa 0 (diário, 10/11 iv). Quem seleciona os pontos é o app (etapa 2).
LIMIAR_PARADO_G = 0.010
#: O critério de lado do GGIR.
LADO_MINIMO_G = 0.3
#: Faixa de temperatura entre os pontos para estimar o coeficiente.
#: PROVISÓRIO: revisar com noites reais em temperaturas diferentes (etapa 3).
FAIXA_MINIMA_TEMPERATURA_C = 2.0
#: 40 épocas paradas de 30 s = 20 min.
PONTOS_MINIMOS = 40
#: Erro RMS da norma, depois de calibrar, acima do qual a calibração é recusada.
ERRO_MAXIMO_ACEITO_G = 0.010
ITERACOES_MAXIMAS = 200
#: Parada: a melhora do erro RMS entre duas iterações.
TOLERANCIA = 1e-10

COMPLETO, DESVIO, FIXO = "completo", "desvio", "fixo"


@dataclass
class Calibracao:
    """O resultado. Sem `aceita`, os parâmetros são os da identidade."""

    aceita: bool = False
    motivo: str = ""
    desvio: list[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    escala: list[float] = field(default_factory=lambda: [1.0, 1.0, 1.0])
    coef_temp: list[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    temp_ref_c: float = 0.0
    modos: list[str] = field(default_factory=lambda: [FIXO, FIXO, FIXO])
    usou_temperatura: bool = False
    n: int = 0
    erro_antes_g: float = 0.0
    erro_depois_g: float = 0.0
    iteracoes: int = 0


def aplicar(c: Calibracao, xyz: np.ndarray, temp_c: np.ndarray | float) -> np.ndarray:
    """Calibra amostras `(n, 3)` em g. Sem `aceita`, devolve uma cópia intacta."""
    xyz = np.asarray(xyz, dtype=float)
    if not c.aceita:
        return xyz.copy()
    dt = np.asarray(temp_c, dtype=float) - c.temp_ref_c
    saida = np.empty_like(xyz)
    for k in range(3):
        saida[..., k] = c.desvio[k] + c.escala[k] * xyz[..., k] + c.coef_temp[k] * dt
    return saida


def desfazer(c: Calibracao, xyz: np.ndarray, temp_c: np.ndarray | float) -> np.ndarray:
    """O inverso de `aplicar`: do calibrado de volta ao bruto.

    O app precisa dele (etapa 2): a época guardada já saiu calibrada pela
    calibração daquela noite, e a próxima estimativa parte do bruto.
    """
    xyz = np.asarray(xyz, dtype=float)
    if not c.aceita:
        return xyz.copy()
    dt = np.asarray(temp_c, dtype=float) - c.temp_ref_c
    saida = np.empty_like(xyz)
    for k in range(3):
        saida[..., k] = (xyz[..., k] - c.desvio[k] - c.coef_temp[k] * dt) / c.escala[k]
    return saida


def _erro_rms(xyz: np.ndarray) -> float:
    return float(np.sqrt(np.mean((np.linalg.norm(xyz, axis=1) - 1.0) ** 2)))


def _resolver(colunas: list[np.ndarray], alvo: np.ndarray) -> np.ndarray:
    """Mínimos quadrados pelas equações normais, como o C++ faz.

    Não é `np.linalg.lstsq` de propósito: o C++ resolve as equações normais
    com eliminação de Gauss, e a referência tem de fazer a mesma conta.
    """
    a = np.column_stack(colunas)
    return np.linalg.solve(a.T @ a, a.T @ alvo)


def estimar(pontos: np.ndarray, temp_c: np.ndarray) -> Calibracao:
    """Estima a calibração a partir de épocas paradas.

    `pontos`: `(n, 3)`, o vetor médio da aceleração de cada época parada, em g,
    BRUTO (sem calibração). `temp_c`: `(n,)`, a temperatura de cada uma.
    """
    p = np.asarray(pontos, dtype=float)
    t = np.asarray(temp_c, dtype=float)
    c = Calibracao(n=int(p.shape[0]))
    if p.ndim != 2 or p.shape[1] != 3 or t.shape != (p.shape[0],):
        raise ValueError("pontos (n, 3) e temp_c (n,)")
    if c.n < PONTOS_MINIMOS:
        c.motivo = f"poucos pontos: {c.n} (mínimo {PONTOS_MINIMOS})"
        return c

    c.erro_antes_g = _erro_rms(p)
    for k in range(3):
        acima = p[:, k].max() > LADO_MINIMO_G
        abaixo = p[:, k].min() < -LADO_MINIMO_G
        c.modos[k] = COMPLETO if (acima and abaixo) else DESVIO if (acima or abaixo) else FIXO
    c.temp_ref_c = float(t.mean())
    dt = t - c.temp_ref_c
    c.usou_temperatura = bool(t.max() - t.min() >= FAIXA_MINIMA_TEMPERATURA_C)

    if all(m == FIXO for m in c.modos):
        c.motivo = "nenhum eixo passou de 0,3 g"
        c.erro_depois_g = c.erro_antes_g
        return c

    # A iteração roda com `aceita` ligado para `aplicar` calibrar; a decisão
    # de aceitar vem no fim.
    c.aceita = True
    um = np.ones(c.n)
    erro = c.erro_antes_g
    for i in range(1, ITERACOES_MAXIMAS + 1):
        cal = aplicar(c, p, t)
        alvo = cal / np.linalg.norm(cal, axis=1, keepdims=True)
        for k, modo in enumerate(c.modos):
            if modo == FIXO:
                continue
            if modo == COMPLETO:
                colunas, y = [um, p[:, k]], alvo[:, k]
            else:
                colunas, y = [um], alvo[:, k] - p[:, k]
            if c.usou_temperatura:
                colunas.append(dt)
            b = _resolver(colunas, y)
            c.desvio[k] = float(b[0])
            if modo == COMPLETO:
                c.escala[k] = float(b[1])
            if c.usou_temperatura:
                c.coef_temp[k] = float(b[-1])
        novo = _erro_rms(aplicar(c, p, t))
        c.iteracoes = i
        melhora = erro - novo
        erro = novo
        if abs(melhora) < TOLERANCIA:
            break

    c.erro_depois_g = erro
    if not (c.erro_depois_g < c.erro_antes_g):
        return _recusar(c, "o erro não caiu")
    if c.erro_depois_g > ERRO_MAXIMO_ACEITO_G:
        return _recusar(c, f"erro depois {c.erro_depois_g:.4f} g acima de {ERRO_MAXIMO_ACEITO_G} g")
    c.motivo = "aceita"
    return c


def _recusar(c: Calibracao, motivo: str) -> Calibracao:
    """Recusada: os parâmetros voltam à identidade, e o diagnóstico fica."""
    recusa = Calibracao(
        aceita=False, motivo=motivo, temp_ref_c=c.temp_ref_c, modos=list(c.modos),
        usou_temperatura=c.usou_temperatura, n=c.n, erro_antes_g=c.erro_antes_g,
        erro_depois_g=c.erro_depois_g, iteracoes=c.iteracoes,
    )
    return recusa
