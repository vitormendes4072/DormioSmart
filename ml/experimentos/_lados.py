"""Efeito do lado do corpo, com o SUJEITO como unidade de agrupamento.

O erro que este módulo existe para não cometer
----------------------------------------------------------------
O Newcastle tem os dois punhos de quase todo participante. É tentador
empilhar as 53 gravações e reportar "n = 53": o IC encolhe, a tabela fica
mais bonita, e o número está errado. Os dois punhos de um mesmo
participante são **a mesma noite, o mesmo sono, a mesma pontuação de PSG** —
medidos de dois lugares. Não são duas observações independentes, e tratá-las
como tal infla o N efetivo e estreita o IC de forma artificial.

A unidade de amostragem aqui é o **participante**, não a gravação. Por isso
este módulo reporta três coisas separadas, e nunca uma média das 53:

    (a) esquerdo isolado  — n = 27 participantes
    (b) direito isolado   — n = 26 participantes
    (c) efeito do lado    — n = 26 participantes que têm OS DOIS punhos,
                            pareado DENTRO do participante

A (c) é a comparação limpa. Nas (a) e (b) a diferença entre os agregados
mistura o efeito do lado com o efeito de a amostra não ser a mesma (falta o
punho direito do ncl010). Na (c), cada participante é seu próprio controle:
mesma noite, mesmo rótulo, mesmo modelo — muda só o lado do corpo. Toda a
variância entre participantes, que é a maior fonte de ruído nestas métricas
(dp ≈ 0,2 em kappa), sai da conta.

Por completude, e só como demonstração, a saída inclui a versão errada
(53 gravações empilhadas como se fossem independentes) ao lado da (c),
para mostrar de quanto é o estreitamento indevido do IC. Esse número não
entra em tabela de resultado.

Leitura do resultado
----------------------------------------------------------------
Se o efeito do lado for pequeno e o IC da diferença contiver zero, é
evidência a favor das features escolhidas: o §7 trocou `angulo_z` por
`inclinacao_rel` e a SMA L1 pela norma L2 justamente para ter invariância a
rotação e a montagem (DECISÕES TÉCNICAS 1 e 2 em `src/features.py`), e
invariância a montagem prevê exatamente insensibilidade ao lado.

Se for grande, é uma fonte de variabilidade que precisa entrar nas
limitações: significa que qual punho recebe o aparelho muda o resultado, e
o produto real não controla isso.
"""

from __future__ import annotations

import numpy as np

__all__ = ["alinhar_por_sujeito", "bootstrap_pareado_intra_sujeito", "bootstrap_agregado"]


def alinhar_por_sujeito(m_a, m_b, metrica: str):
    """Vetores da métrica nos participantes presentes NOS DOIS lados.

    `m_a`/`m_b` são `MetricasAgregadas` (ou o `.dict()` delas). A ordem de
    `sujeitos` é a mesma dentro de cada um, mas os conjuntos diferem — o
    ncl010 não tem punho direito — então o alinhamento é por ID, nunca por
    posição. Alinhar por posição aqui deslocaria todos os participantes
    depois do ncl010 e compararia gente diferente.
    """
    da = m_a if isinstance(m_a, dict) else m_a.dict()
    db = m_b if isinstance(m_b, dict) else m_b.dict()
    ia = {s: k for k, s in enumerate(da["sujeitos"])}
    ib = {s: k for k, s in enumerate(db["sujeitos"])}
    comuns = [s for s in da["sujeitos"] if s in ib]

    va = np.array([da["por_sujeito"][metrica][ia[s]] for s in comuns], dtype=float)
    vb = np.array([db["por_sujeito"][metrica][ib[s]] for s in comuns], dtype=float)
    ok = ~(np.isnan(va) | np.isnan(vb))
    return va[ok], vb[ok], [s for s, bom in zip(comuns, ok) if bom]


def bootstrap_pareado_intra_sujeito(m_a, m_b, metrica: str,
                                    n_bootstrap: int = 2000, seed: int = 0) -> dict | None:
    """IC95 da diferença (a − b) reamostrando PARTICIPANTES, não gravações.

    O bootstrap sorteia participantes com reposição e, para cada participante
    sorteado, leva o par (esquerdo, direito) inteiro. É o cluster bootstrap:
    é o que mantém o N efetivo igual ao nº de participantes.
    """
    va, vb, sujeitos = alinhar_por_sujeito(m_a, m_b, metrica)
    if va.size < 2:
        return None
    d = va - vb
    rng = np.random.default_rng(seed)
    medias = rng.choice(d, size=(n_bootstrap, d.size), replace=True).mean(axis=1)
    lo, hi = float(np.percentile(medias, 2.5)), float(np.percentile(medias, 97.5))
    return {
        "metrica": metrica,
        "media_a": float(va.mean()), "media_b": float(vb.mean()),
        "delta_medio": float(d.mean()),
        "desvio_padrao_delta": float(d.std(ddof=1)),
        "ic95_baixo": lo, "ic95_alto": hi,
        "n_participantes": int(va.size),
        "significativo": bool(lo > 0.0 or hi < 0.0),
        "maior_diferenca_individual": float(np.abs(d).max()),
        "sujeito_mais_discrepante": sujeitos[int(np.argmax(np.abs(d)))],
    }


def bootstrap_agregado(valores: np.ndarray, n_bootstrap: int = 2000, seed: int = 0) -> dict:
    """IC95 da média, reamostrando as unidades que forem passadas.

    Existe para produzir o número ERRADO de propósito (53 gravações como se
    fossem independentes) e poder mostrar, lado a lado com o correto, o
    tamanho do estreitamento indevido.
    """
    v = np.asarray(valores, dtype=float)
    v = v[~np.isnan(v)]
    if v.size < 2:
        return {"media": float(v.mean()) if v.size else float("nan"),
                "ic95_baixo": float("nan"), "ic95_alto": float("nan"), "n": int(v.size)}
    rng = np.random.default_rng(seed)
    medias = rng.choice(v, size=(n_bootstrap, v.size), replace=True).mean(axis=1)
    return {
        "media": float(v.mean()),
        "ic95_baixo": float(np.percentile(medias, 2.5)),
        "ic95_alto": float(np.percentile(medias, 97.5)),
        "n": int(v.size),
    }
