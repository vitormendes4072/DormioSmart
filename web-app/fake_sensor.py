import math
import os
import random
import time

import httpx

from device_auth import TOKEN_HEADER

# URL da sua API local (onde o Flask está rodando)
API_URL = "http://127.0.0.1:5000/api/data"

# Token do dispositivo (SEC-02). O backend exige o header X-Device-Token; sem
# ele a API responde 401. Pareie um device pela aplicação e exporte o token:
#   export DORMIO_DEVICE_TOKEN="<token>"     (Windows: $env:DORMIO_DEVICE_TOKEN=...)
DEVICE_TOKEN = os.environ.get("DORMIO_DEVICE_TOKEN", "")

# --- CRITÉRIO DE MOVIMENTO (docs/DATA-CONTRACT.md v1.1.0) ---
# Réplica exata da regra do firmware. Se um dos dois mudar, o outro muda junto:
# o simulador só tem valor enquanto for indistinguível do dispositivo real.
GRAVIDADE = 9.81         # m/s² — referência de repouso
LIMIAR_MOVIMENTO = 1.2   # m/s² — PROVISÓRIO, calibrar em VIA-01
STATUS_REPOUSO = "Repouso"
STATUS_MOVIMENTO = "Movimento"

# Temperatura do CHIP do MPU6050 — não é temperatura ambiente nem corporal.
# O sensor interno do MPU6050 mede o próprio circuito integrado, que opera
# alguns graus acima do ambiente. Ver docs/DATA-CONTRACT.md seção 2.3.
TEMP_CHIP_INICIAL = 32.0  # °C


def classificar(movimento_total):
    """Classifica uma magnitude de aceleração como repouso ou movimento.

    Usa o desvio ABSOLUTO em relação à gravidade — o mesmo critério simétrico
    do firmware e da intensidade exibida no dashboard.
    """
    intensidade = abs(movimento_total - GRAVIDADE)
    return STATUS_MOVIMENTO if intensidade > LIMIAR_MOVIMENTO else STATUS_REPOUSO

def gerar_dados_simulados():
    print(f"📡 Iniciando simulação do Sensor MPU6050 para: {API_URL}")
    print("Pressione CTRL+C para parar.\n")

    # Temperatura do chip do MPU6050 (não do quarto — ver constantes acima)
    temp_atual = TEMP_CHIP_INICIAL

    while True:
        try:
            # 1. Simula a temperatura do chip (oscila levemente)
            temp_atual += random.uniform(-0.1, 0.1)
            
            # 2. Simula Acelerômetro (Valores de gravidade + movimento)
            # Simula alguém dormindo: movimentos pequenos e ocasionais picos
            if random.random() > 0.8: 
                # 20% de chance de movimento brusco (virou na cama)
                ax = random.uniform(-5, 5)
                ay = random.uniform(-5, 5)
                az = random.uniform(-5, 5)
            else:
                # 80% de chance de estar parado (respiração apenas)
                ax = random.uniform(-0.5, 0.5)
                ay = random.uniform(-0.5, 0.5)
                az = random.uniform(9.0, 10.0) # Gravidade (~9.8 m/s²)

            # 3. Simula Giroscópio
            gx = random.uniform(-2, 2)
            gy = random.uniform(-2, 2)
            gz = random.uniform(-2, 2)

            # 4. Calcula Magnitude do Vetor (Total) e classifica pela mesma
            #    regra do firmware — o status não é decidido "na mão".
            movimento_total = math.sqrt(ax**2 + ay**2 + az**2)
            status = classificar(movimento_total)

            # 5. Monta o pacote JSON (Exatamente como o ESP32 enviará)
            payload = {
                "ax": ax,
                "ay": ay,
                "az": az,
                "gx": gx,
                "gy": gy,
                "gz": gz,
                "t": temp_atual,
                "total": movimento_total,
                "status": status
            }

            # 6. Envia para o Flask
            response = httpx.post(
                API_URL, json=payload, headers={TOKEN_HEADER: DEVICE_TOKEN}
            )

            if response.status_code == 201:
                print(f"✅ [201] Dados enviados! Temp: {temp_atual:.1f}°C | Mov: {movimento_total:.2f} | {status}")
            else:
                print(f"❌ [{response.status_code}] Erro: {response.text}")

        except Exception as e:
            print(f"⚠️ Erro de conexão: {e}")
            print("Certifique-se que o 'app.py' está rodando em outro terminal!")

        # Espera 3 segundos antes do próximo envio
        time.sleep(3)

if __name__ == "__main__":
    gerar_dados_simulados()