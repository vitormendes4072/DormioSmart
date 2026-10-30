"""Validação da leitura enviada pelo dispositivo (SEC-03).

O backend não confia no cliente. Um ESP32 com sensor solto, firmware antigo ou
um POST forjado com token roubado não podem contaminar a base — dado sujo em
estudo de actigrafia não é só bug, é resultado inválido no TCC.

As faixas abaixo saem da configuração real do sensor em `firmware/sketch.ino`,
com margem. Rejeição devolve 400 com o motivo.

── CONTRATO v2.0.0: DOIS TIPOS DE DISPOSITIVO ────────────────────────────

Até a v1.2.0 o único emissor era o ESP32, e todo campo era obrigatório. Com o
celular como segunda fonte (APP-01), três campos deixaram de fazer sentido
universal:

- `t` é a temperatura do **chip do MPU6050**. Um celular não expõe nada
  equivalente. Enviar número inventado seria mentir no dado.
- `gx/gy/gz` dependem de giroscópio, que nem todo aparelho tem — e a web pode
  devolver `rotationRate` nulo. O giroscópio **não entra em nenhum critério**:
  o movimento é decidido só pela magnitude da aceleração.

Ausente é aceito; presente continua sendo validado com a mesma régua. É o
oposto de aceitar lixo: o que entra continua tendo que ser número finito
dentro da faixa.

Contrato: docs/DATA-CONTRACT.md v2.0.0, seções 2 e 5.
"""
import math
from datetime import datetime, timedelta, timezone

# --- Limites físicos ------------------------------------------------------
# Acelerômetro em MPU6050_RANGE_8_G -> ±8 g = ±78,5 m/s². Margem até 100.
# Celular típico vai a ±16 g = ±157 m/s², mas o teto de `total` já cobre.
_ACCEL_MAX = 100.0
# União das duas classes de dispositivo: MPU6050 em ±500 °/s dá ±8,73 rad/s;
# giroscópio de celular vai a ±2000 °/s ≈ ±34,9 rad/s. Teto em 40.
#
# TRADEOFF ASSUMIDO: com o teto antigo (12), um MPU6050 corrompido reportando
# 30 rad/s era rejeitado — fisicamente impossível naquela configuração. Esse
# filtro se perde. Aceito porque o giroscópio não alimenta nenhuma decisão, e
# porque a alternativa (faixa por tipo de dispositivo) acopla a validação ao
# cadastro para proteger um campo que ninguém lê.
_GYRO_MAX = 40.0
# Faixa de operação do MPU6050 segundo o datasheet.
_TEMP_MIN, _TEMP_MAX = -40.0, 85.0
# Magnitude do vetor: nunca negativa; teto = √3 · _ACCEL_MAX, arredondado.
_TOTAL_MIN, _TOTAL_MAX = 0.0, 175.0

# Sempre exigidos: sem eles não há leitura, só um objeto JSON.
CAMPOS_NUMERICOS = {
    "ax": (-_ACCEL_MAX, _ACCEL_MAX),
    "ay": (-_ACCEL_MAX, _ACCEL_MAX),
    "az": (-_ACCEL_MAX, _ACCEL_MAX),
    "total": (_TOTAL_MIN, _TOTAL_MAX),
}

# Aceitos ausentes; validados quando presentes. Ver a nota no topo.
CAMPOS_OPCIONAIS = {
    "gx": (-_GYRO_MAX, _GYRO_MAX),
    "gy": (-_GYRO_MAX, _GYRO_MAX),
    "gz": (-_GYRO_MAX, _GYRO_MAX),
    "t": (_TEMP_MIN, _TEMP_MAX),
}

STATUS_VALIDOS = ("Repouso", "Movimento")

# Época de agregação, em segundos. Ausente = amostra instantânea (o ESP32).
# Presente = a leitura resume uma janela, e `metodo` diz como.
EPOCA_MINIMA, EPOCA_MAXIMA = 1, 3600
# Identificadores de método de agregação (CALC-03 formaliza a escolha; o
# identificador viaja com o dado para que mudar de método depois não torne o
# histórico ambíguo).
METODOS_DE_AGREGACAO = ("pico-da-magnitude",)

# Relógio de celular é ajustável. Ver a nota em `validar_captacao`.
TOLERANCIA_DE_ADIANTAMENTO = timedelta(minutes=5)

# --- Vetor de características por época (contrato v2.5.0 §2.6, DATA-07b) ---
# A ORDEM é a canônica de `ml/src/features.py::FEATURES_DO_DISPOSITIVO`, e
# trocá-la é mudança MAJOR do contrato: um vetor na ordem errada passa em toda
# faixa e produz um modelo errado em silêncio. As faixas são as da tabela do
# §2.6, em **g** — `f` não está em m/s², ao contrário do resto do payload.
FEATURES_DO_DISPOSITIVO = (
    ("enmo_media", 0.0, 1.0),
    ("enmo_desvio", 0.0, 1.0),
    ("enmo_max", 0.0, 16.0),
    ("mag_din_media", 0.0, 2.0),
    ("zcr", 0.0, 1.0),
    ("p_frac", 0.0, 1.0),
)
# `‖g‖ = 1 ± 1e-3` é checagem de COERÊNCIA (o vetor é unitário?), não régua de
# paridade entre implementações — ver a nota do §2.6.
TOLERANCIA_NORMA_G = 1e-3
# A taxa que produziu o vetor. Na C2 é a da grade, 32 Hz; o teto cobre
# qualquer taxa de acelerômetro de celular.
FS_MAXIMA = 200.0

# `total` deve bater com a magnitude de (ax, ay, az). O firmware transmite os
# valores com 2 casas decimais, então a diferença esperada é de centésimos;
# 0,5 m/s² é folga generosa que ainda pega payload montado errado.
TOLERANCIA_COERENCIA = 0.5


def _numero_valido(valor):
    """True para int/float finito. Exclui bool de propósito: em Python
    `isinstance(True, int)` é True, e `"ax": true` não é uma leitura."""
    if isinstance(valor, bool):
        return False
    if not isinstance(valor, (int, float)):
        return False
    return math.isfinite(valor)


def validar_leitura(content):
    """Valida o corpo do POST /api/data.

    Devolve `(None, motivo)` quando inválido e `(content, None)` quando aceito.
    """
    if not isinstance(content, dict):
        return None, "corpo deve ser um objeto JSON"

    for campo, (minimo, maximo) in CAMPOS_NUMERICOS.items():
        if campo not in content or content[campo] is None:
            return None, f"campo obrigatorio ausente: {campo}"

        erro = _fora_da_faixa(campo, content[campo], minimo, maximo)
        if erro:
            return None, erro

    for campo, (minimo, maximo) in CAMPOS_OPCIONAIS.items():
        # Ausente e nulo são a mesma coisa aqui: o dispositivo não tem o sensor.
        if content.get(campo) is None:
            continue

        erro = _fora_da_faixa(campo, content[campo], minimo, maximo)
        if erro:
            return None, erro

    status = content.get("status")
    if not isinstance(status, str) or status not in STATUS_VALIDOS:
        return None, (
            f"campo status deve ser um de {list(STATUS_VALIDOS)}"
        )

    magnitude = math.sqrt(
        content["ax"] ** 2 + content["ay"] ** 2 + content["az"] ** 2
    )
    if abs(content["total"] - magnitude) > TOLERANCIA_COERENCIA:
        return None, (
            f"campo total incoerente com (ax, ay, az): "
            f"recebido {content['total']:.2f}, esperado ~{magnitude:.2f}"
        )

    erro = _recusar_sensor_mudo(content)
    if erro:
        return None, erro

    content, erro = _validar_agregacao(content)
    if erro:
        return None, erro

    erro = _validar_features(content)
    if erro:
        return None, erro
    return content, None


def _recusar_sensor_mudo(content):
    """Recusa a assinatura de sensor que responde mas nao mede (SEC-06).

    ── O CASO REAL ──────────────────────────────────────────────────────

    Em 25/08/2026, durante a caracterizacao de bancada, o MPU6050 passou a
    devolver TODOS os registradores zerados. O delator foi a temperatura:
    36,5 C e exatamente o que a biblioteca produz com o registrador em zero
    (`raw / 340 + 36,53`). Causa tipica: alimentacao mal encaixada — o chip
    sobrevive do vazamento dos pull-ups do I2C, responde no barramento e nao
    mede.

    ── POR QUE O BACKEND PRECISA RECUSAR ────────────────────────────────

    Com os eixos zerados, `total` = 0 e o dispositivo calcula a intensidade
    como |0 - 9,81| = 9,81, muito acima do limiar. Ele classifica como
    MOVIMENTO e envia.

    E o payload passa em tudo o mais: 0 esta dentro da faixa fisica, e a
    coerencia fecha (0 = raiz de 0+0+0). Ou seja, um fio solto encheria a
    base de eventos de movimento FABRICADOS a noite inteira — e num trabalho
    de actigrafia isso nao e tela quebrada, e resultado invalido.

    O firmware ja nao envia (guarda de magnitude implausivel), mas firmware
    velho continua em campo e a base e o que sobra no fim. Defesa em
    profundidade, como o RLS junto do filtro por dono.

    ── POR QUE A REGRA E "OS TRES EXATAMENTE ZERO" ──────────────────────

    Nao um piso de magnitude: em queda livre |a| REALMENTE tende a zero, e
    nao cabe ao backend decidir que isso nunca acontece. Ja os tres eixos
    darem exatamente 0,00 ao mesmo tempo nao e medida — o ruido de um
    acelerometro vivo torna isso praticamente impossivel. E assinatura de
    registrador morto, nao de fisica.
    """
    if content["ax"] == 0 and content["ay"] == 0 and content["az"] == 0:
        return (
            "os tres eixos vieram exatamente zero: assinatura de sensor que "
            "responde mas nao mede (confira a alimentacao do MPU6050)"
        )
    return None


def _fora_da_faixa(campo, valor, minimo, maximo):
    """Devolve o motivo da recusa, ou None se o valor serve."""
    if not _numero_valido(valor):
        return f"campo {campo} deve ser numero finito"
    if not (minimo <= valor <= maximo):
        return f"campo {campo} fora da faixa fisica ([{minimo}, {maximo}]): {valor}"
    return None


def _validar_agregacao(content):
    """Época e método (contrato v2.0.0, APP-01).

    Ambos ausentes = amostra instantânea, o comportamento do ESP32.

    Se `epoca_s` vem, `metodo` é obrigatório: uma leitura que resume 60 s sem
    dizer COMO resumiu não é interpretável depois, e o histórico ficaria
    ambíguo no dia em que o método mudasse. É o mesmo princípio de `status`,
    que viaja com o dado em vez de ser recalculado.
    """
    epoca = content.get("epoca_s")
    metodo = content.get("metodo")

    if epoca is None and metodo is None:
        return content, None

    if epoca is None:
        return None, "campo metodo veio sem epoca_s"

    if isinstance(epoca, bool) or not isinstance(epoca, int):
        return None, "campo epoca_s deve ser inteiro de segundos"

    if not (EPOCA_MINIMA <= epoca <= EPOCA_MAXIMA):
        return None, (
            f"campo epoca_s fora da faixa "
            f"([{EPOCA_MINIMA}, {EPOCA_MAXIMA}]): {epoca}"
        )

    if metodo not in METODOS_DE_AGREGACAO:
        return None, f"campo metodo deve ser um de {list(METODOS_DE_AGREGACAO)}"

    amostras = content.get("amostras")
    if amostras is not None:
        if isinstance(amostras, bool) or not isinstance(amostras, int) or amostras < 1:
            return None, "campo amostras deve ser inteiro maior que zero"

    return content, None


def _validar_features(content):
    """`f`, `g` e `fs` (contrato §2.6, "Validação prevista"; DATA-07b).

    Ausentes os três é o caso normal — e continuará sendo: dispositivo velho
    em campo é dispositivo válido. Presente qualquer um, valem todas as
    regras, e a primeira que falhar recusa a leitura inteira com 400.
    """
    f, gv, fs = content.get("f"), content.get("g"), content.get("fs")
    if f is None and gv is None and fs is None:
        return None
    if f is None or gv is None or fs is None:
        return "campos f, g e fs vem juntos: falta " + ", ".join(
            nome for nome, v in (("f", f), ("g", gv), ("fs", fs)) if v is None)

    # Vetor de características de uma amostra instantânea não significa nada.
    if content.get("epoca_s") is None:
        return "campo f exige epoca_s"

    if not isinstance(f, list) or len(f) != len(FEATURES_DO_DISPOSITIVO):
        return f"campo f deve ser lista de {len(FEATURES_DO_DISPOSITIVO)} numeros"
    for valor, (nome, minimo, maximo) in zip(f, FEATURES_DO_DISPOSITIVO):
        erro = _fora_da_faixa(f"f.{nome}", valor, minimo, maximo)
        if erro:
            return erro

    if not isinstance(gv, list) or len(gv) != 3:
        return "campo g deve ser lista de 3 numeros"
    for valor, eixo in zip(gv, "xyz"):
        erro = _fora_da_faixa(f"g.{eixo}", valor, -1.0, 1.0)
        if erro:
            return erro
    norma = math.sqrt(sum(c * c for c in gv))
    if abs(norma - 1.0) > TOLERANCIA_NORMA_G:
        return f"campo g deve ser unitario (|g| = 1 +- {TOLERANCIA_NORMA_G}): |g| = {norma:.6f}"

    if not _numero_valido(fs) or not (0.0 < fs <= FS_MAXIMA):
        return f"campo fs deve ser numero em (0, {FS_MAXIMA}]"
    return None


#: As colunas de `sleep_data` que guardam o vetor (migração 010). A ordem de
#: `f` vira NOME aqui, uma vez, e daí em diante ninguém depende de posição.
COLUNAS_DE_FEATURES = tuple(nome for nome, _, _ in FEATURES_DO_DISPOSITIVO) + (
    "g_x", "g_y", "g_z", "fs_features")


def colunas_de_features(content):
    """Traduz `f`/`g`/`fs` de uma leitura JÁ VALIDADA para as colunas.

    Sem `f`, as dez colunas vão nulas — que é o que a restrição "tudo ou nada"
    da migração 010 exige.
    """
    f = content.get("f")
    if f is None:
        return {coluna: None for coluna in COLUNAS_DE_FEATURES}
    valores = list(f) + list(content["g"]) + [content["fs"]]
    return dict(zip(COLUNAS_DE_FEATURES, (float(v) for v in valores)))


def validar_captacao(valor):
    """Instante em que a leitura foi MEDIDA (contrato v2.0.0, campo `ts`).

    Devolve `(instante_iso, None)` ou `(None, motivo)`. Ausente é válido e
    devolve `(None, None)`.

    ── POR QUE ISTO PASSOU A EXISTIR ────────────────────────────────────

    Até a v1.2.0 o dispositivo não mandava hora: o ESP32 não tem RTC com
    bateria e perde o relógio a cada Deep Sleep, então o `created_at` do banco
    (hora do RECEBIMENTO) servia — com a rede saudável a diferença é de
    segundos.

    Deixa de servir em dois casos: um celular agrega por época e envia em
    lote, e o buffer offline do HW-05 vai enviar leitura de horas antes. Nos
    dois, o instante do recebimento não é o instante da medição.

    `created_at` continua existindo e continua sendo o do recebimento. O `ts`
    é um campo NOVO, não uma substituição — assim nenhuma linha antiga muda de
    significado.

    ── POR QUE RECUSAR FUTURO ───────────────────────────────────────────

    Relógio de celular é ajustável pelo usuário. Uma leitura carimbada com
    data futura envenenaria qualquer janela de consulta e ficaria pendurada no
    topo do gráfico para sempre. Toleramos 5 minutos de adiantamento, que
    cobre relógio dessincronizado sem aceitar disparate.
    """
    if valor is None:
        return None, None
    if not isinstance(valor, str):
        return None, "campo ts deve ser um instante ISO 8601"

    texto = valor.strip()
    if texto.endswith(("Z", "z")):
        texto = texto[:-1] + "+00:00"
    try:
        instante = datetime.fromisoformat(texto)
    except ValueError:
        return None, "campo ts deve ser um instante ISO 8601"

    if instante.tzinfo is None:
        return None, "campo ts precisa de fuso horario"

    if instante > datetime.now(timezone.utc) + TOLERANCIA_DE_ADIANTAMENTO:
        return None, "campo ts esta no futuro"

    return instante.isoformat(), None
