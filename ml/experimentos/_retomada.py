"""LOSO retomável — checkpoint por DOBRA, não por item.

Por que existe
----------------------------------------------------------------
O `ml03b_otimizacoes.py` já quebrou o experimento em itens para que uma
interrupção custasse no máximo um item. Não bastou: o ambiente desta sessão
mata qualquer processo ao fim de cada chamada de shell (namespace de PID
próprio, sem persistência entre chamadas), com teto de ~3 min por chamada.
Um item de ~11 min não cabe, e o item 9 (contexto ±11) não cabe nem por
braço.

As duas saídas óbvias são ruins:

  * reduzir N — quebra a comparação pareada com a linha de base N=92, que é
    justamente o que dá poder ao teste;
  * rodar em segundo plano — foi o que falhou quatro vezes.

Então o checkpoint desce um nível: cada DOBRA do leave-one-subject-out é
salva assim que termina. Uma chamada processa quantas dobras couberem no
orçamento de tempo, grava, e sai dizendo quanto falta. A chamada seguinte
retoma exatamente de onde parou. O custo de uma interrupção passa a ser uma
dobra (~2 s), e N continua 92.

Garantia de reprodutibilidade
----------------------------------------------------------------
O resultado NÃO depende de onde as chamadas foram cortadas. Cada dobra é
independente por construção (o LOSO ajusta um modelo do zero sobre os
outros 91 sujeitos), a semente é fixada por dobra a partir da semente
global, e a predição de cada sujeito é gravada na posição dele. Rodar em
uma chamada ou em vinte dá exatamente o mesmo vetor de predição — o teste
`testes/test_retomada.py` verifica isso.

A chave de checkpoint inclui o hash da configuração e a lista de sujeitos:
mudar qualquer um dos dois gera um arquivo novo em vez de reaproveitar um
parcial incompatível em silêncio.
"""

from __future__ import annotations

import hashlib
import time
from pathlib import Path
from typing import Callable

import numpy as np

RAIZ = Path(__file__).resolve().parents[1]
PASTA_PARCIAIS = RAIZ / "experimentos" / "saida" / "_parciais"

__all__ = ["loso_com_retomada", "caminho_parcial", "limpar_parcial"]


def caminho_parcial(chave: str, pasta: Path | None = None) -> Path:
    digest = hashlib.sha256(chave.encode("utf-8")).hexdigest()[:16]
    return (pasta or PASTA_PARCIAIS) / f"_loso_{digest}.npz"


def limpar_parcial(chave: str, pasta: Path | None = None) -> None:
    """Apaga o checkpoint, se der.

    `PermissionError` é engolido de propósito: em pasta montada de fora
    (o caso desta sessão) o sistema permite escrever e sobrescrever, mas não
    remover. Apagar um parcial é higiene, nunca pré-requisito — o mecanismo
    já se protege de parcial incompatível pela chave e pela conferência de
    tamanho, então não conseguir apagar não pode derrubar um experimento.
    """
    alvo = caminho_parcial(chave, pasta)
    if alvo.exists():
        try:
            alvo.unlink()
        except PermissionError:
            pass


def loso_com_retomada(
    chave: str,
    X: np.ndarray,
    y: np.ndarray,
    ids: np.ndarray,
    prever_dobra: Callable[[np.ndarray, np.ndarray, np.ndarray, np.ndarray, int], np.ndarray],
    seed: int,
    orcamento_s: float = 115.0,
    registrar=None,
    pasta: Path | None = None,
) -> tuple[np.ndarray, bool, int, int]:
    """Roda o LOSO em pedaços, retomando de um checkpoint em disco.

    `prever_dobra(X_tr, y_tr, X_te, ids_tr, seed) -> pred_te` é a única coisa
    que muda entre itens: recebe o fold já fatiado e devolve a predição do
    sujeito de teste. Recebe `ids_tr` porque o HMM precisa contar as
    transições dentro de cada sujeito de treino.

    A semente passada é a GLOBAL, a mesma em toda dobra — igual ao que o
    `_diagonal` original faz. Nada aqui a deriva por dobra de propósito: o
    `lbfgs` da logística é determinístico e ignora `random_state`, então
    derivar a semente não mudaria número nenhum e só quebraria a
    comparabilidade com a linha de base e com os itens 6-8, que já rodaram
    de uma vez só.

    Devolve `(pred, completo, n_feitas, n_total)`. Enquanto `completo` for
    `False`, `pred` está preenchido só nas dobras já rodadas e não deve ser
    avaliado.
    """
    ids = np.asarray(ids, dtype=object)
    sujeitos = sorted(set(ids.tolist()))
    n_total = len(sujeitos)

    alvo = caminho_parcial(chave, pasta)
    if alvo.exists():
        dados = np.load(alvo, allow_pickle=True)
        pred = dados["pred"].astype(int)
        feitos = set(dados["feitos"].tolist())
        if pred.shape[0] != y.shape[0]:
            raise RuntimeError(
                f"parcial {alvo.name} tem {pred.shape[0]} épocas, dado atual tem "
                f"{y.shape[0]} — chave de checkpoint colidiu; apague o arquivo"
            )
    else:
        pred = np.zeros_like(np.asarray(y, dtype=int))
        feitos = set()

    t0 = time.time()
    novas = 0
    for s in sujeitos:
        if s in feitos:
            continue
        # `>=`, não `>` (ML-WIN-01, 28/10). O relógio do Windows anda em degraus
        # de ~15,6 ms: com orçamento zero, duas leituras no mesmo degrau dão
        # 0 s, `0 > 0` é falso e a chamada fazia mais de uma dobra. Com `>=`, o
        # orçamento zero é "uma dobra por chamada" em qualquer relógio — que é
        # o que `test_retomada_por_partes_da_o_mesmo_que_de_uma_vez` supõe.
        # Reproduzido em Linux com um relógio em degraus: reprovava 3 de 3.
        if novas > 0 and (time.time() - t0) >= orcamento_s:
            break
        mask_te = ids == s
        mask_tr = ~mask_te
        pred[mask_te] = prever_dobra(X[mask_tr], np.asarray(y)[mask_tr],
                                     X[mask_te], ids[mask_tr], seed)
        feitos.add(s)
        novas += 1
        if registrar is not None:
            registrar(len(feitos), n_total, s)

    alvo.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(alvo, pred=pred, feitos=np.array(sorted(feitos), dtype=object))
    return pred, len(feitos) == n_total, len(feitos), n_total
