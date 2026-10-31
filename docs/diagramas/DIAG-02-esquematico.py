"""DIAG-02 — esquemático do circuito do Dormio, v1 (montado) e v2 (projeto).

Item do backlog: `DIAG-02` ("esquemático do circuito; v1 (1 sensor) e v2 (2, endereços
I2C)"). Onde entra no TCC: capítulo de Desenvolvimento, seção de hardware.

POR QUE CÓDIGO, E NÃO KICAD: o `README.md` desta pasta recomendava o KiCad, cujo arquivo é
texto e versiona bem. Mas o KiCad não está na máquina em que o diagrama foi feito, e um
`.kicad_sch` escrito à mão e nunca aberto seria um esquemático que ninguém conferiu. O
`schemdraw` (biblioteca Python, licença MIT) desenha com símbolos de esquemático a partir
deste arquivo, e a imagem é gerada e olhada antes de entrar no texto. Mesma regra das
figuras Mermaid: a fonte é versionada; a imagem, não (`docs/diagramas/saida/` está no
`.gitignore`, pela regra do material do TCC).

O QUE O ESQUEMÁTICO AFIRMA, E DE ONDE CADA LIGAÇÃO VEM:

- SDA no GPIO 21, SCL no GPIO 22: `PINO_SDA`/`PINO_SCL` em `firmware/sketch.ino` e as
  ligações de `firmware/diagram.json`.
- Endereço 0x68, logo AD0 em nível baixo: `ENDERECO_MPU` em `firmware/sketch.ino`. O
  esquemático liga AD0 ao GND explicitamente, em vez de depender de um resistor interno do
  módulo que a fonte consultada não confirma.
- INT, XDA e XCL sem ligação: a C2 lê a FIFO por tempo (sono leve com despertar por timer),
  não por interrupção; e o barramento auxiliar não é usado.
- VCC do módulo no 3V3 do DevKit: é a ligação de `firmware/diagram.json`. ⚠️ A
  página do MPU-6050 no Arduino Playground recomenda 5 V no VCC do GY-521, porque o
  regulador do próprio módulo pode deixar a tensão baixa demais com 3,3 V. Não foi conferido
  nesta placa para qual trilho vão os pull-ups do módulo — e o ESP32 não tolera 5 V nos
  pinos de I2C. A figura mostra o que está ligado e leva a observação.
- Pull-ups do I2C: dentro do módulo GY-521, de 2,2 kΩ ou 10 kΩ conforme o lote (mesma
  fonte). Não há resistor externo.
- Sem botão e sem o resistor de 10 kΩ no GPIO 27: eram andaime do Wokwi (`HW-01`), e o
  `sketch.ino` da C2 não os usa.
- Alimentação pela USB do DevKit: a bateria é decisão aberta (`HW-02`).

A v2 (dois sensores, 0x68 e 0x69 pelo AD0 do segundo) é CONTINGÊNCIA PROJETADA: quem decide
é o `VIA-01`, que depende da solda. Ela sai numa folha própria, com o segundo módulo em caixa
tracejada e rotulado "PROJETO — não montado". O firmware de hoje fala com um sensor só.

ANTES DE DESENHAR, O SCRIPT CONFERE O CÓDIGO: lê `PINO_SDA`, `PINO_SCL` e `ENDERECO_MPU`
em `firmware/sketch.ino` e as ligações do MPU em `firmware/diagram.json`, e recusa desenhar
(saída 1) se algum divergir do que a figura afirma. Um esquemático que continua bonito
depois de o pino mudar no código é o defeito que este arquivo existe para não ter.

Uso:
    python DIAG-02-esquematico.py [pasta_de_saida]
Gera DIAG-02-v1.svg/.png e DIAG-02-v2.svg/.png. Requer `schemdraw==0.19` e
`matplotlib==3.9.2` (fora do `ml/.venv`: esta figura não é do pipeline de ML).
"""
import json
import re
import sys
from pathlib import Path

import schemdraw
import schemdraw.elements as elm

schemdraw.use("matplotlib")

# Nos lados esquerdo e direito do `Ic`, o slot 1 é o de BAIXO. Os quatro pinos que se
# ligam ficam nos mesmos slots dos dois lados, e os dois blocos têm a mesma altura: as
# ligações saem retas.
ALTURA = 4.0


def esp_pinos():
    return [
        elm.IcPin(name="GND", side="right", slot="1/4", anchorname="gnd"),
        elm.IcPin(name="GPIO22 (SCL)", side="right", slot="2/4", anchorname="scl"),
        elm.IcPin(name="GPIO21 (SDA)", side="right", slot="3/4", anchorname="sda"),
        elm.IcPin(name="3V3", side="right", slot="4/4", anchorname="p3v3"),
        elm.IcPin(name="USB", side="left", slot="1/1", anchorname="usb"),
    ]


def gy521_pinos():
    return [
        elm.IcPin(name="GND", side="left", slot="1/4", anchorname="gnd"),
        elm.IcPin(name="SCL", side="left", slot="2/4", anchorname="scl"),
        elm.IcPin(name="SDA", side="left", slot="3/4", anchorname="sda"),
        elm.IcPin(name="VCC", side="left", slot="4/4", anchorname="vcc"),
        elm.IcPin(name="AD0", side="bot", slot="1/1", anchorname="ad0"),
        elm.IcPin(name="XCL", side="right", slot="1/3", anchorname="xcl"),
        elm.IcPin(name="XDA", side="right", slot="2/3", anchorname="xda"),
        elm.IcPin(name="INT", side="right", slot="3/3", anchorname="int"),
    ]


def em(ponto, dx, dy):
    """Uma posição relativa a uma âncora (o `Label` do schemdraw não tem `delta`)."""
    return (ponto[0] + dx, ponto[1] + dy)


def gy521(d, onde, rotulo):
    # Rótulo ACIMA do bloco: no centro ele se sobrepunha aos nomes dos pinos.
    u = elm.Ic(pins=gy521_pinos(), size=(4.0, ALTURA)).at(onde).anchor("vcc").theta(0)
    d += u
    d += elm.Label().at(em(u.vcc, 2.3, 1.1)).label(rotulo, fontsize=11)
    for p in ("int", "xda", "xcl"):
        d += elm.Line().at(getattr(u, p)).theta(0).length(0.4)
        d += elm.NoConnect()
    return u


def desenhar(versao, pasta):
    with schemdraw.Drawing(show=False) as d:
        d.config(fontsize=11, unit=2, margin=1.5)

        esp = elm.Ic(pins=esp_pinos(), size=(5.0, ALTURA)).at((0, 0)).theta(0)
        d += esp
        d += elm.Label().at(em(esp.p3v3, -2.9, 1.1)).label("U1 · ESP32 DevKit V1", fontsize=12)
        d += elm.Line().at(esp.usb).theta(180).length(0.8)
        d += elm.Dot(open=True).label("alimentação USB\n(bateria: HW-02)", loc="left", fontsize=9)

        u2 = gy521(d, em(esp.p3v3, 6.0, 0), "U2 · GY-521 (MPU6050) · 0x68")

        d += elm.Line().at(esp.p3v3).to(u2.vcc).color("firebrick")
        d += elm.Line().at(esp.sda).to(u2.sda)
        d += elm.Line().at(esp.scl).to(u2.scl)
        d += elm.Line().at(esp.gnd).to(u2.gnd)

        # AD0 ao GND: endereço 0x68
        d += elm.Line().at(u2.ad0).theta(-90).length(0.8)
        d += elm.Ground()
        d += elm.Label().at(em(u2.ad0, 0.25, -0.5)).label("AD0 em GND: 0x68", fontsize=9,
                                                          halign="left")

        nota = ("No módulo GY-521: pull-ups do I2C de 2,2 k ou 10 kΩ, conforme o lote, e regulador "
                "de 3,3 V.\nINT, XDA e XCL sem ligação: a C2 lê a FIFO por tempo, sem interrupção.")

        if versao == "v2":
            u3 = gy521(d, em(u2.vcc, 0, -8.5), "U3 · GY-521 (MPU6050) · 0x69")
            # mesmo barramento: uma derivação de cada linha, descendo até U3
            for k, (pino, cor) in enumerate((("vcc", "firebrick"), ("sda", "black"),
                                             ("scl", "black"), ("gnd", "black"))):
                origem = getattr(u2, pino)
                x = origem[0] - 1.2 - 0.6 * k
                d += elm.Dot().at((x, origem[1]))
                d += elm.Wire("|-").at((x, origem[1])).to(getattr(u3, pino)).color(cor)
            # AD0 do segundo módulo no 3V3: endereço 0x69
            d += elm.Line().at(u3.ad0).theta(-90).length(0.8)
            d += elm.Dot(open=True).label("3V3", loc="bottom", fontsize=9)
            d += elm.Label().at(em(u3.ad0, 0.25, -0.5)).label("AD0 em 3V3: 0x69", fontsize=9,
                                                              halign="left")
            d += elm.EncircleBox([u3], padx=0.9, pady=1.6).linestyle("--").label(
                "PROJETO — não montado (contingência; decide o VIA-01)", loc="bottom",
                fontsize=9)

        titulo = {"v1": "DIAG-02 — v1: um sensor (as ligações que o firmware espera)",
                  "v2": "DIAG-02 — v2: dois sensores no mesmo I2C (PROJETO)"}[versao]
        d += elm.Label().at(em(esp.p3v3, 3.5, 2.6)).label(titulo, fontsize=13)
        aviso = (nota + "\n" + "⚠ VCC do GY-521 no 3V3 do DevKit, como em firmware/diagram.json. A fonte consultada\n"
                 "recomenda 5 V no VCC do módulo; não foi conferido para qual trilho vão os pull-ups,\n"
                 "e o ESP32 não tolera 5 V nos pinos de I2C. Ver HW-02.")
        y_aviso = -2.4 if versao == "v1" else -12.6
        d += elm.Label().at(em(esp.gnd, -5.0, y_aviso)).label(aviso, fontsize=8, halign="left")

        for ext in ("svg", "png"):
            d.save(str(pasta / f"DIAG-02-{versao}.{ext}"), dpi=150)


# O que a figura afirma, e onde no código isso tem de estar.
SDA, SCL, ENDERECO = 21, 22, 0x68
RAIZ = Path(__file__).resolve().parents[2]


def conferir_com_o_firmware(raiz=RAIZ):
    """Devolve a lista de divergências entre a figura e o código (vazia = ok)."""
    erros = []
    sketch = (raiz / "firmware" / "sketch.ino").read_text(encoding="utf-8")

    def constante(nome):
        m = re.search(r"\b" + nome + r"\s*=\s*(0x[0-9A-Fa-f]+|\d+)\s*;", sketch)
        return int(m.group(1), 0) if m else None

    for nome, esperado in (("PINO_SDA", SDA), ("PINO_SCL", SCL), ("ENDERECO_MPU", ENDERECO)):
        valor = constante(nome)
        if valor != esperado:
            fmt = (lambda v: "ausente" if v is None else f"{v:#x}") if nome == "ENDERECO_MPU"                 else (lambda v: "ausente" if v is None else str(v))
            erros.append(f"sketch.ino: {nome} = {fmt(valor)}, a figura diz {fmt(esperado)}")

    diagrama = json.loads((raiz / "firmware" / "diagram.json").read_text(encoding="utf-8"))
    ligacoes = {frozenset((a, b)) for a, b, *_ in diagrama["connections"]}
    for par in (("imu1:SDA", f"esp:{SDA}"), ("imu1:SCL", f"esp:{SCL}"), ("esp:3V3", "imu1:VCC")):
        if frozenset(par) not in ligacoes:
            erros.append(f"diagram.json: falta a ligação {par[0]} <-> {par[1]}")
    return erros


def main():
    erros = conferir_com_o_firmware()
    if erros:
        print("O esquemático diverge do código; nada foi desenhado:")
        for e in erros:
            print("  -", e)
        sys.exit(1)
    pasta = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent / "saida"
    pasta.mkdir(parents=True, exist_ok=True)
    for v in ("v1", "v2"):
        desenhar(v, pasta)
    print(f"gerado em {pasta}")


if __name__ == "__main__":
    main()
