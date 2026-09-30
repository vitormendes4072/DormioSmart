"""As geradoras dos casos do vetor dourado. Um módulo só, para as duas suítes
e o verificador por mutação falarem exatamente do mesmo sinal.

Antes isto estava copiado entre `test_vetor_dourado.py` e
`test_redundancia_angular.py`. Duas cópias de uma geradora de sinal é o mesmo
defeito que o vetor dourado existe para evitar, um nível acima: as duas suítes
achavam que testavam o mesmo sinal, e nada garantia isso.

=============================================================================
Por que existem DUAS famílias de caso, e não uma
=============================================================================
O contrato v2.5.0 partiu o vetor de características em duas fronteiras, e cada
uma falha de um jeito diferente:

  FRONTEIRA A — dispositivo (Python ↔ C++)
      As 6 features intra-época mais `ĝ`. Tudo aqui é função **só** das
      amostras da própria época: o firmware não guarda estado entre épocas.
      Testar isto exige as amostras brutas, e é o que `vetor_dourado.json`
      carrega (428 KB para 5 épocas — o custo é real).

  FRONTEIRA B — servidor (derivação a partir do `ĝ` guardado)
      `inclinacao_rel` e `d_angulo`, que são função **só** da sequência de
      `ĝ` — nunca das amostras. Então o dourado desta fronteira **não precisa
      de amostra bruta nenhuma**: ele carrega a sequência de `ĝ` e os dois
      ângulos esperados, e cabe em alguns KB.

Essa separação não é arrumação: é a razão de o `DATA-07c` ser barato. Cobrir
as features inter-época com sequências de 30 épocas de amostras brutas custaria
~2,5 MB de JSON e um parser que o núcleo C++ não tem. Cobrindo-as na fronteira
onde elas de fato vivem, custa 8 KB e nenhum C++.
"""

from __future__ import annotations

import math

import numpy as np

FS_PADRAO = 32.0
DUR_EPOCA_S = 30.0

#: Comprimento de uma época completa a 32 Hz. A paridade só é declarada para
#: épocas completas — ver `N_AMOSTRAS_MINIMO_PARIDADE` em test_vetor_dourado.py.
N_AMOSTRAS_EPOCA = int(FS_PADRAO * DUR_EPOCA_S)


# --------------------------------------------------------------------------
# Geradoras de sinal
# --------------------------------------------------------------------------
def epoca_sintetica(seed: int, fs: float = FS_PADRAO, dur_s: float = DUR_EPOCA_S) -> np.ndarray:
    """A geradora histórica: gravidade em direção aleatória + 3 senoides + ruído.

    Mantida **idêntica** à que gerou os 5 casos originais de `vetor_dourado.
    json`. Mexer aqui invalida o dourado inteiro.
    """
    rng = np.random.default_rng(seed)
    n = int(fs * dur_s)
    t = np.arange(n) / fs
    g = rng.normal(size=3)
    g /= np.linalg.norm(g)
    mov = np.zeros((n, 3))
    for _ in range(3):
        d = rng.normal(size=3)
        d /= np.linalg.norm(d)
        mov += np.outer(np.sin(2 * np.pi * rng.uniform(0.3, 3.5) * t + rng.uniform(0, 6.28)), d)
    return g + mov * rng.uniform(0.005, 0.08) + rng.normal(0, 0.003, (n, 3))


def epoca_com_gravidade(
    g_alvo: np.ndarray,
    seed: int,
    fs: float = FS_PADRAO,
    dur_s: float = DUR_EPOCA_S,
    amplitude: float = 0.02,
) -> np.ndarray:
    """Igual à de cima, mas com a direção da gravidade **imposta**.

    É o que permite montar uma trajetória de postura conhecida. `amplitude` é
    fixa (e não sorteada) de propósito: com ela sorteada, duas épocas que
    deveriam ter a mesma orientação sairiam com `ĝ` levemente diferente, e o
    caso `retorno_a_mesma_orientacao` perderia a precisão que o torna útil.
    """
    rng = np.random.default_rng(seed)
    n = int(fs * dur_s)
    t = np.arange(n) / fs
    mov = np.zeros((n, 3))
    for _ in range(3):
        d = rng.normal(size=3)
        d /= np.linalg.norm(d)
        mov += np.outer(np.sin(2 * np.pi * rng.uniform(0.3, 3.5) * t + rng.uniform(0, 6.28)), d)
    g_alvo = np.asarray(g_alvo, dtype=float)
    g_alvo = g_alvo / np.linalg.norm(g_alvo)
    return g_alvo + mov * amplitude + rng.normal(0, 0.003, (n, 3))


def girar(v: np.ndarray, graus: float, eixo_seed: int) -> np.ndarray:
    """Gira `v` por exatamente `graus`, num plano escolhido de forma determinística.

    O eixo é sorteado e depois **projetado fora de `v`**, de modo que o giro
    aconteça no plano gerado por `v` e pela perpendicular: aí
    `arccos(v · girar(v, θ)) = θ` exatamente, que é o que faz este módulo
    servir para montar um `d_angulo` de valor conhecido.
    """
    v = np.asarray(v, dtype=float)
    v = v / np.linalg.norm(v)
    rng = np.random.default_rng(eixo_seed)
    k = rng.normal(size=3)
    k = k - np.dot(k, v) * v
    k = k / np.linalg.norm(k)
    th = math.radians(graus)
    return v * math.cos(th) + k * math.sin(th)


def _trajetoria(inicio: np.ndarray, passos: list[tuple[float, int]]) -> list[np.ndarray]:
    """Aplica uma lista de (graus, eixo_seed) acumulando a partir de `inicio`."""
    saida = [np.asarray(inicio, dtype=float) / np.linalg.norm(inicio)]
    for graus, eixo in passos:
        saida.append(saida[-1] if graus == 0.0 else girar(saida[-1], graus, eixo))
    return saida


_Z = np.array([0.0, 0.0, 1.0])


# --------------------------------------------------------------------------
# FRONTEIRA B — as sequências. Cada uma devolve (lista de épocas, metadados).
#
# `seeds` controla o conteúdo de movimento de cada época; `direcoes` controla a
# orientação. Repetir um par (direção, seed) produz uma época **bit a bit
# idêntica** — é assim que `retorno_a_mesma_orientacao` consegue exigir
# igualdade exata em vez de "parecido".
# --------------------------------------------------------------------------
def _seq_postura_estavel_com_mudanca():
    """Dormindo de um lado, vira, dorme do outro. O caso mais comum da noite.

    5 épocas paradas, uma transição de 50°, 6 épocas paradas. `d_angulo` é ~0
    em quase tudo e tem um pico só; `inclinacao_rel` tem dois patamares.
    """
    a = _Z
    b = girar(a, 50.0, eixo_seed=101)
    direcoes = [a] * 5 + [b] * 7
    seeds = list(range(200, 212))
    return direcoes, seeds, {
        "o_que_exercita": "um degrau de postura, com patamar antes e depois",
        "espera": "d_angulo ~0 salvo um pico de ~50 graus no indice 5",
    }


def _seq_virada_brusca():
    """Virada grande numa época só — a cauda que o estudo do buffer isolou.

    O estudo mediu que as viradas de [60,180) graus são 1 252 épocas em 87 795
    (1,4 %) e concentram o erro da aproximação barata. Se o dourado não tem uma,
    ele não cobre a faixa onde a feature importa.
    """
    a = _Z
    b = girar(a, 140.0, eixo_seed=303)
    direcoes = [a] * 4 + [b] * 5
    seeds = list(range(300, 309))
    return direcoes, seeds, {
        "o_que_exercita": "virada de 140 graus, faixa [60,180) do estudo do buffer",
        "espera": "um d_angulo de ~140 graus; inclinacao_rel muda de patamar",
    }


def _seq_deriva_lenta():
    """O travesseiro escorregando: 0,8° por época, 30 épocas.

    **É o caso que separa as duas features.** `d_angulo` fica sempre abaixo de
    1° (a faixa onde o estudo diz que a aproximação barata acerta), mas
    `inclinacao_rel` acumula até ~12°. Uma implementação que confundisse as duas
    passaria em `virada_brusca` e cairia aqui.
    """
    # ⚠️ O eixo de giro é o MESMO em todos os passos (`eixo_seed` constante).
    # Com um eixo sorteado por passo isto vira passeio aleatório na esfera: 29
    # passos de 0,8° acumulam só ~0,8·√29 ≈ 4° em vez de 23°, e o caso perde
    # justamente o contraste que o justifica. (Foi o que aconteceu na primeira
    # versão — `test_deriva_lenta_separa_as_duas_features` reprovou com
    # inclinacao_rel máxima de 3,77°.) Deriva é movimento coerente numa
    # direção, que é o que um travesseiro escorregando faz.
    direcoes = _trajetoria(_Z, [(0.8, 400) for _ in range(29)])
    seeds = list(range(400, 430))
    return direcoes, seeds, {
        "o_que_exercita": "deriva sub-grau COERENTE acumulando em deslocamento grande",
        "espera": "d_angulo < 1 grau em todas; inclinacao_rel chega a ~11 graus",
    }


def _seq_retorno_a_mesma_orientacao():
    """Vai e volta: A (5 épocas), B a 70°, A de novo — com as MESMAS sementes.

    As épocas 10..14 são bit a bit iguais às 0..4, então `inclinacao_rel` tem de
    voltar ao valor de partida **exatamente**, não "perto". Isso pega duas
    classes de erro de uma vez: referência que deriva com o tempo (um
    acumulador incremental em vez do Weiszfeld da noite inteira) e sinal
    trocado no produto interno.
    """
    a = _Z
    b = girar(a, 70.0, eixo_seed=505)
    direcoes = [a] * 5 + [b] * 5 + [a] * 5
    seeds = list(range(500, 505)) + list(range(510, 515)) + list(range(500, 505))
    return direcoes, seeds, {
        "o_que_exercita": "retorno exato a uma orientacao ja visitada",
        "espera": "inclinacao_rel[10:15] identica a inclinacao_rel[0:5]",
        "indices_identicos": [[0, 10], [1, 11], [2, 12], [3, 13], [4, 14]],
    }


def _seq_faixa_de_viradas():
    """Uma época em cada faixa que o estudo do buffer separou.

    O estudo reportou o erro da aproximação por faixa de `d_angulo`:
    [0,1) n=73 386 · [5,20) n=4 719 · [60,180) n=1 252. Este caso põe um
    representante de cada uma, mais as intermediárias, para que o dourado
    cubra a distribuição inteira e não só o meio dela.
    """
    alvos = [0.0, 0.3, 0.9, 2.5, 7.0, 18.0, 35.0, 75.0, 130.0, 179.0]
    direcoes = _trajetoria(_Z, [(g, 600 + i) for i, g in enumerate(alvos)])
    seeds = list(range(600, 600 + len(direcoes)))
    return direcoes, seeds, {
        "o_que_exercita": "d_angulo cobrindo [0,1), [1,5), [5,20), [20,60), [60,180)",
        "espera": "cada faixa do estudo do buffer com ao menos um representante",
        "giros_pedidos_graus": alvos,
    }


def _seq_duas_epocas():
    """O mínimo em que as features inter-época existem.

    Com uma época só elas valem 0 por definição; com duas, `d_angulo[1]` é o
    primeiro valor real que o servidor calcula na vida. E `ĝ_ref` de dois
    vetores é um caso de borda do Weiszfeld: a mediana geométrica de dois
    pontos é qualquer ponto do segmento entre eles, e o algoritmo só não
    oscila porque a inicialização é a média.
    """
    a = _Z
    b = girar(a, 33.0, eixo_seed=707)
    return [a, b], [700, 701], {
        "o_que_exercita": "sequencia minima; Weiszfeld com n=2 (mediana nao unica)",
        "espera": "d_angulo[0]=0 por definicao, d_angulo[1]=~33 graus",
    }


def _seq_uma_epoca():
    """O degenerado. As duas features **têm** de valer 0, e 0 aqui significa
    'indefinido', não 'não houve virada'."""
    return [_Z], [800], {
        "o_que_exercita": "n=1, o degenerado",
        "espera": "inclinacao_rel=0 e d_angulo=0, ambos por definicao",
    }


def _seq_lacuna_entre_epocas():
    """Buraco na drenagem: as épocas 0..3 e 4..7 são separadas por ~40 min.

    ⚠️ **Este caso documenta um comportamento, não o endossa.**
    `features_inter_epoca` não conhece carimbo de tempo: ela compara vizinhos
    na ordem do array. Então o `d_angulo` do índice 4 sai como se a virada de
    85° tivesse acontecido em 30 s, quando na verdade houve 40 min sem dado.

    O dourado fixa o valor que o código produz hoje para que a mudança seja
    **visível** no dia em que o `DATA-07b` decidir carregar tempo por época.
    Sem este caso, essa mudança entraria em silêncio.
    """
    a = _Z
    b = girar(a, 85.0, eixo_seed=909)
    direcoes = [a] * 4 + [b] * 4
    seeds = list(range(900, 908))
    return direcoes, seeds, {
        "o_que_exercita": "lacuna temporal entre os indices 3 e 4",
        "espera": "d_angulo[4] calculado COMO SE fosse adjacente — comportamento atual",
        "lacuna_apos_indice": 3,
        "lacuna_s": 2400,
        "ressalva": (
            "features_inter_epoca ignora tempo. Valor fixado para tornar visivel "
            "a mudanca quando o DATA-07b decidir carregar carimbo por epoca."
        ),
    }


#: As sequências da fronteira B, na ordem em que entram no JSON.
SEQUENCIAS = {
    "postura_estavel_com_mudanca": _seq_postura_estavel_com_mudanca,
    "virada_brusca": _seq_virada_brusca,
    "deriva_lenta": _seq_deriva_lenta,
    "retorno_a_mesma_orientacao": _seq_retorno_a_mesma_orientacao,
    "faixa_de_viradas": _seq_faixa_de_viradas,
    "duas_epocas": _seq_duas_epocas,
    "uma_epoca": _seq_uma_epoca,
    "lacuna_entre_epocas": _seq_lacuna_entre_epocas,
}


def montar_sequencia(nome: str, fs: float = FS_PADRAO) -> tuple[np.ndarray, dict]:
    """Devolve (a_epocas (n_ep, n_am, 3), metadados) de uma sequência nomeada."""
    direcoes, seeds, meta = SEQUENCIAS[nome]()
    if len(direcoes) != len(seeds):
        raise AssertionError(f"{nome}: {len(direcoes)} direcoes para {len(seeds)} sementes")
    epocas = np.stack([
        epoca_com_gravidade(d, s, fs=fs) for d, s in zip(direcoes, seeds)
    ])
    return epocas, dict(meta, n_epocas=len(seeds), sementes=seeds)


# --------------------------------------------------------------------------
# FRONTEIRA A — os casos de época única, com amostras brutas.
# --------------------------------------------------------------------------
#: Os 5 casos históricos. Não mexer: o lado C++ vai ler estes números.
SEEDS_DISPOSITIVO = (1, 2, 3, 4, 5)

#: Épocas curtas. **Não entram na paridade** — entram num teste que prova por que
#: não podem entrar. Ver `test_epoca_incompleta_nao_tem_paridade`.
N_AMOSTRAS_CURTAS = (8, 10, 64, 300)
