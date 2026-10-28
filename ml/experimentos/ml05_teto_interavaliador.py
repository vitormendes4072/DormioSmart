"""ML-05 -- teto de concordância entre pontuadores humanos (Wearanize+).

Uso:
    python -m experimentos.ml05_teto_interavaliador
    python -m experimentos.ml05_teto_interavaliador --n-sujeitos 10   # piloto
    python -m experimentos.ml05_teto_interavaliador --resumo          # só relê o JSON

=============================================================================
O QUE ESTE EXPERIMENTO MEDE, E O QUE ELE NÃO MEDE
=============================================================================
O Wearanize+ tem DUAS pontuações manuais independentes da mesma PSG
(`PSG_Manual_Scor1` e `PSG_Manual_Scor2`). Comparar uma com a outra, na mesma
redução binária sono×vigília que o resto do pipeline usa, dá a **referência
superior** contra a qual os Δκ do modelo devem ser lidos: parte do que parece
erro do classificador é margem em que dois especialistas humanos, olhando o
mesmo traçado, também discordam.

O QUE ELE MEDE
  A concordância entre dois pontuadores humanos DEPOIS de reduzir o
  estadiamento AASM completo (-1/0/1/2/3/4) ao binário vigília=0 / sono=1,
  pelo mesmo `_MAPA_ROTULO` que o pipeline aplica aos rótulos de treino. É
  exatamente a tarefa do modelo, medida entre humanos.

O QUE ELE NÃO MEDE
  1. NÃO é a concordância interavaliador em estadiamento, e NÃO é comparável
     com os κ de estadiamento em 5 classes da literatura -- em direção
     nenhuma. Dois efeitos puxam para lados opostos e este experimento não
     quantifica nenhum dos dois: colapsar N1/N2/N3/REM em "sono" apaga a
     discordância interna ao sono (puxa a concordância para cima), mas a
     correção pelo acaso do κ é mais severa quando uma classe domina, que é o
     caso do binário (puxa para baixo). **Não citar este κ como "concordância
     interavaliador em PSG" nem confrontá-lo com valor publicado de
     estadiamento.**
  2. NÃO é um teto de desempenho alcançável. Dois pontuadores discordando não
     implica que exista uma resposta certa inacessível: implica que a própria
     variável-alvo tem ruído de rotulagem nessa magnitude. Um modelo que
     atingisse este κ estaria concordando com o pontuador 1 tanto quanto o
     pontuador 2 concorda -- o que é uma referência, não um limite teórico.
  3. NÃO transfere para o Newcastle. A equipe, o protocolo e os critérios de
     pontuação são outros. O Newcastle OA não publica segunda pontuação, então
     não há como medir o teto lá. Ver a nota `teto_no_newcastle` no JSON.

=============================================================================
O RECORTE -- por que 96, e não 100 nem 92
=============================================================================
ARMADILHA 4 do `wearanize.py`: o `channels.tsv` DECLARA `scor2` para os 100
sujeitos, mas o EDF só o tem em 96. Os 4 do Mentalab não têm segunda
pontuação. Logo:

  96 -- sujeitos com AS DUAS pontuações. É a população desta medição.
  92 -- sujeitos com cabeça E pulso, que é a base de desenvolvimento do ML-03
        ao ML-05. NÃO é o mesmo conjunto: a interseção é o que vale para ler os
        Δκ do modelo, e está no JSON sob `recorte_92_do_ml03`.
 100 -- sujeitos com a primeira pontuação. Irrelevante aqui.

Os dois recortes são reportados lado a lado de propósito. O de 96 é a medição
com mais N; o da interseção é o único diretamente comparável aos números do
modelo, porque é medido nos MESMOS participantes.

=============================================================================
A ASSIMETRIA DAS MÉTRICAS DIRECIONAIS
=============================================================================
κ e acurácia são simétricos: trocar os pontuadores de lugar não muda o valor.
Sensibilidade e especificidade NÃO são. Com o pontuador 1 como referência,
"especificidade" passa a significar *"das épocas que o pontuador 1 chamou de
vigília, quantas o pontuador 2 também chamou"*. É uma quantidade
interpretável e é a que interessa (a vigília é a classe difícil), mas ela
depende de quem é a referência. Por isso as duas direções são calculadas e
gravadas, e o texto do TCC deve dizer qual está citando.

A referência adotada é o **pontuador 1**, porque é ele que serve de verdade
para todos os outros experimentos do trabalho.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

for _fluxo in (sys.stdout, sys.stderr):
    if hasattr(_fluxo, "reconfigure"):
        _fluxo.reconfigure(encoding="utf-8")

from src.avaliar import avaliar_por_sujeito                                   # noqa: E402
from src.carregar.wearanize import (                                          # noqa: E402
    CANAIS_ROTULO,
    PASTA_PADRAO,
    _edf_do_sujeito,
    _indice_canal,
    _ler_rotulos,
    _pasta_plugnplay,
    ler_cabecalho_edf,
    sujeitos_com_posicoes,
    sujeitos_disponiveis,
)
from src.configuracao import carregar_config, fixar_seed                      # noqa: E402

#: As mesmas três de `ml03_transferencia.py`, mais as duas direcionais.
METRICAS_RELATORIO = ("acuracia", "especificidade", "sensibilidade", "kappa")

NOME_SAIDA = "ml05_teto_interavaliador_{hash}.json"

# =========================================================================
# Notas de prosa gravadas no JSON.
#
# Ficam aqui, e não embutidas no `json.dumps`, por uma razão prática: quando
# uma delas é corrigida, regravá-las NÃO deve exigir reler os 100 EDFs. A
# medição leva ~2,5 min de E/S; a nota é texto. `--reescrever-notas` atualiza
# só estas chaves no JSON existente, sem tocar em número nenhum.
# =========================================================================

O_QUE_NAO_MEDE = [
    "NAO e concordancia interavaliador em estadiamento de 5 classes, e NAO e comparavel "
    "com ela em direcao nenhuma: o binario apaga a discordancia interna ao sono (puxa a "
    "concordancia para cima), mas a correcao pelo acaso do kappa e mais severa quando uma "
    "classe domina, que e o caso do binario com ~90% de sono (puxa para baixo). Nenhum dos "
    "dois efeitos foi quantificado aqui, logo nao se afirma direcao",
    "NAO e um limite teorico de desempenho, e sim a magnitude do ruido de rotulagem da "
    "propria variavel-alvo. Um classificador pode, em principio, concordar com o pontuador 1 "
    "mais do que o pontuador 2 concorda",
    "NAO transfere para o Newcastle -- outra equipe, outro protocolo, outros criterios",
]

TETO_NO_NEWCASTLE = (
    "NAO MEDIDO -- a colecao Newcastle 2015 OA nao publica segunda pontuacao manual. "
    "Procedimento nao executado por indisponibilidade do dado publicado, nao procedimento "
    "com resultado desfavoravel."
)

NOTA_ASSIMETRIA = (
    "kappa e acuracia sao simetricos; sensibilidade e especificidade NAO sao. Com o "
    "pontuador 1 como referencia, especificidade = fracao das epocas que o pontuador 1 "
    "chamou de vigilia e o pontuador 2 tambem. As duas direcoes estao gravadas."
)

#: Chaves que `--reescrever-notas` atualiza. Nenhuma delas é medição.
CHAVES_DE_PROSA = {
    "o_que_nao_mede": O_QUE_NAO_MEDE,
    "teto_no_newcastle": TETO_NO_NEWCASTLE,
    "nota_assimetria": NOTA_ASSIMETRIA,
}


def _rotulos_dos_dois(sujeito: str, pasta_pnp: Path) -> tuple[np.ndarray, np.ndarray] | None:
    """(scor1, scor2) por época, ou None se o sujeito não tem as duas.

    Lê SÓ os dois canais de pontuação. Cada um tem 1 amostra por registro de
    30 s (premissa verificada em `_ler_rotulos`), então são ~1000 inteiros por
    canal -- o `memmap` de `_ler_canal` não traz o acelerômetro para a RAM.
    Ler a noite inteira aqui seria desperdício de ordens de magnitude.
    """
    edf = _edf_do_sujeito(pasta_pnp, sujeito)
    if edf is None:
        return None
    cab = ler_cabecalho_edf(edf)
    if any(_indice_canal(cab, CANAIS_ROTULO[p]) is None for p in (1, 2)):
        return None
    y1 = _ler_rotulos(cab, 1)
    y2 = _ler_rotulos(cab, 2)
    if y1 is None or y2 is None:
        return None
    if y1.shape != y2.shape:
        raise ValueError(
            f"{edf.name}: os dois canais de pontuação têm tamanhos diferentes "
            f"({y1.shape} vs {y2.shape}). A premissa 'um registro = uma época' "
            "vale por canal, então isto não deveria acontecer."
        )
    return y1, y2


def _empilhar(
    pares: dict[str, tuple[np.ndarray, np.ndarray]],
    sujeitos: list[str],
) -> tuple[np.ndarray, np.ndarray, np.ndarray, dict]:
    """Empilha os sujeitos pedidos, mantendo só épocas válidas nos DOIS.

    Uma época marcada -1 (descartar) por qualquer um dos pontuadores sai da
    conta. Descartar só pelo pontuador 1 contaria como discordância uma época
    que o pontuador 2 nem pontuou, o que não é discordância -- é ausência de
    dado. O censo do que saiu vai para o JSON, não para o silêncio.
    """
    y1s, y2s, ids = [], [], []
    n_bruto = n_descartada_1 = n_descartada_2 = n_descartada_ambos = 0
    for s in sujeitos:
        y1, y2 = pares[s]
        n_bruto += int(y1.size)
        so1 = (y1 < 0) & (y2 >= 0)
        so2 = (y2 < 0) & (y1 >= 0)
        ambos = (y1 < 0) & (y2 < 0)
        n_descartada_1 += int(np.count_nonzero(so1))
        n_descartada_2 += int(np.count_nonzero(so2))
        n_descartada_ambos += int(np.count_nonzero(ambos))
        val = (y1 >= 0) & (y2 >= 0)
        if not np.any(val):
            continue
        y1s.append(y1[val])
        y2s.append(y2[val])
        ids.append(np.full(int(np.count_nonzero(val)), s, dtype=object))
    if not y1s:
        raise RuntimeError("nenhuma época válida nos dois pontuadores")
    censo = {
        "n_epocas_brutas": n_bruto,
        "n_epocas_validas_nos_dois": int(sum(a.size for a in y1s)),
        "n_descartadas_so_pelo_pontuador_1": n_descartada_1,
        "n_descartadas_so_pelo_pontuador_2": n_descartada_2,
        "n_descartadas_pelos_dois": n_descartada_ambos,
    }
    return (
        np.concatenate(y1s),
        np.concatenate(y2s),
        np.concatenate(ids),
        censo,
    )


def _medir(y1: np.ndarray, y2: np.ndarray, ids: np.ndarray, seed: int) -> dict:
    """As duas direções, com o pontuador 1 como referência na primeira."""
    ref1 = avaliar_por_sujeito(y1, y2, ids, metricas=METRICAS_RELATORIO, seed=seed)
    ref2 = avaliar_por_sujeito(y2, y1, ids, metricas=METRICAS_RELATORIO, seed=seed)
    return {
        "referencia_pontuador_1": ref1.dict(),
        "referencia_pontuador_2": ref2.dict(),
        "prevalencia_sono_pontuador_1": float(np.mean(y1 == 1)),
        "prevalencia_sono_pontuador_2": float(np.mean(y2 == 1)),
    }


def _imprimir(titulo: str, bloco: dict) -> None:
    print(f"\n=== {titulo} ===")
    for chave, rotulo in (
        ("referencia_pontuador_1", "pontuador 1 como referência"),
        ("referencia_pontuador_2", "pontuador 2 como referência"),
    ):
        m = bloco[chave]
        print(f"  {rotulo}  (n={m['n_sujeitos']} participantes)")
        for met in METRICAS_RELATORIO:
            print(
                f"    {met:<15} {m['media'][met]:.3f} "
                f"[{m['ic95_baixo'][met]:.3f}, {m['ic95_alto'][met]:.3f}]  "
                f"dp={m['desvio_padrao'][met]:.3f}  n_valido={m['n_valido'][met]}"
            )
    print(
        f"  prevalência de sono: pontuador 1 = "
        f"{bloco['prevalencia_sono_pontuador_1']:.4f} · pontuador 2 = "
        f"{bloco['prevalencia_sono_pontuador_2']:.4f}"
    )


def _reescrever_notas(destino: Path) -> int:
    """Atualiza só as chaves de prosa do JSON, sem recalcular nada.

    Existe porque corrigir uma nota não deveria custar 2,5 min de E/S sobre
    46 GB — e porque reprocessar "só para atualizar um texto" é justamente o
    tipo de coisa que, feita com pressa, acaba gravando um número novo por
    acidente. Aqui nenhum número é tocado: as chaves regravadas estão em
    `CHAVES_DE_PROSA`, e o `utc` da medição é preservado.
    """
    if not destino.exists():
        print(f"não encontrado: {destino}", file=sys.stderr)
        return 2
    d = json.loads(destino.read_text(encoding="utf-8"))
    mudou = []
    for chave, valor in CHAVES_DE_PROSA.items():
        if d.get(chave) != valor:
            d[chave] = valor
            mudou.append(chave)
    d["utc_notas"] = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    destino.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
    if mudou:
        print(f"notas atualizadas em {destino.name}: {', '.join(mudou)}")
    else:
        print(f"nada a atualizar em {destino.name} — as notas já conferem com o código")
    print("nenhuma medição foi recalculada; `utc` da medição preservado:", d["utc"])
    return 0


def _resumo(destino: Path) -> int:
    if not destino.exists():
        print(f"não encontrado: {destino}", file=sys.stderr)
        return 2
    d = json.loads(destino.read_text(encoding="utf-8"))
    print(f"arquivo: {destino.name}")
    print(f"n com as duas pontuações: {d['censo_de_sujeitos']['n_com_os_dois_pontuadores']}")
    _imprimir("96 sujeitos com as duas pontuações", d["todos_os_96"])
    _imprimir("interseção com os 92 da base de desenvolvimento", d["recorte_92_do_ml03"])
    print("\ncenso de épocas (96):", json.dumps(d["todos_os_96"]["censo_de_epocas"]))
    print("censo de épocas (interseção):", json.dumps(d["recorte_92_do_ml03"]["censo_de_epocas"]))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--n-sujeitos", type=int, default=None,
                    help="limita a N sujeitos (ordem alfabética) -- piloto rápido")
    ap.add_argument("--pasta", type=Path, default=None)
    ap.add_argument("--resumo", action="store_true",
                    help="não recalcula: relê o JSON já gravado e imprime")
    ap.add_argument("--reescrever-notas", action="store_true",
                    help="atualiza só as chaves de prosa do JSON (o_que_nao_mede, "
                         "teto_no_newcastle, nota_assimetria) a partir do código, sem "
                         "recalcular medição alguma")
    args = ap.parse_args()

    cfg = carregar_config()
    saida = RAIZ / "experimentos" / "saida"
    destino = saida / NOME_SAIDA.format(hash=cfg.hash)
    if args.resumo:
        return _resumo(destino)
    if args.reescrever_notas:
        return _reescrever_notas(destino)

    fixar_seed(cfg.seed)
    pasta = Path(args.pasta) if args.pasta else PASTA_PADRAO
    pasta_pnp = _pasta_plugnplay(pasta)
    kwargs_pasta = {"pasta": pasta} if args.pasta else {}

    todos = sujeitos_disponiveis(pasta)
    if args.n_sujeitos:
        todos = todos[: args.n_sujeitos]

    print(f"config hash={cfg.hash} · seed={cfg.seed} · sujeitos no disco={len(todos)}")
    print("Lendo SÓ os dois canais de pontuação de cada EDF (o acelerômetro não é tocado)...")

    pares: dict[str, tuple[np.ndarray, np.ndarray]] = {}
    sem_segundo: list[str] = []
    for s in todos:
        par = _rotulos_dos_dois(s, pasta_pnp)
        if par is None:
            sem_segundo.append(s)
            continue
        pares[s] = par

    com_os_dois = sorted(pares)
    print(f"  com as duas pontuações: {len(com_os_dois)}")
    print(f"  sem a segunda (ARMADILHA 4): {len(sem_segundo)} -> {sem_segundo}")

    # A base de desenvolvimento do ML-03 em diante. A interseção é o único
    # recorte diretamente comparável aos Δκ do modelo.
    try:
        sujeitos_92 = sujeitos_com_posicoes(["cabeca", "pulso"], **kwargs_pasta)
    except Exception as ex:                                   # pragma: no cover
        print(f"[ml05] AVISO: não foi possível montar os 92 do ML-03: {ex}", file=sys.stderr)
        sujeitos_92 = []
    intersecao = sorted(set(com_os_dois) & set(sujeitos_92))
    print(f"  base de desenvolvimento (cabeça∩pulso): {len(sujeitos_92)}")
    print(f"  interseção com quem tem os dois pontuadores: {len(intersecao)}")

    blocos: dict[str, dict] = {}
    for nome, lista in (("todos_os_96", com_os_dois), ("recorte_92_do_ml03", intersecao)):
        if not lista:
            blocos[nome] = {"indisponivel": "conjunto vazio"}
            continue
        y1, y2, ids, censo = _empilhar(pares, lista)
        bloco = _medir(y1, y2, ids, cfg.seed)
        bloco["censo_de_epocas"] = censo
        bloco["sujeitos"] = lista
        blocos[nome] = bloco
        _imprimir(nome, bloco)

    saida.mkdir(parents=True, exist_ok=True)
    carimbo = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    destino.write_text(
        json.dumps(
            {
                "experimento": "ML-05 -- teto de concordancia entre pontuadores humanos",
                "hash_config": cfg.hash,
                "seed": cfg.seed,
                "utc": carimbo,
                "dataset": "wearanize",
                "tarefa": "sono x vigilia binario (estadiamento AASM reduzido por _MAPA_ROTULO)",
                "referencia_adotada_no_texto": "pontuador 1",
                "o_que_nao_mede": O_QUE_NAO_MEDE,
                "teto_no_newcastle": TETO_NO_NEWCASTLE,
                "censo_de_sujeitos": {
                    "n_no_disco": len(todos),
                    "n_com_os_dois_pontuadores": len(com_os_dois),
                    "n_sem_o_segundo": len(sem_segundo),
                    "sem_o_segundo": sem_segundo,
                    "n_base_desenvolvimento_cabeca_e_pulso": len(sujeitos_92),
                    "n_intersecao": len(intersecao),
                },
                "metricas": list(METRICAS_RELATORIO),
                "nota_assimetria": NOTA_ASSIMETRIA,
                **blocos,
                "config": cfg.dict() if hasattr(cfg, "dict") else {},
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"\nsalvo em experimentos/saida/{destino.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
