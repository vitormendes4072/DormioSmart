"""Simulador do dispositivo na arquitetura C2 (SIM-02).

Gera uma noite sintética de épocas de 30 s, no formato EXATO que o firmware C2
envia, e a entrega em lotes ao `POST /api/data/lote`. Serve para exercitar e
demonstrar a corrente nova — dispositivo → lote → `/api/features` → painel —
antes de a placa existir.

Rodar pelo ambiente de ML (precisa de numpy e scipy, que NÃO entram no backend):

    ml/.venv/Scripts/python scripts/simulador_c2.py --seco            # só gera e resume
    ml/.venv/Scripts/python scripts/simulador_c2.py                   # a última noite já terminada, 23h–7h
    ml/.venv/Scripts/python scripts/simulador_c2.py --tempo-real      # uma época a cada 30 s

    DORMIO_API_URL      base da API (padrão: http://127.0.0.1:5000)
    DORMIO_DEVICE_TOKEN token do dispositivo pareado (header X-Device-Token)

⚠️ O backend local fala com o Supabase do `.env`: enviar grava linhas de verdade
na conta dona do token. A ingestão é idempotente (`DATA-08`): reenviar a mesma
noite não duplica nada.

── O QUE É REAL E O QUE É SINTÉTICO ─────────────────────────────────────

Real, por construção:
  * as seis características e o `g` saem de `ml/src/features.py::
    features_de_epoca` — a referência que o firmware copia linha por linha e
    com que o modelo foi treinado. Não há uma terceira implementação;
  * o pico (`ax/ay/az/total`) é o da grade de 32 Hz, convertido por 9,81, com
    2 casas, e o `status` é a regra do firmware (`firmware/nucleo/epoca_c2.cpp`
    e `payload.h`); `amostras` = 960, `fs` = 32, `ts` = INÍCIO da época;
  * o envio segue `firmware/nucleo/lote.h`: lotes de até 60, confirma o
    prefixo antes do primeiro pendente, divide no 413, recua no resto.

Sintético — e por isso NADA medido sobre estes dados é resultado do TCC:
  * o sinal. É um modelo plausível (gravidade + respiração + ruído do MPU6050,
    rajadas de movimento acordado, viradas de posição no sono), não uma
    gravação. Serve para a corrente funcionar, não para medir o classificador.

A FIFO a 50 Hz e a reamostragem para 32 Hz NÃO são simuladas: essa cadeia tem
vetor dourado próprio (`ml/testes/test_dourado_cadeia_c2.py`). O sinal nasce
direto na grade.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "ml"))
from src.features import FEATURES_DO_DISPOSITIVO, NOMES_FEATURES, features_de_epoca, unitario  # noqa: E402

# --------------------------------------------------------------------------
# Constantes do firmware. O teste confere cada uma contra o arquivo C++ de
# onde veio, em vez de confiar nesta cópia.
# --------------------------------------------------------------------------
GRAVIDADE_MS2 = 9.81          # payload.h — o pico em g vira m/s² por este fator
LIMIAR_MOVIMENTO_MS2 = 1.2    # payload.h — PROVISÓRIO até o CAL-01
METODO_AGREGACAO = "pico-da-magnitude"
MAX_LEITURAS_POR_LOTE = 60    # lote.h
TOKEN_HEADER = "X-Device-Token"  # web-app/device_auth.py

EPOCA_S = 30
FS_GRADE = 32.0
AMOSTRAS = int(EPOCA_S * FS_GRADE)  # 960

#: No tempo real o firmware acorda a tarefa de envio a cada 10 min (sketch.ino,
#: INTERVALO_DE_ENVIO_US): ~20 épocas por lote.
EPOCAS_POR_ENVIO_TEMPO_REAL = 20

ACORDADO, SONO = "acordado", "sono"


def classificar(total_ms2: float) -> str:
    """A regra do firmware (`payload.h::classificar`)."""
    return "Movimento" if abs(total_ms2 - GRAVIDADE_MS2) > LIMIAR_MOVIMENTO_MS2 else "Repouso"


def formatar_ts(instante: datetime) -> str:
    """`AAAA-MM-DDTHH:MM:SS.mmmZ`, como `formatar_iso8601_utc` do firmware."""
    u = instante.astimezone(timezone.utc)
    return u.strftime("%Y-%m-%dT%H:%M:%S.") + f"{u.microsecond // 1000:03d}Z"


# ==========================================================================
# A noite sintética
# ==========================================================================
@dataclass
class EpocaGerada:
    indice: int
    inicio: datetime
    estado: str            # gabarito: ACORDADO ou SONO
    evento: str            # "", "virada" ou "movimento"
    grade: np.ndarray      # (960, 3), em g
    temp_c: float


def _rotacao(u: np.ndarray, v: np.ndarray, frac: float) -> np.ndarray:
    """Interpolação esférica de u para v (unitários), na fração `frac`."""
    c = float(np.clip(np.dot(u, v), -1.0, 1.0))
    ang = math.acos(c)
    if ang < 1e-9:
        return u.copy()
    s = math.sin(ang)
    return (math.sin((1 - frac) * ang) * u + math.sin(frac * ang) * v) / s


def _girar(u: np.ndarray, graus: float, rng: np.random.Generator) -> np.ndarray:
    """`u` girado de `graus` em torno de um eixo aleatório perpendicular a ele."""
    eixo = np.cross(u, unitario(rng.normal(size=3)))
    eixo = unitario(eixo)
    t = math.radians(graus)
    return unitario(u * math.cos(t) + np.cross(eixo, u) * math.sin(t))


def hipnograma(n_epocas: int, rng: np.random.Generator) -> tuple[list[str], list[str]]:
    """Estado e evento de cada época. Simples e declarado:

    * latência de 10–25 min acordado no começo, e 5–15 min acordado no fim;
    * no sono, despertares curtos (2–6 min) a ~0,8 por hora e viradas de
      posição a ~2 por hora;
    * acordado, quase toda época tem alguma rajada de movimento.
    """
    estado = [SONO] * n_epocas
    evento = [""] * n_epocas
    lat = min(n_epocas, int(rng.integers(20, 51)))
    fim = min(n_epocas - lat, int(rng.integers(10, 31)))
    for i in range(lat):
        estado[i] = ACORDADO
    for i in range(n_epocas - fim, n_epocas):
        estado[i] = ACORDADO

    i = lat
    while i < n_epocas - fim:
        if rng.random() < 0.8 / 120:            # despertar
            dur = int(rng.integers(4, 13))
            for j in range(i, min(i + dur, n_epocas - fim)):
                estado[j] = ACORDADO
            i += dur
            continue
        if rng.random() < 2.0 / 120:            # virada
            evento[i] = "virada"
        i += 1

    for i in range(n_epocas):
        if estado[i] == ACORDADO and rng.random() < 0.85:
            evento[i] = "movimento"
    return estado, evento


class NoiteSintetica:
    """Gera as épocas uma a uma — a orientação do travesseiro é o estado."""

    def __init__(self, inicio: datetime, n_epocas: int, seed: int = 0):
        if inicio.tzinfo is None:
            raise ValueError("inicio precisa de fuso")
        self.inicio = inicio
        self.n_epocas = n_epocas
        self.rng = np.random.default_rng(seed)
        self.estados, self.eventos = hipnograma(n_epocas, self.rng)
        self._g = unitario(self.rng.normal(size=3))
        self._temp = 30.0 + float(self.rng.uniform(0.0, 1.0))
        self._resp_hz = float(self.rng.uniform(0.2, 0.3))
        self._resp_dir = unitario(self.rng.normal(size=3))

    def __iter__(self):
        for k in range(self.n_epocas):
            yield self.epoca(k)

    def epoca(self, k: int) -> EpocaGerada:
        rng = self.rng
        t = (k * EPOCA_S) + np.arange(AMOSTRAS) / FS_GRADE
        estado, evento = self.estados[k], self.eventos[k]

        # Orientação: constante, salvo virada (sono) ou ajuste pequeno (acordado).
        g_ini = self._g.copy()
        if evento == "virada":
            g_fim = _girar(g_ini, float(rng.uniform(30, 90)), rng)
        elif estado == ACORDADO and rng.random() < 0.3:
            g_fim = _girar(g_ini, float(rng.uniform(5, 20)), rng)
        else:
            g_fim = g_ini
        i0 = int(rng.integers(64, AMOSTRAS - 160))
        dur = int(rng.integers(64, 129))          # 2 a 4 s de transição
        frac = np.clip((np.arange(AMOSTRAS) - i0) / dur, 0.0, 1.0)
        grav = np.array([_rotacao(g_ini, g_fim, f) for f in frac])
        self._g = g_fim

        # Respiração transmitida ao travesseiro e ruído do MPU6050 (~2 mg).
        a = grav + np.outer(np.sin(2 * np.pi * self._resp_hz * t), self._resp_dir) \
            * float(rng.uniform(0.001, 0.003))
        a += rng.normal(0.0, 0.002, (AMOSTRAS, 3))

        # Movimento: rajadas de 1–4 s, 0,5–3 Hz, de 0,05 a 0,3 g acordado; a
        # própria virada carrega uma rajada durante a transição.
        rajadas = []
        if evento == "movimento":
            rajadas = [(int(rng.integers(0, AMOSTRAS - 128)), int(rng.integers(32, 129)),
                        float(rng.uniform(0.05, 0.3))) for _ in range(int(rng.integers(1, 5)))]
        elif evento == "virada":
            rajadas = [(i0, dur, float(rng.uniform(0.1, 0.4)))]
        for ini, n, amp in rajadas:
            fim = min(ini + n, AMOSTRAS)
            tt = t[ini:fim]
            d = unitario(rng.normal(size=3))
            env = np.hanning(fim - ini)
            a[ini:fim] += np.outer(env * np.sin(2 * np.pi * rng.uniform(0.5, 3.0) * tt), d) * amp

        # Temperatura do CHIP: sobe devagar com o calor da cabeça, até ~33 °C.
        self._temp += (33.0 - self._temp) * 0.01 + float(rng.normal(0.0, 0.02))

        return EpocaGerada(k, self.inicio + timedelta(seconds=k * EPOCA_S),
                           estado, evento, a, self._temp)


# ==========================================================================
# Da época ao payload — o que o firmware monta
# ==========================================================================
def payload_da_epoca(e: EpocaGerada) -> dict:
    X, g_media = features_de_epoca(e.grade[None, :, :], fs=FS_GRADE)
    # Pico da grade (`epoca_da_grade`): a amostra de maior |a|, em m/s².
    m2 = np.einsum("ij,ij->i", e.grade, e.grade)
    i = int(np.argmax(m2))
    total = math.sqrt(float(m2[i])) * GRAVIDADE_MS2
    ax, ay, az = (float(v) * GRAVIDADE_MS2 for v in e.grade[i])
    return {
        "ax": round(ax, 2), "ay": round(ay, 2), "az": round(az, 2),
        "t": round(e.temp_c, 1),
        "total": round(total, 2),
        "status": classificar(total),
        "ts": formatar_ts(e.inicio),
        "epoca_s": EPOCA_S,
        "metodo": METODO_AGREGACAO,
        "amostras": AMOSTRAS,
        "f": [float(X[0, NOMES_FEATURES.index(n)]) for n in FEATURES_DO_DISPOSITIVO],
        "g": [float(v) for v in unitario(g_media[0])],
        "fs": FS_GRADE,
    }


# ==========================================================================
# O envio — a regra de `firmware/nucleo/lote.h`
# ==========================================================================
def transporte_http(url: str, token: str, corpo: dict, timeout_s: float = 15.0) -> tuple[int, str]:
    """POST com a biblioteca padrão. Erro de rede = status -1, como no firmware."""
    req = urllib.request.Request(
        url, data=json.dumps(corpo).encode("utf-8"), method="POST",
        headers={"Content-Type": "application/json", TOKEN_HEADER: token})
    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        return -1, str(e)


@dataclass
class ResumoDoEnvio:
    aceitas: int = 0
    rejeitadas: int = 0
    lotes: int = 0
    divisoes: int = 0
    recuos: int = 0
    motivos_de_rejeicao: list = field(default_factory=list)
    interrompido: str = ""   # vazio = a fila esvaziou


def _prefixo_confirmado(resposta: dict, enviadas: int) -> tuple[int, int, int] | None:
    """(confirmar, aceitas, rejeitadas) no prefixo antes do 1º pendente; None se incoerente."""
    try:
        ac = {int(i) for i in resposta["aceitas"]}
        rj = {int(x["indice"]) for x in resposta["rejeitadas"]}
        pe = {int(i) for i in resposta["pendentes"]}
    except (KeyError, TypeError, ValueError):
        return None
    if ac | rj | pe != set(range(enviadas)) or len(ac) + len(rj) + len(pe) != enviadas:
        return None
    confirmar = min(pe) if pe else enviadas
    return (confirmar, sum(1 for i in ac if i < confirmar), sum(1 for i in rj if i < confirmar))


def enviar_fila(fila: list[dict], url: str, token: str, transporte=transporte_http,
                dormir=time.sleep, max_recuos_seguidos: int = 5,
                avisar=print) -> ResumoDoEnvio:
    """Esvazia `fila` (lista de payloads, a mais antiga primeiro) em lotes.

    Remove da `fila` o que foi confirmado; o que sobrar ficou para depois.
    """
    r = ResumoDoEnvio()
    tamanho = MAX_LEITURAS_POR_LOTE
    recuos_seguidos = 0
    while fila:
        lote = fila[:tamanho]
        status, texto = transporte(url, token, {"leituras": lote})
        r.lotes += 1

        if status == 413:
            if tamanho == 1:
                r.interrompido = "413 com uma leitura só"
                return r
            tamanho = max(1, tamanho // 2)
            r.divisoes += 1
            avisar(f"  413: lote dividido para {tamanho}")
            continue

        if status in (401, 403):
            r.interrompido = f"HTTP {status}: confira o DORMIO_DEVICE_TOKEN"
            return r

        decisao = None
        if status in (200, 503):
            try:
                corpo = json.loads(texto)
                decisao = _prefixo_confirmado(corpo, len(lote))
            except ValueError:
                decisao = None
            if decisao is not None:
                for x in corpo["rejeitadas"]:
                    if int(x["indice"]) < decisao[0]:
                        r.motivos_de_rejeicao.append(x.get("erro", ""))

        if decisao is not None and decisao[0] > 0:
            confirmar, ac, rj = decisao
            del fila[:confirmar]
            r.aceitas += ac
            r.rejeitadas += rj
            recuos_seguidos = 0
            avisar(f"  HTTP {status}: {ac} aceitas, {rj} rejeitadas, "
                   f"{len(lote) - confirmar} pendentes; faltam {len(fila)}")
            continue

        # Nada confirmado: 5xx, resposta ilegível, rede, 400 de envelope.
        recuos_seguidos += 1
        r.recuos += 1
        if recuos_seguidos > max_recuos_seguidos:
            r.interrompido = f"HTTP {status} {recuos_seguidos} vezes seguidas: {texto[:200]}"
            return r
        espera = 2 ** recuos_seguidos
        avisar(f"  HTTP {status}: nada confirmado; nova tentativa em {espera} s")
        dormir(espera)
    return r


# ==========================================================================
# Linha de comando
# ==========================================================================
def _inicio_padrao(agora_local: datetime, duracao: timedelta) -> datetime:
    """As 23h mais recentes (fuso local) cuja noite já terminou.

    De madrugada, "ontem às 23h" ainda não acabou — e o servidor recusa `ts`
    no futuro —, então recua um dia.
    """
    d = agora_local.date()
    inicio = datetime(d.year, d.month, d.day, 23, 0, tzinfo=agora_local.tzinfo)
    while inicio + duracao > agora_local:
        inicio -= timedelta(days=1)
    return inicio


def _gravar_gabarito(caminho: Path, epocas: list[EpocaGerada], payloads: list[dict]) -> None:
    with open(caminho, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["ts", "estado", "evento", "status"])
        for e, p in zip(epocas, payloads):
            w.writerow([p["ts"], e.estado, e.evento, p["status"]])


def _resumo_da_noite(epocas: list[EpocaGerada], payloads: list[dict]) -> str:
    n = len(epocas)
    sono = sum(e.estado == SONO for e in epocas)
    viradas = sum(e.evento == "virada" for e in epocas)
    mov = sum(p["status"] == "Movimento" for p in payloads)
    return (f"{n} épocas ({n * EPOCA_S / 3600:.1f} h), de {payloads[0]['ts']} a {payloads[-1]['ts']}; "
            f"gabarito: {sono} de sono ({100 * sono / n:.0f} %), {viradas} viradas; "
            f"{mov} épocas com status Movimento")


def main(argv=None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--inicio", help="início da noite, ISO 8601 (padrão: as 23h mais recentes cuja noite já terminou)")
    p.add_argument("--horas", type=float, default=8.0)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--seco", action="store_true", help="gera e resume, sem enviar")
    p.add_argument("--tempo-real", action="store_true",
                   help="uma época a cada 30 s a partir de agora, enviando a cada --por-envio")
    p.add_argument("--por-envio", type=int, default=EPOCAS_POR_ENVIO_TEMPO_REAL)
    p.add_argument("--gabarito", type=Path, help="CSV local com o estado verdadeiro de cada época")
    a = p.parse_args(argv)

    url = os.environ.get("DORMIO_API_URL", "http://127.0.0.1:5000").rstrip("/") + "/api/data/lote"
    token = os.environ.get("DORMIO_DEVICE_TOKEN", "")
    if not a.seco and not token:
        print("Defina DORMIO_DEVICE_TOKEN (token do dispositivo pareado) ou use --seco.")
        return 2
    n_epocas = int(round(a.horas * 3600 / EPOCA_S))
    agora = datetime.now().astimezone()

    if a.tempo_real:
        inicio = datetime.fromtimestamp(math.floor(agora.timestamp() / EPOCA_S) * EPOCA_S,
                                        tz=agora.tzinfo)
        return _tempo_real(NoiteSintetica(inicio, n_epocas, a.seed), url, token, a)

    inicio = (datetime.fromisoformat(a.inicio) if a.inicio
              else _inicio_padrao(agora, timedelta(seconds=n_epocas * EPOCA_S)))
    if inicio.tzinfo is None:
        inicio = inicio.replace(tzinfo=agora.tzinfo)
    if inicio + timedelta(seconds=n_epocas * EPOCA_S) > agora:
        print("A noite termina no futuro, e o servidor recusa `ts` futuro. "
              "Use --inicio mais cedo, menos --horas ou --tempo-real.")
        return 2

    noite = NoiteSintetica(inicio, n_epocas, a.seed)
    epocas = list(noite)
    payloads = [payload_da_epoca(e) for e in epocas]
    print(_resumo_da_noite(epocas, payloads))
    if a.gabarito:
        _gravar_gabarito(a.gabarito, epocas, payloads)
        print(f"gabarito em {a.gabarito}")
    if a.seco:
        print("--seco: nada enviado. Primeira época:")
        print(json.dumps(payloads[0], ensure_ascii=False))
        return 0

    print(f"enviando para {url}")
    r = enviar_fila(list(payloads), url, token)
    print(f"{r.aceitas} aceitas, {r.rejeitadas} rejeitadas, {r.lotes} requisições, "
          f"{r.divisoes} divisões, {r.recuos} recuos")
    for m in sorted(set(r.motivos_de_rejeicao)):
        print(f"  rejeição: {m}")
    if r.interrompido:
        print(f"INTERROMPIDO: {r.interrompido}")
        return 1
    return 0


def _tempo_real(noite: NoiteSintetica, url: str, token: str, a) -> int:
    fila: list[dict] = []
    epocas, payloads = [], []
    print(f"tempo real: uma época a cada {EPOCA_S} s, envio a cada {a.por_envio}. CTRL+C para.")
    try:
        for e in noite:
            fim = e.inicio + timedelta(seconds=EPOCA_S)
            espera = (fim - datetime.now(timezone.utc)).total_seconds()
            if espera > 0:
                time.sleep(espera)
            pl = payload_da_epoca(e)
            epocas.append(e)
            payloads.append(pl)
            fila.append(pl)
            print(f"{pl['ts']}  {e.estado:8s} {e.evento:9s} {pl['status']}")
            if len(fila) >= a.por_envio and not a.seco:
                r = enviar_fila(fila, url, token)
                if r.interrompido:
                    print(f"INTERROMPIDO: {r.interrompido}")
                    return 1
    except KeyboardInterrupt:
        pass
    if fila and not a.seco:
        enviar_fila(fila, url, token)
    if a.gabarito and epocas:
        _gravar_gabarito(a.gabarito, epocas, payloads)
    return 0


if __name__ == "__main__":
    sys.exit(main())
