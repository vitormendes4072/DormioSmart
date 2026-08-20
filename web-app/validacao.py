"""Validação da leitura enviada pelo dispositivo (SEC-03).

O backend não confia no cliente. Um ESP32 com sensor solto, firmware antigo ou
um POST forjado com token roubado não podem contaminar a base — dado sujo em
estudo de actigrafia não é só bug, é resultado inválido no TCC.

As faixas abaixo saem da configuração real do sensor em `firmware/sketch.ino`,
com margem. Rejeição devolve 400 com o motivo.

Contrato: docs/DATA-CONTRACT.md v1.1.0, seções 2 e 5.
"""
import math

# --- Limites físicos ------------------------------------------------------
# Acelerômetro em MPU6050_RANGE_8_G -> ±8 g = ±78,5 m/s². Margem até 100.
_ACCEL_MAX = 100.0
# Giroscópio em MPU6050_RANGE_500_DEG -> ±500 °/s = ±8,73 rad/s. Margem até 12.
_GYRO_MAX = 12.0
# Faixa de operação do MPU6050 segundo o datasheet.
_TEMP_MIN, _TEMP_MAX = -40.0, 85.0
# Magnitude do vetor: nunca negativa; teto = √3 · _ACCEL_MAX, arredondado.
_TOTAL_MIN, _TOTAL_MAX = 0.0, 175.0

CAMPOS_NUMERICOS = {
    "ax": (-_ACCEL_MAX, _ACCEL_MAX),
    "ay": (-_ACCEL_MAX, _ACCEL_MAX),
    "az": (-_ACCEL_MAX, _ACCEL_MAX),
    "gx": (-_GYRO_MAX, _GYRO_MAX),
    "gy": (-_GYRO_MAX, _GYRO_MAX),
    "gz": (-_GYRO_MAX, _GYRO_MAX),
    "t": (_TEMP_MIN, _TEMP_MAX),
    "total": (_TOTAL_MIN, _TOTAL_MAX),
}

STATUS_VALIDOS = ("Repouso", "Movimento")

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

        valor = content[campo]
        if not _numero_valido(valor):
            return None, f"campo {campo} deve ser numero finito"

        if not (minimo <= valor <= maximo):
            return None, (
                f"campo {campo} fora da faixa fisica "
                f"([{minimo}, {maximo}]): {valor}"
            )

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

    return content, None
