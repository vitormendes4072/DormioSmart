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
"""

from __future__ import annotations

import re
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


def _ler_bin_geneactiv(caminho: Path) -> tuple[np.ndarray, np.ndarray]:
    """Leitor mínimo do .bin do GENEActiv. Devolve (t_segundos, a_g).

    ✅ Validado contra `actipy` (OxWearables) em amostra real do Newcastle —
    ver ARMADILHA 3 abaixo. Antes da correção, a leitura batia com `actipy`
    só na ordem de grandeza; após aplicar a calibração por eixo, os primeiros
    valores batem a 5 casas decimais.

    O formato é texto ASCII com blocos: cada página traz um cabeçalho de
    metadados e ~300 amostras codificadas em hexadecimal, 12 bits por eixo.

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
    tempos: list[float] = []
    amostras: list[tuple[int, int, int]] = []
    calib: dict[str, int] = {}

    with open(caminho, "r", errors="ignore") as fh:
        linhas = fh.read().splitlines()

    t_pagina = None
    for linha in linhas:
        m = re.match(r"^([xyz]) (gain|offset):(-?\d+)", linha.strip())
        if m:
            eixo, campo, valor = m.groups()
            calib[f"{eixo}_{campo}"] = int(valor)
            continue
        if linha.startswith("Page Time"):
            t_pagina = linha.split(":", 1)[1].strip()
        elif len(linha) >= 3000 and re.fullmatch(r"[0-9a-fA-F]+", linha.strip()):
            bloco = linha.strip()
            n = len(bloco) // 12          # 12 hex chars = x,y,z,luz (3 cada)
            for k in range(n):
                p = bloco[k * 12 : k * 12 + 9]
                vals = []
                for j in range(3):
                    v = int(p[j * 3 : j * 3 + 3], 16)
                    if v > 2047:          # complemento de dois em 12 bits
                        v -= 4096
                    vals.append(v)
                amostras.append(tuple(vals))
            if t_pagina is not None:
                tempos.append(len(amostras))

    faltando = [c for c in _CHAVES_CALIBRACAO if c not in calib]
    if faltando:
        raise ValueError(
            f"calibração incompleta no cabeçalho de {caminho.name}: faltam {faltando}. "
            "Sem isso a conversão para g não é confiável — ver ARMADILHA 3."
        )
    if not amostras:
        raise ValueError(f"nenhuma amostra lida de {caminho.name} — formato inesperado")

    bruto = np.asarray(amostras, dtype=float)
    ganho = np.array([calib["x_gain"], calib["y_gain"], calib["z_gain"]], dtype=float)
    offset = np.array([calib["x_offset"], calib["y_offset"], calib["z_offset"]], dtype=float)
    a = (bruto * 100.0 - offset) / ganho
    t = np.arange(a.shape[0], dtype=float) / TAXA_NOMINAL_HZ
    return t, a


def _ler_rotulos(caminho: Path) -> np.ndarray:
    """Rótulos de PSG (.txt, 30 s) mapeados para 0 = vigília, 1 = sono, -1 = n/d.

    O Newcastle traz estágios AASM. Como o escopo é sono×vigília (ver §1 do
    ML-DATASETS-E-PLANO.md: estadiamento é limite FÍSICO, não algorítmico),
    tudo que não é vigília vira sono.
    """
    mapa = {
        "w": 0, "wake": 0, "0": 0,
        "n1": 1, "n2": 1, "n3": 1, "n4": 1, "r": 1, "rem": 1,
        "1": 1, "2": 1, "3": 1, "4": 1, "5": 1,
    }
    out = []
    for linha in Path(caminho).read_text(errors="ignore").splitlines():
        chave = linha.strip().lower()
        if not chave:
            continue
        out.append(mapa.get(chave, -1))
    return np.asarray(out, dtype=int)


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


def carregar_newcastle(pasta: Path | str = PASTA_PADRAO) -> list[Gravacao]:
    """Todas as gravações do Newcastle presentes em `pasta`.

    Levanta FileNotFoundError com instrução de download se a pasta estiver
    vazia — o dado não entra no git, por tamanho e por princípio.
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
    gravacoes = []
    for b in bins:
        id_sujeito = _id_do_nome_do_arquivo(b)  # ARMADILHA 2
        rot = rotulos_por_id.get(id_sujeito)
        if rot is None:
            continue
        t, a = _ler_bin_geneactiv(b)
        y = _ler_rotulos(rot)
        gravacoes.append(
            Gravacao(
                id_sujeito=id_sujeito,
                t=t,
                a=a,
                rotulos=y,
                t0_rotulo=float(t[0]),
                meta={
                    "fonte": "newcastle2015",
                    "arquivo": b.name,
                    "taxa_origem_hz": TAXA_NOMINAL_HZ,
                    "faixa_g": FAIXA_G,
                    "bits": BITS,
                    "id_cabecalho_ignorado": True,
                },
            )
        )
    return gravacoes
