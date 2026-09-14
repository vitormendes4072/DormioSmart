"""Carregador do Newcastle 2015 (GENEActiv, dois punhos, PSG).

Fonte
-----
Dados : Zenodo, CC-BY 4.0, sem cadastro — https://zenodo.org/records/1160410
        962,8 MB · 55 arquivos .bin (falta o punho direito de um participante)
        + rótulos de PSG em .txt (30 s) + um .csv com diagnóstico, idade e sexo.
Protocolo : van Hees, V. T.; Sabia, S.; Anderson, K. N.; Denton, S. J.; Oliver,
        J.; Catt, M.; Abell, J. G.; Kivimäki, M.; Trenell, M. I.; Singh-Manoux,
        A. (2015). *A Novel, Open Access Method to Assess Sleep Duration Using a
        Wrist-Worn Accelerometer.* PLoS ONE 10(11), e0142533.
        → "configured to collect data at **85.70 Hz** with a **±8 g** dynamic
          range", punho não dominante.
Aparelho : GENEActiv Original — ±8 g, **12 bits, 3,9 mg/LSB**
        (ActivInsights, Product Information Sheet, jan/2025).

=============================================================================
ARMADILHA 1 — o formato .bin é proprietário
=============================================================================
Os .bin do GENEActiv são lidos nativamente em R (`GENEAread`, `GGIR`). Em
Python dá, mas custa. Duas rotas, nesta ordem de preferência:

  (a) `actipy` (OxWearables) — lê GENEActiv e Axivity, mantido, pip-instalável.
      Está comentado no requirements.txt.
  (b) O leitor deste módulo (`_ler_bin_geneactiv`), que implementa o formato
      texto-com-blocos-hex do GENEActiv diretamente.

✅ **Validado em 2026-09-14** contra um .bin real do Newcastle (participante
01, punho esquerdo, 3.700.800 amostras / ~12 h), comparando amostra a amostra
com a rota (a) (`actipy`). 3.700.798 de 3.700.800 batem a ~1e-7 g (arredonda-
mento de ponto flutuante); 2 amostras isoladas divergem (~16 g), consistente
com saturação pontual do ADC no sensor — não com erro de parsing. Essa
validação só passou a ser possível depois de corrigir a ARMADILHA 3 abaixo,
que é o bug de verdade que estava aqui.

=============================================================================
ARMADILHA 2 — os IDs no cabeçalho dos .bin estão ERRADOS
=============================================================================
Documentado pelos próprios autores do dataset: o ID de participante gravado
*dentro* do cabeçalho do .bin **não é confiável**. O ID válido é o do **nome do
arquivo**.

Isto não é um detalhe cosmético: o `id_sujeito` é a chave do split
leave-one-subject-out. Usar o ID errado mistura o mesmo sujeito entre treino e
teste, e **infla a acurácia de forma espetacular e silenciosa** — o erro mais
comum da literatura de wearables. Por isso `_id_do_nome_do_arquivo()` é a única
fonte de ID neste módulo, e o do cabeçalho é explicitamente ignorado.

=============================================================================
ARMADILHA 3 — calibração por eixo do cabeçalho, e a estrutura real do zip
=============================================================================
Duas coisas só apareceram ao carregar o zip de verdade (não estavam previstas
antes da validação acima):

  1. O zip **não** é uma pasta plana: os `.bin` ficam em `acc/` e os `.txt`
     de rótulo em `psg/`. `_achar_bins()` e `_indice_rotulos()` tratam isso
     (com fallback para pasta plana, por robustez).
  2. `.bin` e `.txt` **não compartilham nome-base** — o `.bin` carrega punho e
     serial do aparelho no nome, o `.txt` só o número do participante. O
     pareamento é por ID extraído do nome (a mesma regra da ARMADILHA 2), não
     por stem.
  3. O valor bruto de 12 bits não é aceleração até passar pela calibração
     **por eixo, por aparelho** da seção "Calibration Data" do cabeçalho
     (`x/y/z gain`, `x/y/z offset`). Ver o docstring de `_ler_bin_geneactiv`
     para a fórmula e o tamanho do erro que ignorá-la introduz.

=============================================================================
ARMADILHA 4 — carregar as 55 gravações inteiras de uma vez estoura memória
=============================================================================
Os 55 `.bin` somam 4,6 GB de texto hex (um sozinho tem 282 MB — o protocolo é
"uma noite", mas a duração real varia bastante por participante). A primeira
versão de `carregar_newcastle()` devolvia `list[Gravacao]`, o que força ter
as 55 gravações a 85,7 Hz — brutas, sem decimar — na memória ao mesmo tempo.
Em execução real (máquina de 12 GB), isso passou de 3 GB e continuava
crescendo antes de terminar um terço dos arquivos.

**Duas mudanças, uma para cada metade do problema:**
  - `_ler_bin_geneactiv` decodifica o hex inteiro com numpy vetorizado em vez
    de um laço Python por amostra (era o gargalo de CPU: ~6 s/arquivo médio,
    escalando mal para os arquivos grandes).
  - `carregar_newcastle` virou **generator** (`yield`, não `list` + `return`):
    `processar_gravacoes()` (`src/carregar/__init__.py`) já consome uma
    gravação por vez — extrai as features de 30 s e descarta o bruto antes de
    seguir para a próxima — então nada exigia ter as 55 na RAM simultaneamente.
    O pico de memória agora é o de UM arquivo (o maior, ~282 MB de texto), não
    a soma dos 55.

=============================================================================
ARMADILHA 5 — o rótulo NÃO começa quando o acelerômetro liga
=============================================================================
A primeira versão deste carregador usava `t0_rotulo = t[0]` — sempre zero,
por construção (`t` começa em zero em `_ler_bin_geneactiv`). Isso assume que
o primeiro rótulo de PSG corresponde à primeira amostra do acelerômetro.

**É falso, e não é um detalhe pequeno.** No participante 1: o acelerômetro
("Start Time" do cabeçalho do `.bin`) liga às 19:30:00; o primeiro rótulo de
PSG ("Recording Date" + primeira linha "Time [hh:mm:ss]" do `.txt`) é às
21:22:40 — **1h52min50s depois**. O dispositivo é colocado no participante
antes de ele ir para a clínica se preparar para o estudo; a pontuação de PSG
só começa quando o estudo de fato começa.

Com `t0_rotulo=0`, `fatiar_epocas()` procura cada rótulo no trecho ERRADO do
sinal — na prática, quase toda época falha o teste de cobertura e é
descartada. Rodado assim contra os 55 arquivos reais, sobraram **275 épocas
em 28 sujeitos** (a noite inteira deveria render milhares) — o sintoma que
expôs o bug.

**A correção:** `_ler_bin_geneactiv` agora devolve o instante `Start Time` do
cabeçalho; `_ler_rotulos_psg` devolve o instante do primeiro rótulo
(`Recording Date` + hora da primeira linha de dado). `t0_rotulo` é a
diferença entre os dois, em segundos — não mais uma suposição. Uma checagem
de sanidade (`0 <= t0_rotulo <= duração da gravação`) levanta erro alto e
claro se o alinhamento calculado cair fora da gravação, em vez de silenciar
como "zero épocas cobertas".

Segundo bug, encontrado no caminho: `_ler_rotulos` (antiga) lia o arquivo
linha a linha sem pular o cabeçalho do RemLogic, e a seção "Events Included:"
lista os códigos de estágio um por linha ("R", "W", "N1", "N2", "N3") — que
batem por acidente no mapa de estágio -> label e viram 5 épocas FALSAS antes
de qualquer dado real. `_ler_rotulos_psg` só começa a ler depois de achar a
linha de cabeçalho de colunas ("Sleep Stage\t...").

**Checagem de sanidade encontrou 1 caso real** (de 28): `ncl029` tem os dois
acelerômetros (esquerdo e direito) configurados para 24h a partir de
2014-02-06 18:00:00, mas a PSG só começa a pontuar em 2014-02-07 20:25:57 —
**2h26min DEPOIS do fim da janela gravada**. Não é bug de parsing (os outros
27 participantes calculam `t0_rotulo` dentro da gravação sem exceção); é uma
inconsistência real na coleta original do dataset — o Zenodo não documenta a
causa. `carregar_newcastle()` pula esse participante com aviso em stderr, em
vez de abortar a noite dos outros 27 por causa de 1.
"""

from __future__ import annotations

import re
import sys
from collections.abc import Iterator
from datetime import date, datetime
from pathlib import Path

import numpy as np

from .base import Gravacao

__all__ = ["carregar_newcastle", "PASTA_PADRAO"]

PASTA_PADRAO = Path(__file__).resolve().parents[2] / "dados" / "bruto" / "newcastle"

TAXA_NOMINAL_HZ = 85.70
FAIXA_G = 8.0
BITS = 12


def _id_do_nome_do_arquivo(caminho: Path) -> str:
    """ID de participante a partir do NOME do arquivo — nunca do cabeçalho.

    Ver ARMADILHA 2 no topo do módulo.
    """
    m = re.search(r"(\d+)", caminho.stem)
    if not m:
        raise ValueError(f"não consegui extrair ID do nome: {caminho.name}")
    return f"ncl{int(m.group(1)):03d}"


#: Chaves de calibração exigidas no cabeçalho do .bin — ver ARMADILHA 3.
_CHAVES_CALIBRACAO = ("x_gain", "x_offset", "y_gain", "y_offset", "z_gain", "z_offset")

#: Tabela de conversão de caractere hex ASCII -> nibble (4 bits), para decodificar
#: o bloco de amostras inteiro de uma vez com numpy em vez de laço por amostra.
_LUT_HEX = np.zeros(256, dtype=np.uint8)
for _c in "0123456789abcdefABCDEF":
    _LUT_HEX[ord(_c)] = int(_c, 16)


def _ler_bin_geneactiv(caminho: Path) -> tuple[np.ndarray, np.ndarray, datetime]:
    """Leitor mínimo do .bin do GENEActiv. Devolve (t_segundos, a_g, inicio).

    `inicio` é o instante (data+hora) da amostra t=0, lido do cabeçalho
    ("Start Time"). É o que permite alinhar esta gravação com o rótulo de
    PSG — ver ARMADILHA 5.

    ✅ Validado contra `actipy` (OxWearables) em amostra real do Newcastle —
    ver ARMADILHA 3 abaixo. Antes da correção, a leitura batia com `actipy`
    só na ordem de grandeza; após aplicar a calibração por eixo, os primeiros
    valores batem a 5 casas decimais.

    O formato é texto ASCII com blocos: cada página traz um cabeçalho de
    metadados e ~300 amostras codificadas em hexadecimal, 12 bits por eixo.
    A decodificação do hex é vetorizada (numpy) — a primeira versão fazia um
    laço Python por amostra e, nos 55 arquivos reais (4,6 GB, um com 282 MB
    sozinho), levava a memória a >3 GB e crescendo numa máquina de 12 GB antes
    de terminar um terço dos arquivos. Ver ARMADILHA 4 no topo do módulo.

    =========================================================================
    ARMADILHA 3 — o valor bruto NÃO é a aceleração; falta a calibração por
    eixo do cabeçalho
    =========================================================================
    A primeira versão deste leitor convertia o inteiro de 12 bits para g com
    uma escala genérica de quantização ideal (±8 g sobre 12 bits). **Isso é
    sistematicamente errado**: o GENEActiv calibra cada eixo de cada aparelho
    de fábrica, e o cabeçalho carrega essa calibração na seção "Calibration
    Data" (`x gain`, `x offset`, `y gain`, `y offset`, `z gain`, `z offset`).
    A fórmula correta (confirmada batendo com `actipy` amostra a amostra) é

        g_eixo = (bruto_eixo · 100 − offset_eixo) / gain_eixo

    Testado na primeira amostra do primeiro participante: a escala genérica
    dava erro de **até 9,4 % no eixo Z** — nada sutil, e silencioso, porque o
    valor resultante ainda "parece" uma aceleração plausível (~1 g). Ignorar
    a calibração por eixo teria introduzido viés sistemático — não ruído —
    em toda medição feita sobre o Newcastle.
    """
    blocos: list[str] = []
    calib: dict[str, int] = {}
    inicio: datetime | None = None

    with open(caminho, "r", errors="ignore") as fh:
        linhas = fh.read().splitlines()

    for linha in linhas:
        m = re.match(r"^([xyz]) (gain|offset):(-?\d+)", linha.strip())
        if m:
            eixo, campo, valor = m.groups()
            calib[f"{eixo}_{campo}"] = int(valor)
            continue
        l = linha.strip()
        if inicio is None and l.startswith("Start Time:"):
            m2 = re.search(r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})", l)
            if m2:
                inicio = datetime.strptime(m2.group(1), "%Y-%m-%d %H:%M:%S")
            continue
        if len(l) >= 3000 and re.fullmatch(r"[0-9a-fA-F]+", l):
            usavel = (len(l) // 12) * 12  # 12 hex chars = x,y,z,luz (3 cada)
            blocos.append(l[:usavel])

    faltando = [c for c in _CHAVES_CALIBRACAO if c not in calib]
    if faltando:
        raise ValueError(
            f"calibração incompleta no cabeçalho de {caminho.name}: faltam {faltando}. "
            "Sem isso a conversão para g não é confiável — ver ARMADILHA 3."
        )
    if inicio is None:
        raise ValueError(f"'Start Time' não encontrado no cabeçalho de {caminho.name}")
    if not blocos:
        raise ValueError(f"nenhuma amostra lida de {caminho.name} — formato inesperado")

    hexall = "".join(blocos)
    nibbles = _LUT_HEX[np.frombuffer(hexall.encode("ascii"), dtype=np.uint8)]
    grupos = nibbles.reshape(-1, 3).astype(np.int32)         # cada linha: 1 valor de 12 bits
    valores = grupos[:, 0] * 256 + grupos[:, 1] * 16 + grupos[:, 2]
    bruto = valores.reshape(-1, 4)[:, :3]                    # x, y, z (descarta luz)
    bruto = np.where(bruto > 2047, bruto - 4096, bruto)      # complemento de dois em 12 bits

    ganho = np.array([calib["x_gain"], calib["y_gain"], calib["z_gain"]], dtype=float)
    offset = np.array([calib["x_offset"], calib["y_offset"], calib["z_offset"]], dtype=float)
    a = (bruto.astype(float) * 100.0 - offset) / ganho
    t = np.arange(a.shape[0], dtype=float) / TAXA_NOMINAL_HZ
    return t, a, inicio


#: Estágio AASM -> 0 (vigília) / 1 (sono). Estadiamento é limite FÍSICO do
#: escopo (ver §1 do ML-DATASETS-E-PLANO.md), não algorítmico: tudo que não é
#: vigília vira sono.
_MAPA_ESTAGIO = {
    "w": 0, "wake": 0, "0": 0,
    "n1": 1, "n2": 1, "n3": 1, "n4": 1, "r": 1, "rem": 1,
    "1": 1, "2": 1, "3": 1, "4": 1, "5": 1,
}


def _ler_rotulos_psg(caminho: Path) -> tuple[datetime, np.ndarray]:
    """Cabeçalho + rótulos de PSG (.txt, 30 s). Devolve (inicio, rotulos).

    `inicio` é o instante (data+hora) do PRIMEIRO rótulo — é isso que alinha
    esta gravação com o `.bin` do acelerômetro. Ver ARMADILHA 5.

    Duas armadilhas de formato que só apareceram com os 28 arquivos reais:

      1. O layout de colunas NÃO é fixo entre participantes — alguns têm uma
         coluna "Position" a mais, outros não (`mecsleep01` vs `mecsleep34`).
         Por isso o parsing é por NOME de coluna (a partir da linha
         "Sleep Stage\t...\tTime [hh:mm:ss]\t..."), nunca por índice fixo.
      2. O arquivo tem um cabeçalho de metadados (RemLogic) ANTES da tabela de
         dados, incluindo uma seção "Events Included:" que lista os códigos de
         estágio um por linha — "R", "W", "N1", "N2", "N3". Ler o arquivo linha
         a linha sem pular esse cabeçalho faz esses códigos **baterem por
         acidente** no mapa de estágios e virarem 5 épocas falsas antes de
         qualquer dado real — silenciosamente. Por isso o parsing só começa
         depois de achar a linha "Sleep Stage" (cabeçalho de colunas).
    """
    linhas = Path(caminho).read_text(errors="ignore").splitlines()

    data_gravacao: date | None = None
    idx_cabecalho: int | None = None
    for i, linha in enumerate(linhas):
        if data_gravacao is None and linha.strip().lower().startswith("recording date"):
            partes = linha.split("\t")
            if len(partes) >= 2 and partes[1].strip():
                data_gravacao = datetime.strptime(partes[1].strip(), "%d/%m/%Y").date()
        if linha.strip().lower().startswith("sleep stage"):
            idx_cabecalho = i
            break

    if data_gravacao is None:
        raise ValueError(f"'Recording Date' não encontrado em {caminho.name}")
    if idx_cabecalho is None:
        raise ValueError(f"linha de cabeçalho de colunas ('Sleep Stage...') não achada em {caminho.name}")

    colunas = [c.strip() for c in linhas[idx_cabecalho].split("\t")]
    try:
        i_estagio = colunas.index("Sleep Stage")
        i_tempo = colunas.index("Time [hh:mm:ss]")
    except ValueError as e:
        raise ValueError(f"colunas esperadas ausentes em {caminho.name}: {colunas}") from e

    rotulos: list[int] = []
    inicio: datetime | None = None
    for linha in linhas[idx_cabecalho + 1:]:
        if not linha.strip():
            continue
        campos = linha.split("\t")
        if len(campos) <= max(i_estagio, i_tempo):
            continue
        chave = campos[i_estagio].strip().lower()
        rotulos.append(_MAPA_ESTAGIO.get(chave, -1))
        if inicio is None:
            hora = datetime.strptime(campos[i_tempo].strip(), "%H:%M:%S").time()
            inicio = datetime.combine(data_gravacao, hora)

    if inicio is None:
        raise ValueError(f"nenhuma linha de dado em {caminho.name}")

    return inicio, np.asarray(rotulos, dtype=int)


def _achar_bins(pasta: Path) -> list[Path]:
    """.bin ficam em `pasta/acc/` no zip oficial; aceita `pasta/` direto também."""
    sub = pasta / "acc"
    if sub.is_dir():
        return sorted(sub.glob("*.bin"))
    return sorted(pasta.glob("*.bin"))


def _indice_rotulos(pasta: Path) -> dict[str, Path]:
    """Mapa id-do-sujeito → caminho do .txt de rótulo.

    Os nomes NÃO compartilham stem com os .bin: o .bin é
    "MECSLEEP01_left wrist_012870_...bin" e o rótulo é "mecsleep01_psg.txt".
    A única chave comum é o número do participante — por isso a busca é por
    ID extraído do nome (mesma função usada para os .bin), não por stem.
    """
    sub = pasta / "psg"
    pasta_rotulos = sub if sub.is_dir() else pasta
    indice: dict[str, Path] = {}
    for caminho in pasta_rotulos.glob("*.txt"):
        indice[_id_do_nome_do_arquivo(caminho)] = caminho
    return indice


def carregar_newcastle(pasta: Path | str = PASTA_PADRAO) -> Iterator[Gravacao]:
    """Todas as gravações do Newcastle presentes em `pasta`.

    Levanta FileNotFoundError com instrução de download se a pasta estiver
    vazia — o dado não entra no git, por tamanho e por princípio.

    ⚠️ **Generator, não lista** — ver ARMADILHA 4. `processar_gravacoes()` já
    consome uma gravação por vez (extrai features e descarta o bruto antes de
    seguir para a próxima); manter tudo em memória ao mesmo tempo, como a
    primeira versão fazia, não tem por que existir.
    """
    pasta = Path(pasta)
    bins = _achar_bins(pasta)
    if not bins:
        raise FileNotFoundError(
            f"Nenhum .bin em {pasta} (nem em {pasta / 'acc'}).\n"
            "Baixe o Newcastle 2015 (CC-BY 4.0, sem cadastro, 962,8 MB):\n"
            "  https://zenodo.org/records/1160410\n"
            "e descompacte o zip nessa pasta (mantém a estrutura acc/ e psg/)."
        )

    rotulos_por_id = _indice_rotulos(pasta)
    for b in bins:
        id_sujeito = _id_do_nome_do_arquivo(b)  # ARMADILHA 2
        rot = rotulos_por_id.get(id_sujeito)
        if rot is None:
            continue
        t, a, inicio_acc = _ler_bin_geneactiv(b)
        inicio_psg, y = _ler_rotulos_psg(rot)

        # ARMADILHA 5: t0_rotulo é o instante do PRIMEIRO rótulo relativo ao
        # início da gravação do acelerômetro — NÃO é zero. O acelerômetro liga
        # bem antes do estudo de sono começar (aqui, ~1h50 antes no
        # participante 1); tratar as duas gravações como simultâneas descarta
        # quase todas as épocas por "falta de cobertura" (fatiar_epocas
        # procura o rótulo no lugar errado do sinal) e ainda embaralha o
        # pouco que sobra. Ver ARMADILHA 5 no topo do módulo.
        t0_rotulo = (inicio_psg - inicio_acc).total_seconds()
        duracao_s = float(t[-1]) if t.shape[0] else 0.0
        if not (0.0 <= t0_rotulo <= duracao_s):
            # Não é bug de parsing: nos 28 participantes, só este caso ocorre,
            # e a causa é rastreável no próprio cabeçalho (ver ARMADILHA 5) —
            # ex.: ncl029 tem os DOIS acelerômetros (esquerdo e direito)
            # configurados para 24h a partir de 2014-02-06 18:00, mas a PSG
            # começa a pontuar em 2014-02-07 20:25:57 — 2h26min DEPOIS do fim
            # da janela gravada. É uma inconsistência real na coleta do
            # dataset, não um erro de leitura. Pular com aviso, não abortar a
            # noite inteira dos outros 27 participantes por causa de 1.
            print(
                f"[newcastle] pulando {id_sujeito} ({b.name}): alinhamento "
                f"PSG/acelerômetro fora da gravação (t0_rotulo={t0_rotulo:.1f}s, "
                f"duração={duracao_s:.1f}s, inicio_acc={inicio_acc}, "
                f"inicio_psg={inicio_psg}) — provável inconsistência na coleta "
                "original, não erro de parsing (ver ARMADILHA 5).",
                file=sys.stderr,
            )
            continue

        yield Gravacao(
            id_sujeito=id_sujeito,
            t=t,
            a=a,
            rotulos=y,
            t0_rotulo=t0_rotulo,
            meta={
                "fonte": "newcastle2015",
                "arquivo": b.name,
                "taxa_origem_hz": TAXA_NOMINAL_HZ,
                "faixa_g": FAIXA_G,
                "bits": BITS,
                "id_cabecalho_ignorado": True,
                "inicio_acc": inicio_acc.isoformat(),
                "inicio_psg": inicio_psg.isoformat(),
            },
        )
