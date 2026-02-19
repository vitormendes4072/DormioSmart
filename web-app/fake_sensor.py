import time
import random
import requests
import math

# URL da sua API local (onde o Flask está rodando)
API_URL = "http://127.0.0.1:5000/api/data"

def gerar_dados_simulados():
    print(f"📡 Iniciando simulação do Sensor MPU6050 para: {API_URL}")
    print("Pressione CTRL+C para parar.\n")

    # Temperatura base do quarto (começa em 24°C)
    temp_atual = 24.0

    while True:
        try:
            # 1. Simula Temperatura (oscila levemente)
            temp_atual += random.uniform(-0.1, 0.1)
            
            # 2. Simula Acelerômetro (Valores de gravidade + movimento)
            # Simula alguém dormindo: movimentos pequenos e ocasionais picos
            if random.random() > 0.8: 
                # 20% de chance de movimento brusco (virou na cama)
                ax = random.uniform(-5, 5)
                ay = random.uniform(-5, 5)
                az = random.uniform(-5, 5)
                status = "Movimento Detectado!"
            else:
                # 80% de chance de estar parado (respiração apenas)
                ax = random.uniform(-0.5, 0.5)
                ay = random.uniform(-0.5, 0.5)
                az = random.uniform(9.0, 10.0) # Gravidade (~9.8 m/s²)
                status = "Dormindo"

            # 3. Simula Giroscópio
            gx = random.uniform(-2, 2)
            gy = random.uniform(-2, 2)
            gz = random.uniform(-2, 2)

            # 4. Calcula Magnitude do Vetor (Total)
            movimento_total = math.sqrt(ax**2 + ay**2 + az**2)

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
            response = requests.post(API_URL, json=payload)

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