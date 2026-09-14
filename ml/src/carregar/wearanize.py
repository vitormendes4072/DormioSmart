"""Carregador do Wearanize+ OA (Zmax cabeça · Empatica E4 pulso · ActivPAL coxa).

Fonte
-----
Dados : Radboud Data Repository, coleção **aberta** `Wearanize+ OA`
        DOI 10.34973/xrmf-5726 · **CC-BY-4.0** · sem cadastro, sem DUA
        https://data.ru.nl/collections/di/dcmn/DSC_wrnzpoa_t0000925a_195
        Versão usada: `Wearanize+_OA_PlugNPlay_v1.1` (EEG-BIDS, um EDF por sujeito)
Artigo : Sikder, N.; Verkaar, L.; Paltarzhytskaya, A.; Acan, S.; Bovy, L.;
        Almazova, T.; Krugliakova, E.; Rosenblum, Y.; Krauledat, M.;
        Dresler, M.; Zerr, P. (2026). *Wearanize+: a multimodal dataset for
        evaluating wearable technologies in sleep research.* SLEEP Advances
        7(1), zpaf094. doi:10.1093/sleepadvances/zpaf094

⚠️ **Citação obrigatória** (README oficial + descrição da coleção): citar o
artigo **e** o dataset primário `10.34973/j6jf-9e62`, mesmo usando só a OA.
⚠️ **Uso científico apenas; não tentar reidentificar participante; não
redistribuir.** O `dados/` é gitignored — isso não é higiene, é condição de uso.

Por que este dataset existe no projeto
--------------------------------------
É a **única base pública com acelerômetro na cabeça e PSG pontuada na mesma
noite**. A cabeça é o proxy cinemático mais próximo de um sensor em travesseiro,
que é o que o Dormio usa. Três posições + os mesmos rótulos + a mesma noite é o
que permite o `ML-03`: treinar no pulso, testar na cabeça, **medir a queda de
kappa** em vez de declarar a transferência como limitação.

✅ Tudo abaixo foi **verificado nos arquivos reais** em 2026-09-14 (via WebDAV
anônimo), não lido em documentação. Onde a documentação oficial diverge do
arquivo, o arquivo venceu — e a divergência está registrada como ARMADILHA.

=============================================================================
ARMADILHA 1 — o nome do canal de rótulo difere entre o `.tsv` e o EDF
=============================================================================
O sidecar BIDS `sub-NNN_task-sleep_channels.tsv` grafa `PSG_Manual_scor1` e
`PSG_Manual_scor2` (s minúsculo). **Dentro do EDF os rótulos são
`PSG_Manual_Scor1` e `PSG_Manual_Scor2` (S MAIÚSCULO).** Conferido nos 100
sujeitos: o EDF usa `Scor`, sem exceção, e `PSG_USleep_score` com `s` minúsculo.

Casar nome de canal com `==` sensível a maiúscula pega o acelerômetro e **perde
o rótulo** — e sem rótulo o carregador não levanta erro óbvio, ele só devolve
zero época. Por isso toda busca de canal aqui passa por `_indice_canal()`, que
compara em minúsculas.

=============================================================================
ARMADILHA 2 — a unidade do Empatica E4 é `g/64`, NÃO `g`
=============================================================================
O canal `Emp_ACC*` é gravado na codificação nativa do aparelho: inteiro de
**8 bits com sinal** (−128 a +127) em unidades de **1/64 g**. Logo:

    aceleracao_g = valor_do_edf / 64.0

Ignorar isso dá aceleração **64× maior** — magnitude de repouso ~65 g em vez de
~1 g. Verificado no `sub-005`, registro 500: com a divisão, |a| = 1,025 g; sem
ela, 65,6 g.

⚠️ **E há uma segunda camada nesta armadilha, que é a razão de usarmos a
coleção ABERTA e não a restrita.** Os autores documentam que a versão
`PlugNPlay v1.0` — a que está na coleção **restrita**, atrás do DUA — declara
essa unidade **errada, como `g/16`**. Citando o README oficial:

    "Files in PlugNPlay v1.0 state this unit as g/16. However, the actual unit
     is g/64 (same as the source). The units were fixed in PlugNPlay v1.1."

Ou seja: na v1.0 a aceleração de **pulso** sai com **fator 4 de erro**. O pulso
é justamente o braço "treina" do `ML-03` — o experimento inteiro mediria um
artefato de escala em vez da transferência entre posições. A **v1.1 (OA)** está
correta, e é a que este módulo lê. `_conferir_unidade_empatica()` aborta se
encontrar um arquivo que declare `g/16`, em vez de silenciosamente produzir
números 4× errados.

=============================================================================
ARMADILHA 3 — nem todo sujeito tem os três sensores
=============================================================================
Censo lido nos cabeçalhos EDF dos 100 sujeitos do PlugNPlay v1.1:

    Zmax (cabeça)      100/100
    Empatica (pulso)    92/100   faltam sub-001, 002, 004, 063, 064, 100, 129, 130
    ActivPAL (coxa)     93/100   faltam sub-004, 072, 075, 076, 095, 096, 106

    cabeça + pulso            92   ← o N do experimento principal do ML-03
    as três posições          86   ← o N da matriz 3x3 completa

**Consequência metodológica que precisa ir para o TCC:** para a matriz 3x3 ser
comparável entre células, as nove têm de rodar sobre o MESMO conjunto de
sujeitos — os 86. Variar o N por célula torna as quedas de kappa incomparáveis
entre si. Use `sujeitos_com_posicoes()` para obter essa interseção.

Um sujeito sem o sensor pedido é **pulado com aviso em stderr**, nunca com
exceção: pedir "pulso" não pode abortar a noite dos 92 que têm pulso por causa
dos 8 que não têm.

=============================================================================
ARMADILHA 4 — o `channels.tsv` MENTE sobre o segundo pontuador
=============================================================================
Esta só apareceu comparando o sidecar com o EDF, e não está documentada em
lugar nenhum do dataset.

    `channels.tsv` declara `PSG_Manual_scor2` para  **100**/100 sujeitos
    o EDF contém de fato   `PSG_Manual_Scor2` em     **96**/100

Os 4 ausentes são `sub-115`, `sub-124`, `sub-129`, `sub-130` — exatamente os
gravados com **Mentalab** em vez de SOMNOscreen, e exatamente os mesmos que não
têm `PSG_USleep_score` nem `PSG_Pos.`. Bate com a versão `raw` da coleção, cujo
diretório `2.Sleep_scores/2.PSG_manual_scores_scorer2/` tem 96 arquivos contra
103 do pontuador 1.

**Portanto: o teto inter-avaliador é N = 96, não 100.** Um pipeline que
confiasse no `.tsv` para montar a lista de sujeitos quebraria em 4 deles —
por isso este módulo lê a disponibilidade **do EDF**, nunca do sidecar.

=============================================================================
ARMADILHA 5 — o número de canais varia por sujeito (38 a 61)
=============================================================================
Medido: 38, 41, 45, 47, 48, 49, 54 e 61 canais, conforme o sujeito. Depende de
quais wearables funcionaram e de qual PSG foi usada (SOMNOscreen usa montagem
10–20; Mentalab usa 10–10, com muito mais eletrodos).

**Nunca indexar canal por posição fixa.** Sempre por nome, via `_indice_canal`.

=============================================================================
O que este dataset dá de graça — e o Newcastle não dava
=============================================================================
1. **A época de 30 s já vem pronta na estrutura do arquivo.** O registro de
   dados do EDF tem `duração = 30 s` (conferido: 30 nos 100 sujeitos) e os
   canais de pontuação têm **1 amostra por registro**. Um registro = uma época
   = um rótulo. Não há `t0_rotulo` a calcular e não há como errar alinhamento —
   o que foi a ARMADILHA 5 inteira do `newcastle.py`. Aqui `t0_rotulo = 0.0`
   não é suposição: é a estrutura do arquivo.
2. **Duas pontuações manuais independentes** (nos 96): dá o **teto
   inter-avaliador**, que é o número contra o qual o Δκ do `ML-03` deve ser
   comparado.
3. **Postura de referência** em `PSG_Pos.` (4 Hz, 96 sujeitos): validação
   independente das features `inclinacao_rel` / `d_angulo`.

=============================================================================
CONTROLE EXPERIMENTAL — "cabeça degradada", para não confundir posição com
qualidade de sensor no ML-03
=============================================================================
A matriz de transferência ingênua (treina numa posição, testa noutra) mistura
duas variáveis: o Zmax da cabeça é 256 Hz / 12 bits / 0,977 mg-LSB; o Empatica
do pulso é 32 Hz / 8 bits / 15,625 mg-LSB — **16× mais grosseiro**. Treinar em
pulso e testar em cabeça muda a posição E a qualidade do sensor ao mesmo
tempo, e o Δκ que sai dali não se pode atribuir a nenhuma das duas sozinha.

`qualidade="e4"` em `carregar_wearanize()` isola as duas variáveis: reamostra
e requantiza o sinal pedido para a grade exata do Empatica E4 (via
`degradar_para_e4()`, que reusa o `reamostrar()` de `src/sinal.py` — o mesmo
anti-aliasing do resto do pipeline, não um atalho). Aplicado à cabeça, dá o
braço de controle:

  cabeça original   vs. cabeça degradada  →  custo da QUALIDADE, isolado
  pulso             vs. cabeça degradada  →  custo da POSIÇÃO, isolado —
                                              os dois lados na mesma qualidade
  cabeça original   vs. pulso             →  a matriz ingênua, continua
                                              reportada (é o que a
                                              literatura faria)

Aplicado ao próprio sinal do Empatica, `qualidade="e4"` tem de ser
**aproximadamente idempotente** — já está na grade que descreve; a única
mudança esperada é o resíduo de reamostrar 32→32 Hz (interpolação na mesma
grade, filtro não entra: `reamostrar()` só filtra quando a origem é mais
rápida que o destino). Ver `testes/test_wearanize.py::test_degradar_e4_e_quase_idempotente`.

**A cabeça degradada é também o proxy mais honesto do que o MPU6050 do
Dormio entregaria** — 16 bits nominal, mas a resolução que sobra depois de
qualquer bit de folga é mais perto da grade do E4 do que da do Zmax. Esse
número interessa duas vezes: como controle experimental E como estimativa de
desempenho esperado do dispositivo real.

=============================================================================
Especificações dos sensores — o que é lido e o que é DERIVADO
=============================================================================
| Sensor    | Taxa       | Unidade no EDF | Faixa   | Bits | Resolução     |
|-----------|-----------|----------------|---------|------|---------------|
| Zmax      | 256 Hz ✅  | `g` ✅          | ±2 g 🟢 | 12 🟢| 0,977 mg 🟢   |
| Empatica  | 32 Hz ✅   | `g/64` ✅       | ±2 g ✅  | 8 ✅ | 15,625 mg ✅  |
| ActivPAL  | 20 Hz ✅   | `g` ✅          | ±4 g 🟡 | 10 🟡| 7,8125 mg 🟢  |

✅ = lido do arquivo · 🟢 = derivado da grade de quantização observada nos 100
sujeitos · 🟡 = coerente com a grade, mas os extremos não encostam na trava.

⚠️ **Nenhum fabricante publica faixa/bits do Zmax nem do ActivPAL, e o
cabeçalho EDF NÃO serve para descobrir**: o pipeline de conversão do dataset
reescalou tudo para o span cheio de 16 bits do contêiner (`digital min/max` =
−32768/32767) e gravou em `physical min/max` os **extremos observados daquela
gravação**, diferentes por canal. No TCC, escrever "derivado dos arquivos do
dataset", jamais "segundo a folha de dados". Detalhe em
`docs/WEARANIZE-ACESSO.md` §6.2.
"""

from __future__ import annotations

import sys
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from ..sinal import reamostrar
from .base import Gravacao

__all__ = [
    "carregar_wearanize",
    "sujeitos_disponiveis",
    "sujeitos_com_posicoes",
    "degradar_para_e4",
    "POSICOES",
    "QUALIDADES",
    "PASTA_PADRAO",
]

PASTA_PADRAO = (
    Path(__file__).resolve().parents[2] / "dados" / "bruto" / "wearanize"
)

#: Subdiretório da coleção OA que este carregador lê. A versão `raw` tem os 130
#: participantes mas não é sincronizada; a `Parquet` é a mesma coisa em outro
#: contêiner. **PlugNPlay é a sincronizada e truncada** — é a que serve.
SUBPASTA_PLUGNPLAY = "Wearanize+_OA_PlugNPlay_v1.1"


@dataclass(frozen=True)
class Posicao:
    """Uma posição de sensor: canais, taxa e o fator que leva a unidade a `g`."""

    nome: str
    canais: tuple[str, str, str]
    taxa_hz: float
    #: Multiplicador para converter o valor do EDF em **g**. É 1/64 no Empatica
    #: (ARMADILHA 2) e 1,0 nos outros dois, que já vêm em `g`.
    para_g: float
    unidade_edf: str
    descricao: str


POSICOES: dict[str, Posicao] = {
    "cabeca": Posicao(
        nome="cabeca",
        canais=("Zmax_ACCX", "Zmax_ACCY", "Zmax_ACCZ"),
        taxa_hz=256.0,
        para_g=1.0,
        unidade_edf="g",
        descricao="Zmax (Hypnodyne), testeira — proxy do sensor em travesseiro",
    ),
    "pulso": Posicao(
        nome="pulso",
        canais=("Emp_ACCX", "Emp_ACCY", "Emp_ACCZ"),
        taxa_hz=32.0,
        para_g=1.0 / 64.0,  # ARMADILHA 2
        unidade_edf="g/64",
        descricao="Empatica E4, punho — a posição da actigrafia clássica",
    ),
    "coxa": Posicao(
        nome="coxa",
        canais=("ActivPal_ACCX", "ActivPal_ACCY", "ActivPal_ACCZ"),
        taxa_hz=20.0,
        para_g=1.0,
        unidade_edf="g",
        descricao="ActivPAL (PAL Technologies), coxa",
    ),
}

#: Canais de pontuação, na grafia do **EDF** (ARMADILHA 1 — `Scor` com S
#: maiúsculo; o `channels.tsv` usa `scor` minúsculo). A busca é insensível a
#: maiúsculas de qualquer forma; estes nomes são a referência documental.
CANAIS_ROTULO = {
    1: "PSG_Manual_Scor1",
    2: "PSG_Manual_Scor2",
    "usleep": "PSG_USleep_score",
}

CANAL_POSTURA = "PSG_Pos."

QUALIDADES: tuple[str, ...] = ("original", "e4")

#: Grade do Empatica E4 (ver `Posicao["pulso"]` acima): 8 bits com sinal,
#: 1/64 g por LSB, 32 Hz. `degradar_para_e4()` reproduz exatamente isto.
_E4_BITS = 8
_E4_LSB_G = 1.0 / 64.0                              # 15,625 mg
_E4_TAXA_HZ = 32.0
_E4_MIN_G = -(2 ** (_E4_BITS - 1)) * _E4_LSB_G       # -128/64 = -2,000 g
_E4_MAX_G = (2 ** (_E4_BITS - 1) - 1) * _E4_LSB_G    #  127/64 =  1,984375 g


def degradar_para_e4(t: np.ndarray, a: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Reamostra e requantiza `(t, a)` para a grade do Empatica E4.

    Ver "CONTROLE EXPERIMENTAL" no topo do módulo para o porquê. Duas etapas,
    nesta ordem:

    1. **Reamostrar para 32 Hz com anti-aliasing** — `reamostrar()` de
       `src/sinal.py`, o mesmo usado no resto do pipeline (a taxa de origem é
       derivada de `t`, não precisa ser passada). Decimar sem filtrar
       dobraria energia de alta frequência para dentro da banda; se a origem
       já estiver a <= 32 Hz, `reamostrar()` já sabe não filtrar.
    2. **Requantizar para 8 bits com sinal, 1/64 g por LSB, faixa ±2 g** —
       `round(a / LSB) * LSB`, com saturação nos extremos. É exatamente o que
       um ADC de 8 bits faz; sem a saturação, um pico acima de ±2 g na cabeça
       (a faixa do Zmax é maior) apareceria como um valor que o E4 nunca
       poderia ter produzido.

    Parameters
    ----------
    t, a : mesma forma de `Gravacao.t` / `.a` — `a` já em **g**.

    Returns
    -------
    (t_novo, a_novo) — `a_novo` na grade do E4: 32 Hz, valores múltiplos de
    1/64 g, saturados em [-2, 1,984375] g.
    """
    t_novo, a_novo = reamostrar(t, a, taxa_destino=_E4_TAXA_HZ)
    a_sat = np.clip(a_novo, _E4_MIN_G, _E4_MAX_G)
    a_quant = np.round(a_sat / _E4_LSB_G) * _E4_LSB_G
    return t_novo, a_quant

#: Rótulo do dataset -> convenção interna (0 = vigília, 1 = sono, -1 = descartar).
#: Mapa oficial: -1 não pontuável · 0 vigília · 1 N1 · 2 N2 · 3 N3 · 4 REM.
#: Estadiamento está fora de escopo por limite FÍSICO, não algorítmico (§0.4 do
#: ML-DATASETS-E-PLANO.md): REM e N3 são ambos estados quietos e um acelerômetro
#: não os distingue. Tudo que não é vigília vira sono.
_MAPA_ROTULO = {-1: -1, 0: 0, 1: 1, 2: 1, 3: 1, 4: 1}

EPOCA_S = 30.0


# =========================================================================
# Leitor EDF/EDF+ mínimo
# =========================================================================
# Sem dependência nova: o projeto já implementa o leitor proprietário do
# GENEActiv em `newcastle.py` pelo mesmo motivo. `mne` e `pyedflib` resolveriam,
# mas trariam árvores de dependência grandes para ler um formato que são ~60
# linhas de struct. As versões PINADAS do requirements.txt continuam valendo.
#
# Layout do cabeçalho EDF (EDF+ é compatível):
#   bytes   0..7    versão
#           8..87   identificação do paciente
#          88..167  identificação da gravação
#         168..175  data de início (dd.mm.yy)
#         176..183  hora de início (hh.mm.ss)
#         184..191  nº de bytes do cabeçalho  ( = 256 * (ns + 1) )
#         192..235  reservado
#         236..243  nº de registros de dados
#         244..251  duração de um registro, em segundos
#         252..255  nº de sinais (ns)
#   depois, por sinal e nesta ordem:
#         16*ns  rótulo        80*ns  transdutor     8*ns  dimensão física
#          8*ns  mínimo físico  8*ns  máximo físico  8*ns  mínimo digital
#          8*ns  máximo digital 80*ns pré-filtragem  8*ns  amostras/registro
#         32*ns  reservado
#   Os dados são int16 little-endian, registro a registro, canal a canal.
# =========================================================================


@dataclass
class CabecalhoEDF:
    caminho: Path
    n_sinais: int
    bytes_cabecalho: int
    n_registros: int
    duracao_registro_s: float
    rotulos: tuple[str, ...]
    dimensoes: tuple[str, ...]
    fis_min: np.ndarray
    fis_max: np.ndarray
    dig_min: np.ndarray
    dig_max: np.ndarray
    amostras_por_registro: np.ndarray

    @property
    def amostras_totais_por_registro(self) -> int:
        return int(self.amostras_por_registro.sum())

    @property
    def deslocamentos(self) -> np.ndarray:
        """Índice da primeira amostra de cada canal dentro de um registro."""
        return np.concatenate(([0], np.cumsum(self.amostras_por_registro)[:-1]))

    def taxa_hz(self, i: int) -> float:
        return float(self.amostras_por_registro[i]) / self.duracao_registro_s


def _campo(buf: bytes, ini: int, fim: int) -> str:
    return buf[ini:fim].decode("latin-1").strip()


def ler_cabecalho_edf(caminho: Path | str) -> CabecalhoEDF:
    """Lê só o cabeçalho — não toca nos ~500 MB de dados."""
    caminho = Path(caminho)
    with open(caminho, "rb") as fh:
        fixo = fh.read(256)
        if len(fixo) < 256:
            raise ValueError(f"{caminho.name}: arquivo curto demais para ser EDF")
        n_sinais = int(_campo(fixo, 252, 256))
        bytes_cab = int(_campo(fixo, 184, 192))
        n_reg = int(_campo(fixo, 236, 244))
        dur = float(_campo(fixo, 244, 252))
        if bytes_cab != 256 * (n_sinais + 1):
            raise ValueError(
                f"{caminho.name}: cabeçalho inconsistente "
                f"({bytes_cab} bytes para {n_sinais} sinais; esperado "
                f"{256 * (n_sinais + 1)}). Arquivo truncado ou não é EDF."
            )
        resto = fh.read(bytes_cab - 256)

    def bloco(desloc: int, largura: int) -> list[str]:
        return [
            _campo(resto, desloc + largura * i, desloc + largura * (i + 1))
            for i in range(n_sinais)
        ]

    o_rot = 0
    o_dim = o_rot + n_sinais * (16 + 80)
    o_fmin = o_dim + n_sinais * 8
    o_fmax = o_fmin + n_sinais * 8
    o_dmin = o_fmax + n_sinais * 8
    o_dmax = o_dmin + n_sinais * 8
    o_amo = o_dmax + n_sinais * (8 + 80)

    def numeros(desloc: int) -> np.ndarray:
        return np.array([float(v) for v in bloco(desloc, 8)], dtype=float)

    return CabecalhoEDF(
        caminho=caminho,
        n_sinais=n_sinais,
        bytes_cabecalho=bytes_cab,
        n_registros=n_reg,
        duracao_registro_s=dur,
        rotulos=tuple(bloco(o_rot, 16)),
        dimensoes=tuple(bloco(o_dim, 8)),
        fis_min=numeros(o_fmin),
        fis_max=numeros(o_fmax),
        dig_min=numeros(o_dmin),
        dig_max=numeros(o_dmax),
        amostras_por_registro=numeros(o_amo).astype(int),
    )


def _indice_canal(cab: CabecalhoEDF, nome: str) -> int | None:
    """Índice do canal pelo nome, **insensível a maiúsculas** — ARMADILHA 1."""
    alvo = nome.strip().lower()
    for i, r in enumerate(cab.rotulos):
        if r.strip().lower() == alvo:
            return i
    return None


def _ler_canal(cab: CabecalhoEDF, i: int) -> np.ndarray:
    """Um canal inteiro, já convertido para unidade física.

    Usa `np.memmap`: o EDF do Wearanize+ tem ~500 MB e até 61 canais, dos quais
    precisamos de 3 ou 4. Mapear e fatiar lê só as páginas dos canais pedidos,
    em vez de trazer o arquivo inteiro para a RAM — o mesmo problema que a
    ARMADILHA 4 do `newcastle.py` resolveu com generator, aqui resolvido no
    nível do acesso a disco.
    """
    total = cab.amostras_totais_por_registro
    esperado = cab.bytes_cabecalho + cab.n_registros * total * 2
    real = cab.caminho.stat().st_size
    if real < esperado:
        raise ValueError(
            f"{cab.caminho.name}: arquivo truncado — "
            f"{real} bytes, esperado {esperado}. Download incompleto? "
            "Rode `ferramentas/baixar_wearanize.py --verificar`."
        )

    dados = np.memmap(
        cab.caminho,
        dtype="<i2",
        mode="r",
        offset=cab.bytes_cabecalho,
        shape=(cab.n_registros, total),
    )
    ini = int(cab.deslocamentos[i])
    n = int(cab.amostras_por_registro[i])
    bruto = np.asarray(dados[:, ini:ini + n], dtype=np.float64).reshape(-1)
    del dados

    # Escala EDF: físico = digital * ganho + deslocamento
    span_dig = cab.dig_max[i] - cab.dig_min[i]
    if span_dig == 0:
        raise ValueError(f"{cab.caminho.name}: canal {cab.rotulos[i]!r} com span digital zero")
    ganho = (cab.fis_max[i] - cab.fis_min[i]) / span_dig
    desloc = cab.fis_min[i] - cab.dig_min[i] * ganho
    return bruto * ganho + desloc


# =========================================================================
# Wearanize+
# =========================================================================


def _pasta_plugnplay(pasta: Path) -> Path:
    """Aceita a pasta da coleção ou já o PlugNPlay dentro dela."""
    candidatos = [pasta / SUBPASTA_PLUGNPLAY, pasta]
    # Tolerante a variação de versão no nome (v1.1 -> v1.2 um dia).
    candidatos.extend(sorted(pasta.glob("*PlugNPlay*")))
    for c in candidatos:
        if c.is_dir() and any(c.glob("sub-*")):
            return c
    raise FileNotFoundError(
        f"Não achei sujeitos (`sub-*`) em {pasta} nem em {pasta / SUBPASTA_PLUGNPLAY}.\n"
        "Baixe a coleção ABERTA Wearanize+ OA (CC-BY-4.0, sem cadastro):\n"
        "  python -m ferramentas.baixar_wearanize --n-sujeitos 10\n"
        "Ver ml/README.md."
    )


def _edf_do_sujeito(pasta_pnp: Path, sujeito: str) -> Path | None:
    p = pasta_pnp / sujeito / "eeg" / f"{sujeito}_task-sleep_eeg.edf"
    return p if p.is_file() else None


def sujeitos_disponiveis(pasta: Path | str = PASTA_PADRAO) -> list[str]:
    """IDs `sub-NNN` com EDF presente em disco, ordenados."""
    pnp = _pasta_plugnplay(Path(pasta))
    return sorted(
        d.name for d in pnp.glob("sub-*") if d.is_dir() and _edf_do_sujeito(pnp, d.name)
    )


def _conferir_unidade_empatica(cab: CabecalhoEDF, i: int) -> None:
    """Aborta se o arquivo for da v1.0, que declara a unidade errada.

    ARMADILHA 2: a `PlugNPlay v1.0` (coleção restrita) declara `g/16` quando a
    unidade real é `g/64` — fator 4 de erro no acelerômetro de **pulso**, que é
    o braço "treina" do ML-03. Falhar alto aqui é muito melhor que produzir uma
    matriz de transferência inteira sobre um artefato de escala.
    """
    dim = cab.dimensoes[i].strip().lower().replace(" ", "")
    if dim in {"g/16", "g/16.0"}:
        raise ValueError(
            f"{cab.caminho.name}: canal {cab.rotulos[i]!r} declara unidade 'g/16'.\n"
            "Isto é a PlugNPlay v1.0 (coleção RESTRITA), cuja unidade do Empatica "
            "está ERRADA por fator 4 — os próprios autores documentam a correção "
            "na v1.1.\n"
            "Use a coleção ABERTA `Wearanize+ OA` (DOI 10.34973/xrmf-5726), que é "
            "v1.1 e está correta. Ver ARMADILHA 2 no topo deste módulo."
        )
    if dim not in {"g/64", "g/64.0"}:
        print(
            f"[wearanize] AVISO: {cab.caminho.name} canal {cab.rotulos[i]!r} declara "
            f"unidade {cab.dimensoes[i]!r}, esperado 'g/64'. Aplicando /64 mesmo "
            "assim — confira antes de confiar no resultado.",
            file=sys.stderr,
        )


def _posicao(nome: str) -> Posicao:
    chave = nome.strip().lower()
    # tolera acento e grafias comuns
    chave = {"cabeça": "cabeca", "punho": "pulso", "perna": "coxa"}.get(chave, chave)
    if chave not in POSICOES:
        raise ValueError(
            f"posição desconhecida: {nome!r}. Disponíveis: {tuple(POSICOES)}"
        )
    return POSICOES[chave]


def sujeitos_com_posicoes(
    posicoes: Sequence[str],
    pasta: Path | str = PASTA_PADRAO,
    pontuador: int | None = None,
) -> list[str]:
    """Sujeitos que têm **todas** as posições pedidas (e, opcionalmente, o pontuador).

    É a função que o `ML-03` usa para montar a matriz 3x3 sobre um conjunto
    único de sujeitos. ARMADILHA 3: as células da matriz precisam do MESMO N,
    senão as quedas de kappa não são comparáveis entre si.

    >>> sujeitos_com_posicoes(["pulso", "cabeca"])          # 92 no dataset completo
    >>> sujeitos_com_posicoes(["cabeca", "pulso", "coxa"])  # 86
    >>> sujeitos_com_posicoes(["cabeca"], pontuador=2)      # 96
    """
    pnp = _pasta_plugnplay(Path(pasta))
    alvos = [_posicao(p) for p in posicoes]
    fora: list[str] = []
    for s in sujeitos_disponiveis(pasta):
        edf = _edf_do_sujeito(pnp, s)
        if edf is None:
            continue
        cab = ler_cabecalho_edf(edf)
        ok = all(
            all(_indice_canal(cab, c) is not None for c in p.canais) for p in alvos
        )
        if ok and pontuador is not None:
            ok = _indice_canal(cab, CANAIS_ROTULO[pontuador]) is not None
        if ok:
            fora.append(s)
    return fora


def _ler_rotulos(cab: CabecalhoEDF, pontuador: int) -> np.ndarray | None:
    """Rótulos por época, já em 0 = vigília / 1 = sono / -1 = descartar."""
    i = _indice_canal(cab, CANAIS_ROTULO[pontuador])
    if i is None:
        return None
    if int(cab.amostras_por_registro[i]) != 1:
        raise ValueError(
            f"{cab.caminho.name}: canal de rótulo {cab.rotulos[i]!r} tem "
            f"{cab.amostras_por_registro[i]} amostras por registro, esperado 1. "
            "A premissa 'um registro = uma época = um rótulo' não vale neste arquivo."
        )
    cru = _ler_canal(cab, i)
    # O escalonamento EDF é de ponto flutuante: os inteiros -1..4 voltam como
    # 1,9999847... conforme o ganho. Arredondar é obrigatório, não cosmético —
    # sem isso o mapa de rótulo erra a chave e tudo vira -1 silenciosamente.
    inteiros = np.rint(cru).astype(int)
    desconhecidos = set(np.unique(inteiros)) - set(_MAPA_ROTULO)
    if desconhecidos:
        raise ValueError(
            f"{cab.caminho.name}: rótulos fora do mapa AASM esperado: "
            f"{sorted(desconhecidos)}. Esperado -1..4."
        )
    return np.array([_MAPA_ROTULO[v] for v in inteiros], dtype=int)


def carregar_wearanize(
    posicao: str = "cabeca",
    pasta: Path | str = PASTA_PADRAO,
    pontuador: int = 1,
    sujeitos: Sequence[str] | None = None,
    qualidade: str = "original",
) -> Iterator[Gravacao]:
    """Gravações do Wearanize+ OA para uma posição de sensor.

    Parameters
    ----------
    posicao : "cabeca" | "pulso" | "coxa"
        Qual acelerômetro ler. É o parâmetro que o `ML-03` varia: treinar em
        `pulso` e testar em `cabeca` é o experimento que é a contribuição
        original do trabalho.
    pontuador : 1 ou 2
        Qual das duas pontuações manuais usar como verdade. O pontuador 2 só
        existe em 96 dos 100 (ARMADILHA 4). Comparar os dois dá o **teto
        inter-avaliador** — o número contra o qual o Δκ deve ser lido.
    sujeitos : lista de IDs, opcional
        Restringe o conjunto. Use com `sujeitos_com_posicoes()` para garantir
        que todas as células da matriz 3x3 rodem sobre o MESMO N.
    qualidade : "original" (padrão) | "e4"
        "e4" reamostra e requantiza o sinal para a grade do Empatica E4
        (`degradar_para_e4()`) antes de devolver. Aplicado a `posicao="cabeca"`
        dá o braço de controle "cabeça degradada" que isola custo de posição
        de custo de qualidade de sensor no `ML-03` — ver "CONTROLE
        EXPERIMENTAL" no topo do módulo.

    Yields
    ------
    Gravacao
        `a` em **g**, `t` em segundos a partir de zero, `rotulos` por época de
        30 s, `t0_rotulo = 0.0`.

    ⚠️ **Generator, não lista** — mesma razão do `newcastle.py` (ARMADILHA 4 de
    lá): `processar_gravacoes()` consome uma gravação por vez. Uma noite de
    Zmax a 256 Hz são ~7,5 milhões de amostras por eixo; ter 92 delas em
    memória ao mesmo tempo não cabe em máquina nenhuma razoável.
    """
    pos = _posicao(posicao)
    if pontuador not in (1, 2):
        raise ValueError(f"pontuador deve ser 1 ou 2, recebido {pontuador!r}")
    if qualidade not in QUALIDADES:
        raise ValueError(f"qualidade deve ser {QUALIDADES}, recebido {qualidade!r}")

    pasta = Path(pasta)
    pnp = _pasta_plugnplay(pasta)
    alvos = list(sujeitos) if sujeitos is not None else sujeitos_disponiveis(pasta)
    if not alvos:
        raise FileNotFoundError(
            f"Nenhum sujeito em {pnp}. Baixe primeiro:\n"
            "  python -m ferramentas.baixar_wearanize --n-sujeitos 10"
        )

    sem_sensor: list[str] = []
    sem_rotulo: list[str] = []
    entregues = 0

    for sujeito in alvos:
        edf = _edf_do_sujeito(pnp, sujeito)
        if edf is None:
            continue
        cab = ler_cabecalho_edf(edf)

        if abs(cab.duracao_registro_s - EPOCA_S) > 1e-9:
            raise ValueError(
                f"{edf.name}: registro de dados dura {cab.duracao_registro_s} s, "
                f"esperado {EPOCA_S}. A premissa 'um registro = uma época' não vale."
            )

        idx = [_indice_canal(cab, c) for c in pos.canais]
        if any(i is None for i in idx):
            # ARMADILHA 3 — pular com aviso, nunca abortar os outros.
            sem_sensor.append(sujeito)
            continue

        rotulos = _ler_rotulos(cab, pontuador)
        if rotulos is None:
            # ARMADILHA 4 — acontece com os 4 do Mentalab quando pontuador=2.
            sem_rotulo.append(sujeito)
            continue

        if pos.nome == "pulso":
            _conferir_unidade_empatica(cab, int(idx[0]))

        taxa = cab.taxa_hz(int(idx[0]))
        if abs(taxa - pos.taxa_hz) > 1e-6:
            print(
                f"[wearanize] AVISO: {sujeito} canal {pos.canais[0]} a {taxa:g} Hz, "
                f"esperado {pos.taxa_hz:g} Hz. Seguindo com a taxa do arquivo.",
                file=sys.stderr,
            )

        a = np.stack([_ler_canal(cab, int(i)) for i in idx], axis=1) * pos.para_g
        t = np.arange(a.shape[0], dtype=float) / taxa

        if qualidade == "e4":
            t, a = degradar_para_e4(t, a)

        n_rot = int(rotulos.shape[0])
        if n_rot != cab.n_registros:
            raise ValueError(
                f"{edf.name}: {n_rot} rótulos para {cab.n_registros} registros."
            )

        entregues += 1
        yield Gravacao(
            id_sujeito=sujeito,
            t=t,
            a=a,
            rotulos=rotulos,
            # Não é suposição: o canal de rótulo tem 1 amostra por registro de
            # 30 s, e o registro k cobre [30k, 30(k+1)) do mesmo arquivo. O
            # PlugNPlay já vem sincronizado e truncado. É a diferença estrutural
            # em relação ao Newcastle, onde isto era a ARMADILHA 5.
            t0_rotulo=0.0,
            epoca_rotulo_s=EPOCA_S,
            meta={
                "fonte": "wearanize+_oa_plugnplay_v1.1",
                "doi_colecao": "10.34973/xrmf-5726",
                "doi_dataset_primario": "10.34973/j6jf-9e62",
                "licenca": "CC-BY-4.0",
                "arquivo": edf.name,
                "posicao": pos.nome,
                "dispositivo": pos.descricao,
                "canais": pos.canais,
                "taxa_origem_hz": taxa,
                "unidade_edf": cab.dimensoes[int(idx[0])],
                "fator_para_g": pos.para_g,
                "qualidade": qualidade,
                "pontuador": pontuador,
                "canal_rotulo": CANAIS_ROTULO[pontuador],
                "n_registros": cab.n_registros,
                "n_canais_no_arquivo": cab.n_sinais,
                "tem_postura": _indice_canal(cab, CANAL_POSTURA) is not None,
            },
        )

    if sem_sensor:
        print(
            f"[wearanize] {len(sem_sensor)} sujeito(s) sem o sensor "
            f"{pos.nome!r} ({', '.join(pos.canais)}) — pulados: "
            f"{', '.join(sem_sensor)}. Esperado: ver ARMADILHA 3.",
            file=sys.stderr,
        )
    if sem_rotulo:
        print(
            f"[wearanize] {len(sem_rotulo)} sujeito(s) sem o canal "
            f"{CANAIS_ROTULO[pontuador]!r} — pulados: {', '.join(sem_rotulo)}. "
            "Esperado com pontuador=2: ver ARMADILHA 4.",
            file=sys.stderr,
        )
    if entregues == 0:
        raise ValueError(
            f"Nenhuma gravação utilizável para posicao={pos.nome!r}, "
            f"pontuador={pontuador}. {len(sem_sensor)} sem sensor, "
            f"{len(sem_rotulo)} sem rótulo, de {len(alvos)} sujeitos em disco."
        )
