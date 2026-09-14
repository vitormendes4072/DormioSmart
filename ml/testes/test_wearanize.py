"""Testes do carregador do Wearanize+ OA.

=============================================================================
POR QUE ESTES TESTES CONSTROEM UM EDF EM VEZ DE LER O DATASET
=============================================================================
O dataset tem ~49 GB e não entra no git (é condição de uso, não só tamanho).
Um teste que exige o dado em disco não roda em máquina limpa, não roda em CI, e
na prática não roda nunca.

Então estes testes **fabricam EDFs mínimos que reproduzem exatamente as
esquisitices verificadas nos arquivos reais** em 2026-09-14 — grafia de canal,
unidade do Empatica, canais ausentes, o `PSG_Move.` a 128 Hz. Cada uma delas é
uma armadilha documentada em `src/carregar/wearanize.py`, e cada teste aqui
existe para garantir que a armadilha continue tratada quando alguém mexer no
carregador daqui a três meses.

A estrutura fabricada foi conferida contra o `sub-005` real:
    48 canais · 974 registros · registro de 30 s · cabeçalho de 12 544 bytes
    tamanho previsto pelo cabeçalho = 499 966 744 B, que é o tamanho do arquivo

⚠️ **O que estes testes NÃO provam:** que o carregador funciona no dado real.
Isso exige o dataset em disco. Ver `ml/README.md`, seção "O que falta executar".
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from src.carregar import carregar
from src.carregar.wearanize import (
    POSICOES,
    SUBPASTA_PLUGNPLAY,
    carregar_wearanize,
    ler_cabecalho_edf,
    sujeitos_com_posicoes,
    sujeitos_disponiveis,
)

# =========================================================================
# Números do censo real — travados aqui de propósito
# =========================================================================
# Lidos dos cabeçalhos EDF dos 100 sujeitos da coleção aberta em 2026-09-14.
# Não são usados pelo código: existem para que o número na documentação e o
# número medido não se separem em silêncio. Se o dataset for revisado (v1.2),
# estes valores mudam E a documentação tem de mudar junto.
CENSO_REAL = {
    "n_sujeitos_plugnplay": 100,
    "cabeca": 100,
    "pulso": 92,
    "coxa": 93,
    "scor1": 100,
    "scor2": 96,          # o channels.tsv declara 100 — ARMADILHA 4
    "usleep": 96,
    "cabeca_e_pulso": 92,        # N do experimento principal do ML-03
    "tres_posicoes": 86,         # N da matriz 3x3 comparável
}
SEM_PULSO = ("sub-001", "sub-002", "sub-004", "sub-063",
             "sub-064", "sub-100", "sub-129", "sub-130")
SEM_COXA = ("sub-004", "sub-072", "sub-075", "sub-076",
            "sub-095", "sub-096", "sub-106")
SEM_SCOR2 = ("sub-115", "sub-124", "sub-129", "sub-130")   # os 4 do Mentalab


# =========================================================================
# Fabricação de EDF
# =========================================================================

_DMIN, _DMAX = -32768, 32767


def _txt(valor, largura: int) -> bytes:
    s = str(valor)
    if len(s) > largura:
        s = s[:largura]
    return s.ljust(largura).encode("latin-1")


def _num(valor: float, largura: int = 8) -> bytes:
    """Número no campo EDF, com o máximo de precisão que couber."""
    s = f"{valor:g}"
    if len(s) > largura:
        s = f"{valor:.{max(largura - 7, 1)}f}"[:largura]
    return s.ljust(largura).encode("latin-1")


class Canal:
    def __init__(self, rotulo: str, dim: str, nsamp: int,
                 pmin: float, pmax: float, valores: np.ndarray):
        self.rotulo, self.dim, self.nsamp = rotulo, dim, nsamp
        self.pmin, self.pmax = float(pmin), float(pmax)
        self.valores = np.asarray(valores, dtype=float)

    def digitais(self, n_reg: int) -> np.ndarray:
        ganho = (self.pmax - self.pmin) / (_DMAX - _DMIN)
        desloc = self.pmin - _DMIN * ganho
        v = self.valores
        alvo = self.nsamp * n_reg
        if v.shape[0] != alvo:
            v = np.resize(v, alvo)
        d = np.rint((v - desloc) / ganho)
        return np.clip(d, _DMIN, _DMAX).astype("<i2").reshape(n_reg, self.nsamp)


def escrever_edf(caminho: Path, canais: list[Canal], n_reg: int, dur_s: float = 30.0) -> Path:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    ns = len(canais)
    cab = bytearray()
    cab += _txt("0", 8)                       # versão
    cab += _txt("X X X TESTE", 80)            # paciente
    cab += _txt("Startdate X X X X", 80)      # gravação
    cab += _txt("01.01.24", 8)
    cab += _txt("22.00.00", 8)
    cab += _txt(256 * (ns + 1), 8)            # bytes de cabeçalho
    cab += _txt("EDF+C", 44)                  # reservado
    cab += _txt(n_reg, 8)
    cab += _txt(f"{dur_s:g}", 8)
    cab += _txt(ns, 4)
    assert len(cab) == 256, len(cab)

    for c in canais:
        cab += _txt(c.rotulo, 16)
    for _ in canais:
        cab += _txt("", 80)                   # transdutor
    for c in canais:
        cab += _txt(c.dim, 8)
    for c in canais:
        cab += _num(c.pmin)
    for c in canais:
        cab += _num(c.pmax)
    for _ in canais:
        cab += _txt(_DMIN, 8)
    for _ in canais:
        cab += _txt(_DMAX, 8)
    for _ in canais:
        cab += _txt("", 80)                   # pré-filtragem
    for c in canais:
        cab += _txt(c.nsamp, 8)
    for _ in canais:
        cab += _txt("", 32)                   # reservado
    assert len(cab) == 256 * (ns + 1), len(cab)

    blocos = [c.digitais(n_reg) for c in canais]
    dados = np.concatenate([b.reshape(n_reg, -1) for b in blocos], axis=1)
    with open(caminho, "wb") as fh:
        fh.write(bytes(cab))
        fh.write(dados.astype("<i2").tobytes())
    return caminho


# --- canais prontos, com os valores REAIS conferidos no dataset -----------

def _accel(rotulo: str, dim: str, nsamp: int, pmin: float, pmax: float,
           n_reg: int, mag_g: float, escala: float, rng) -> Canal:
    """Um eixo de acelerômetro com magnitude ~`mag_g` na unidade do canal."""
    n = nsamp * n_reg
    v = (mag_g / np.sqrt(3.0) + rng.normal(0, 0.01, n)) * escala
    return Canal(rotulo, dim, nsamp, pmin, pmax, v)


def canais_zmax(n_reg: int, rng) -> list[Canal]:
    # 256 Hz -> 7680 amostras por registro de 30 s. Unidade `g`, faixa ±2 g.
    return [_accel(f"Zmax_ACC{e}", "g", 7680, -2.0, 1.999023, n_reg, 1.0, 1.0, rng)
            for e in "XYZ"]


def canais_empatica(n_reg: int, rng, dim: str = "g/64") -> list[Canal]:
    # 32 Hz -> 960 amostras. Unidade `g/64`, inteiro de 8 bits: -128..127.
    return [_accel(f"Emp_ACC{e}", dim, 960, -128.0, 127.0, n_reg, 1.0, 64.0, rng)
            for e in "XYZ"]


def canais_activpal(n_reg: int, rng) -> list[Canal]:
    # 20 Hz -> 600 amostras. Unidade `g`.
    return [_accel(f"ActivPal_ACC{e}", "g", 600, -3.96875, 3.984375, n_reg, 1.0, 1.0, rng)
            for e in "XYZ"]


def canal_rotulo(rotulo: str, n_reg: int, valores: np.ndarray) -> Canal:
    # 1 amostra por registro de 30 s. min -1 (não pontuável), max 4 (REM).
    return Canal(rotulo, "Unitless", 1, -1.0, 4.0, valores.astype(float))


def canal_psg_move(n_reg: int, rng) -> Canal:
    """`PSG_Move.` — ARMADILHA: tipo ACCEL no .tsv, mas 128 Hz e NÃO é posição."""
    return Canal("PSG_Move.", "mg", 3840, 0.0, 933.9131,
                 rng.uniform(0, 900, 3840 * n_reg))


def canal_postura(n_reg: int, rng) -> Canal:
    return Canal("PSG_Pos.", "position", 120, 1.0, 6.0,
                 rng.integers(1, 7, 120 * n_reg).astype(float))


def canal_annot(n_reg: int) -> Canal:
    return Canal("EDF Annotations", "", 57, -1.0, 1.0, np.zeros(57 * n_reg))


def _rotulos_realistas(n_reg: int, rng) -> np.ndarray:
    """Vigília nas pontas, sono no meio, alguns -1. Como uma noite de PSG."""
    y = rng.choice([1, 2, 2, 3, 4], size=n_reg).astype(int)
    y[: max(1, n_reg // 10)] = 0
    y[-max(1, n_reg // 10):] = 0
    if n_reg > 20:
        y[n_reg // 2] = -1           # época não pontuável
    return y


def montar_sujeito(
    raiz: Path,
    sujeito: str,
    n_reg: int = 20,
    com_pulso: bool = True,
    com_coxa: bool = True,
    com_scor2: bool = True,
    dim_empatica: str = "g/64",
    dur_s: float = 30.0,
    seed: int = 0,
) -> tuple[Path, np.ndarray]:
    """Monta a árvore BIDS de um sujeito. Devolve (caminho, rotulos_crus)."""
    rng = np.random.default_rng(seed)
    y = _rotulos_realistas(n_reg, rng)

    canais: list[Canal] = []
    canais += canais_zmax(n_reg, rng)
    canais.append(canal_postura(n_reg, rng))
    canais.append(canal_psg_move(n_reg, rng))          # a armadilha dos 128 Hz
    canais.append(canal_rotulo("PSG_Manual_Scor1", n_reg, y))
    canais.append(canal_rotulo("PSG_USleep_score", n_reg, y))
    if com_pulso:
        canais += canais_empatica(n_reg, rng, dim=dim_empatica)
    if com_coxa:
        canais += canais_activpal(n_reg, rng)
    if com_scor2:
        # O 2º pontuador discorda em algumas épocas — é o que dá o teto
        # inter-avaliador. Aqui, discorda numa.
        #
        # A divergência TEM de cruzar vigília↔sono (0 vs 1-4), não só trocar
        # de estágio dentro do sono (1↔2, p.ex.): o carregador reduz os
        # rótulos a binário sono/vigília, e N1 e N2 são ambos "sono" — uma
        # troca 1↔2 nunca aparece depois da redução, para nenhuma seed.
        y2 = y.copy()
        if n_reg > 5:
            y2[3] = 0 if y2[3] != 0 else 2
        canais.append(canal_rotulo("PSG_Manual_Scor2", n_reg, y2))
    canais.append(canal_annot(n_reg))

    pnp = raiz / SUBPASTA_PLUGNPLAY
    edf = pnp / sujeito / "eeg" / f"{sujeito}_task-sleep_eeg.edf"
    escrever_edf(edf, canais, n_reg, dur_s=dur_s)

    # Sidecar `channels.tsv` com a grafia MINÚSCULA do dataset real — e
    # declarando `scor2` mesmo quando o EDF não tem (ARMADILHA 4).
    tsv = edf.with_name(f"{sujeito}_task-sleep_channels.tsv")
    linhas = ["name\ttype\tunits\tsampling_frequency\tmax_val\tmin_val\tduration\tdescription"]
    for c in canais:
        if c.rotulo == "EDF Annotations":
            continue
        nome_tsv = c.rotulo.replace("Scor", "scor")   # o .tsv usa s minúsculo
        linhas.append(
            f"{nome_tsv}\tACCEL\t{c.dim}\t{c.nsamp / dur_s}\t{c.pmax}\t{c.pmin}"
            f"\t{n_reg * dur_s}\tDevice: teste"
        )
    if not com_scor2:
        linhas.append(
            f"PSG_Manual_scor2\tMISC\tUnitless\t{1 / dur_s}\t4.0\t-1.0"
            f"\t{n_reg * dur_s}\tDevice: teste"   # o .tsv MENTE — ARMADILHA 4
        )
    tsv.write_text("\n".join(linhas) + "\n", encoding="utf-8")
    return edf, y


@pytest.fixture
def colecao(tmp_path: Path) -> Path:
    """Uma mini-coleção com a mesma topologia de ausências do dataset real."""
    raiz = tmp_path / "wearanize"
    montar_sujeito(raiz, "sub-001", com_pulso=False, seed=1)                 # sem Empatica
    montar_sujeito(raiz, "sub-004", com_pulso=False, com_coxa=False, seed=4)  # sem os dois
    montar_sujeito(raiz, "sub-005", seed=5)                                  # completo
    montar_sujeito(raiz, "sub-007", seed=7)                                  # completo
    montar_sujeito(raiz, "sub-115", com_scor2=False, seed=115)               # Mentalab
    (raiz / SUBPASTA_PLUGNPLAY / "participants.tsv").write_text(
        "participant_id\tage\tgender\thandedness\n"
        "sub-001\t21\tM\tR\nsub-004\t23\tF\tR\nsub-005\t28\tF\tR\n"
        "sub-007\t18\tM\tL\nsub-115\t21\tF\tR\n",
        encoding="utf-8",
    )
    return raiz


# =========================================================================
# Cabeçalho EDF
# =========================================================================

def test_cabecalho_edf_bate_com_a_estrutura_real(colecao: Path):
    """O leitor de EDF entende o layout — e o layout é o do arquivo real."""
    edf = colecao / SUBPASTA_PLUGNPLAY / "sub-005" / "eeg" / "sub-005_task-sleep_eeg.edf"
    cab = ler_cabecalho_edf(edf)

    assert cab.bytes_cabecalho == 256 * (cab.n_sinais + 1)
    assert cab.duracao_registro_s == 30.0
    # A conta que valida tudo: o tamanho previsto pelo cabeçalho é o tamanho do
    # arquivo. No sub-005 real: 12 544 + 974 * 513 300 = 499 966 744 B.
    previsto = cab.bytes_cabecalho + cab.n_registros * cab.amostras_totais_por_registro * 2
    assert previsto == edf.stat().st_size

    i = cab.rotulos.index("Zmax_ACCX")
    assert cab.taxa_hz(i) == pytest.approx(256.0)


def test_taxas_por_posicao(colecao: Path):
    """256 / 32 / 20 Hz — as três taxas conferidas nos 100 sujeitos reais."""
    edf = colecao / SUBPASTA_PLUGNPLAY / "sub-005" / "eeg" / "sub-005_task-sleep_eeg.edf"
    cab = ler_cabecalho_edf(edf)
    for chave, esperada in (("cabeca", 256.0), ("pulso", 32.0), ("coxa", 20.0)):
        canal = POSICOES[chave].canais[0]
        assert cab.taxa_hz(cab.rotulos.index(canal)) == pytest.approx(esperada)
        assert POSICOES[chave].taxa_hz == esperada


# =========================================================================
# ARMADILHA 1 — grafia do canal de rótulo
# =========================================================================

def test_rotulo_encontrado_apesar_do_S_maiusculo(colecao: Path):
    """`PSG_Manual_Scor1` no EDF vs `scor1` no .tsv.

    Casar nome de canal com `==` sensível a maiúscula perde o rótulo — e o
    sintoma não é uma exceção, é zero época. Este teste é a guarda disso.
    """
    edf = colecao / SUBPASTA_PLUGNPLAY / "sub-005" / "eeg" / "sub-005_task-sleep_eeg.edf"
    cab = ler_cabecalho_edf(edf)
    assert "PSG_Manual_Scor1" in cab.rotulos          # EDF: S maiúsculo
    assert "PSG_Manual_scor1" not in cab.rotulos      # a grafia do .tsv NÃO está no EDF

    tsv = edf.with_name("sub-005_task-sleep_channels.tsv").read_text(encoding="utf-8")
    assert "PSG_Manual_scor1" in tsv                  # .tsv: s minúsculo
    assert "PSG_Manual_Scor1" not in tsv

    # Apesar da divergência, o carregador acha o rótulo:
    gr = next(carregar_wearanize("cabeca", pasta=colecao, sujeitos=["sub-005"]))
    assert gr.rotulos.shape[0] == cab.n_registros
    assert set(np.unique(gr.rotulos)) <= {-1, 0, 1}


# =========================================================================
# ARMADILHA 2 — unidade do Empatica
# =========================================================================

def test_empatica_convertido_de_g64_para_g(colecao: Path):
    """|a| tem de dar ~1 g. Sem a divisão por 64 daria ~64 g."""
    gr = next(carregar_wearanize("pulso", pasta=colecao, sujeitos=["sub-005"]))
    mag = np.linalg.norm(gr.a, axis=1)
    assert mag.mean() == pytest.approx(1.0, abs=0.1), (
        f"magnitude média {mag.mean():.2f} g — se estiver perto de 64, a "
        "conversão g/64 -> g não foi aplicada (ARMADILHA 2)"
    )
    assert gr.meta["fator_para_g"] == pytest.approx(1.0 / 64.0)
    assert gr.meta["unidade_edf"] == "g/64"


def test_cabeca_e_coxa_nao_sao_reescalados(colecao: Path):
    """Zmax e ActivPAL já vêm em `g` — dividir por 64 aqui seria o erro oposto."""
    for posicao in ("cabeca", "coxa"):
        gr = next(carregar_wearanize(posicao, pasta=colecao, sujeitos=["sub-005"]))
        assert gr.meta["fator_para_g"] == 1.0
        assert np.linalg.norm(gr.a, axis=1).mean() == pytest.approx(1.0, abs=0.1)


def test_rejeita_versao_v1_0_com_unidade_errada(tmp_path: Path):
    """Um arquivo que declare `g/16` é a v1.0 restrita — fator 4 de erro.

    Falhar alto é muito melhor que rodar a matriz de transferência inteira
    sobre um artefato de escala no braço 'treina'.
    """
    raiz = tmp_path / "v10"
    montar_sujeito(raiz, "sub-005", dim_empatica="g/16", seed=5)
    with pytest.raises(ValueError, match=r"g/16"):
        next(carregar_wearanize("pulso", pasta=raiz, sujeitos=["sub-005"]))


# =========================================================================
# ARMADILHA 3 — sensores ausentes
# =========================================================================

def test_sujeito_sem_empatica_e_pulado_sem_abortar(colecao: Path, capsys):
    """8 dos 100 não têm pulso. Não podem derrubar os 92 que têm."""
    gravacoes = list(carregar_wearanize("pulso", pasta=colecao))
    ids = [g.id_sujeito for g in gravacoes]
    assert "sub-001" not in ids and "sub-004" not in ids   # sem Empatica
    assert "sub-005" in ids and "sub-007" in ids
    assert "sem o sensor" in capsys.readouterr().err


def test_sujeito_sem_activpal_e_pulado(colecao: Path):
    ids = [g.id_sujeito for g in carregar_wearanize("coxa", pasta=colecao)]
    assert "sub-004" not in ids                            # sem ActivPAL
    assert {"sub-001", "sub-005", "sub-007"} <= set(ids)


def test_cabeca_existe_em_todos(colecao: Path):
    """100/100 têm Zmax — inclusive os que não têm nenhum outro sensor."""
    ids = {g.id_sujeito for g in carregar_wearanize("cabeca", pasta=colecao)}
    assert ids == set(sujeitos_disponiveis(colecao))


def test_intersecao_para_a_matriz_3x3(colecao: Path):
    """As 9 células do ML-03 têm de rodar sobre o MESMO conjunto de sujeitos."""
    so_pulso = sujeitos_com_posicoes(["pulso"], pasta=colecao)
    tres = sujeitos_com_posicoes(["cabeca", "pulso", "coxa"], pasta=colecao)
    assert set(tres) <= set(so_pulso)
    assert "sub-004" not in tres and "sub-001" not in tres
    assert {"sub-005", "sub-007"} <= set(tres)

    # O uso real: mesmo N nas duas pontas da transferência.
    treino = list(carregar_wearanize("pulso", pasta=colecao, sujeitos=tres))
    teste = list(carregar_wearanize("cabeca", pasta=colecao, sujeitos=tres))
    assert [g.id_sujeito for g in treino] == [g.id_sujeito for g in teste]


def test_posicao_desconhecida_levanta(colecao: Path):
    with pytest.raises(ValueError, match="posição desconhecida"):
        next(carregar_wearanize("tornozelo", pasta=colecao))


# =========================================================================
# ARMADILHA 4 — o .tsv mente sobre o segundo pontuador
# =========================================================================

def test_tsv_declara_scor2_que_o_edf_nao_tem(colecao: Path):
    """A discrepância existe no dataset real em 4 sujeitos. Aqui, no sub-115."""
    edf = colecao / SUBPASTA_PLUGNPLAY / "sub-115" / "eeg" / "sub-115_task-sleep_eeg.edf"
    tsv = edf.with_name("sub-115_task-sleep_channels.tsv").read_text(encoding="utf-8")
    assert "PSG_Manual_scor2" in tsv                              # o .tsv declara
    assert "PSG_Manual_Scor2" not in ler_cabecalho_edf(edf).rotulos  # o EDF não tem


def test_pontuador_2_pula_quem_nao_tem(colecao: Path, capsys):
    com_1 = {g.id_sujeito for g in carregar_wearanize("cabeca", pasta=colecao, pontuador=1)}
    com_2 = {g.id_sujeito for g in carregar_wearanize("cabeca", pasta=colecao, pontuador=2)}
    assert "sub-115" in com_1
    assert "sub-115" not in com_2
    assert com_2 < com_1
    assert "PSG_Manual_Scor2" in capsys.readouterr().err


def test_dois_pontuadores_discordam(colecao: Path):
    """É o teto inter-avaliador — o número contra o qual o Δκ deve ser lido."""
    g1 = next(carregar_wearanize("cabeca", pasta=colecao, sujeitos=["sub-005"], pontuador=1))
    g2 = next(carregar_wearanize("cabeca", pasta=colecao, sujeitos=["sub-005"], pontuador=2))
    assert g1.rotulos.shape == g2.rotulos.shape
    assert not np.array_equal(g1.rotulos, g2.rotulos)
    assert g1.meta["canal_rotulo"] == "PSG_Manual_Scor1"
    assert g2.meta["canal_rotulo"] == "PSG_Manual_Scor2"


def test_pontuador_invalido(colecao: Path):
    with pytest.raises(ValueError, match="pontuador"):
        next(carregar_wearanize("cabeca", pasta=colecao, pontuador=3))


# =========================================================================
# ARMADILHA 5 — nº de canais varia; e o PSG_Move. a 128 Hz
# =========================================================================

def test_numero_de_canais_varia_entre_sujeitos(colecao: Path):
    """No dataset real vai de 38 a 61. Indexar por posição fixa quebra."""
    n = {}
    for s in sujeitos_disponiveis(colecao):
        edf = colecao / SUBPASTA_PLUGNPLAY / s / "eeg" / f"{s}_task-sleep_eeg.edf"
        n[s] = ler_cabecalho_edf(edf).n_sinais
    assert len(set(n.values())) > 1, f"os sujeitos deveriam diferir: {n}"


def test_psg_move_nao_e_confundido_com_acelerometro(colecao: Path):
    """`PSG_Move.` tem tipo ACCEL no .tsv e está a **128 Hz**, não 4 Hz como diz
    o README oficial. Não é posição de sensor e não pode ser escolhido."""
    edf = colecao / SUBPASTA_PLUGNPLAY / "sub-005" / "eeg" / "sub-005_task-sleep_eeg.edf"
    cab = ler_cabecalho_edf(edf)
    assert cab.taxa_hz(cab.rotulos.index("PSG_Move.")) == pytest.approx(128.0)

    nomes = {c for p in POSICOES.values() for c in p.canais}
    assert "PSG_Move." not in nomes

    gr = next(carregar_wearanize("cabeca", pasta=colecao, sujeitos=["sub-005"]))
    assert gr.meta["taxa_origem_hz"] == pytest.approx(256.0)   # não 128
    assert gr.meta["canais"] == ("Zmax_ACCX", "Zmax_ACCY", "Zmax_ACCZ")


# =========================================================================
# Estrutura: um registro = uma época = um rótulo
# =========================================================================

def test_um_registro_uma_epoca_um_rotulo(colecao: Path):
    """A propriedade que elimina a classe de bug de alinhamento do Newcastle."""
    edf = colecao / SUBPASTA_PLUGNPLAY / "sub-005" / "eeg" / "sub-005_task-sleep_eeg.edf"
    cab = ler_cabecalho_edf(edf)
    gr = next(carregar_wearanize("cabeca", pasta=colecao, sujeitos=["sub-005"]))

    assert gr.epoca_rotulo_s == 30.0
    assert gr.t0_rotulo == 0.0             # não é suposição: é a estrutura
    assert gr.rotulos.shape[0] == cab.n_registros
    # Amostras e rótulos cobrem exatamente a mesma janela de tempo.
    assert gr.t[-1] + 1 / 256.0 == pytest.approx(cab.n_registros * 30.0)


def test_registro_com_duracao_diferente_de_30s_levanta(tmp_path: Path):
    raiz = tmp_path / "errado"
    montar_sujeito(raiz, "sub-005", dur_s=20.0, seed=5)
    with pytest.raises(ValueError, match="uma época"):
        next(carregar_wearanize("cabeca", pasta=raiz, sujeitos=["sub-005"]))


# =========================================================================
# Rótulos
# =========================================================================

def test_mapa_de_rotulo_aasm(colecao: Path):
    """-1 descarta · 0 vigília · 1..4 (N1,N2,N3,REM) viram sono.

    Estadiamento está fora por limite FÍSICO (§0.4): REM e N3 são ambos estados
    quietos e um acelerômetro não os distingue.
    """
    _, y_cru = montar_sujeito(colecao, "sub-900", n_reg=40, seed=900)
    gr = next(carregar_wearanize("cabeca", pasta=colecao, sujeitos=["sub-900"]))
    esperado = np.array([-1 if v < 0 else (0 if v == 0 else 1) for v in y_cru])
    assert np.array_equal(gr.rotulos, esperado)
    assert (gr.rotulos == -1).sum() == (y_cru == -1).sum()


def test_rotulo_arredondado_apos_escala_edf(colecao: Path):
    """O escalonamento EDF é de ponto flutuante: 2 volta como 1,9999847...

    Sem `np.rint` o mapa de rótulo erra a chave e tudo viraria inválido — em
    silêncio. Este teste garante que os valores são inteiros exatos.
    """
    gr = next(carregar_wearanize("cabeca", pasta=colecao, sujeitos=["sub-005"]))
    assert gr.rotulos.dtype.kind in "iu"
    assert set(np.unique(gr.rotulos)) <= {-1, 0, 1}


def test_rotulo_fora_do_mapa_levanta(tmp_path: Path):
    """Um valor de estágio inesperado é erro, não é 'descarta e segue'."""
    raiz = tmp_path / "rotulo_ruim"
    rng = np.random.default_rng(0)
    n_reg = 10
    canais = canais_zmax(n_reg, rng)
    canais.append(Canal("PSG_Manual_Scor1", "Unitless", 1, -1.0, 9.0,
                        np.full(n_reg, 9.0)))       # 9 não existe no AASM
    canais.append(canal_annot(n_reg))
    edf = raiz / SUBPASTA_PLUGNPLAY / "sub-005" / "eeg" / "sub-005_task-sleep_eeg.edf"
    escrever_edf(edf, canais, n_reg)
    with pytest.raises(ValueError, match="fora do mapa"):
        next(carregar_wearanize("cabeca", pasta=raiz, sujeitos=["sub-005"]))


# =========================================================================
# Robustez
# =========================================================================

def test_arquivo_truncado_e_detectado(colecao: Path):
    """Download interrompido não pode virar resultado. Tem de virar exceção."""
    edf = colecao / SUBPASTA_PLUGNPLAY / "sub-007" / "eeg" / "sub-007_task-sleep_eeg.edf"
    dados = edf.read_bytes()
    edf.write_bytes(dados[: len(dados) // 2])
    with pytest.raises(ValueError, match="truncado"):
        next(carregar_wearanize("cabeca", pasta=colecao, sujeitos=["sub-007"]))


def test_pasta_vazia_da_instrucao_de_download(tmp_path: Path):
    with pytest.raises(FileNotFoundError, match="baixar_wearanize"):
        next(carregar_wearanize("cabeca", pasta=tmp_path / "nada"))


def test_aceita_a_pasta_do_plugnplay_direto(colecao: Path):
    """Tolerância a quem aponta para dentro em vez de para a raiz."""
    dentro = colecao / SUBPASTA_PLUGNPLAY
    assert sujeitos_disponiveis(dentro) == sujeitos_disponiveis(colecao)


# =========================================================================
# Interface única
# =========================================================================

def test_carregar_registra_posicao_no_meta(colecao: Path):
    """Um resultado do ML-03 sem a posição registrada é um resultado sem sentido."""
    conj = carregar(
        "wearanize", posicao="pulso", pasta=colecao, sujeitos=["sub-005", "sub-007"]
    )
    assert conj.meta["dataset"] == "wearanize"
    assert conj.meta["posicao"] == "pulso"
    assert conj.meta["pontuador"] == 1
    assert len(conj) > 0
    assert conj.X.shape[0] == conj.y.shape[0] == conj.id_sujeito.shape[0]
    assert set(np.unique(conj.y)) <= {0, 1}          # -1 já foi removido
    assert set(conj.id_sujeito) == {"sub-005", "sub-007"}


def test_wearanize_esta_no_dispatcher():
    from src.carregar import DATASETS
    assert "wearanize" in DATASETS


def test_opcao_de_posicao_rejeitada_nos_outros_datasets():
    """Passar `posicao=` para o Newcastle é engano — e tem de doer, não ser
    ignorado em silêncio."""
    with pytest.raises(TypeError, match="posicao"):
        carregar("newcastle", posicao="pulso")
    with pytest.raises(TypeError):
        carregar("sintetico", posicao="cabeca")


def test_opcao_desconhecida_no_wearanize(colecao: Path):
    """Erro de digitação em nome de opção tem de doer, não virar default silencioso."""
    with pytest.raises(TypeError, match="desconhecidas"):
        carregar("wearanize", pasta=colecao, posicaoo="pulso")


# =========================================================================
# Censo — a documentação e o código não podem se separar
# =========================================================================

def test_censo_real_coerente():
    """Os números medidos no dataset real, travados contra si mesmos.

    Não lê disco. Existe para que uma revisão futura do dataset não deixe a
    documentação dizendo 92 enquanto o dado diz outra coisa.
    """
    c = CENSO_REAL
    assert c["cabeca"] == c["n_sujeitos_plugnplay"] == 100
    assert c["cabeca_e_pulso"] == c["pulso"] == 92
    assert c["tres_posicoes"] <= min(c["cabeca"], c["pulso"], c["coxa"])
    assert c["scor2"] == c["usleep"] == 96
    assert len(SEM_PULSO) == c["n_sujeitos_plugnplay"] - c["pulso"] == 8
    assert len(SEM_COXA) == c["n_sujeitos_plugnplay"] - c["coxa"] == 7
    assert len(SEM_SCOR2) == c["n_sujeitos_plugnplay"] - c["scor2"] == 4
    # Os 4 sem 2º pontuador são os do Mentalab, e 2 deles também não têm pulso.
    assert set(SEM_SCOR2) & set(SEM_PULSO) == {"sub-129", "sub-130"}
