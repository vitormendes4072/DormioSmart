#include <Adafruit_MPU6050.h>
#include <Adafruit_Sensor.h>
#include <Wire.h>

// --- CONFIGURAÇÃO MESTRA ---
// Deixe como 'true' para usar no Wokwi. 
// Mude para 'false' quando for gravar na placa real do TCC.
#define MODO_SIMULADOR true 

Adafruit_MPU6050 mpu;
#define PINO_WAKEUP GPIO_NUM_27

void setup() {
  Serial.begin(115200);
  pinMode(PINO_WAKEUP, INPUT); // Resistor físico de 10k garante o LOW

  // Verifica quem acordou (Funciona no Hardware Real)
  esp_sleep_wakeup_cause_t causa = esp_sleep_get_wakeup_cause();

  Serial.println("\n=====================================");
  // No simulador, sempre vai parecer que ligou do zero, e tudo bem.
  if(causa == ESP_SLEEP_WAKEUP_EXT1 || causa == ESP_SLEEP_WAKEUP_EXT0){
    Serial.println(">>> HARDWARE REAL: ACORDEI PELO BOTAO! <<<");
  } else {
    Serial.println(">>> INICIO DO SISTEMA <<<");
  }

  // Tenta iniciar o sensor
  if (!mpu.begin()) {
    Serial.println("Sensor MPU6050: Offline (Seguindo sem ele)...");
  } else {
    Serial.println("Sensor MPU6050: Online.");
    mpu.enableSleep(true); // Coloca o sensor para dormir
  }

  Serial.println("Verificando Pino 27...");
  delay(100);
  if (digitalRead(PINO_WAKEUP) == HIGH) {
    Serial.println("ALERTA: Botao pressionado! Solte o botao.");
    // Espera soltar o botão para não reiniciar em loop
    while(digitalRead(PINO_WAKEUP) == HIGH) delay(10);
  } else {
    Serial.println("Pino em LOW. Tudo OK.");
  }

  Serial.println("Processando dados (Simulacao)...");
  delay(1000);

  Serial.println("Zzz... Entrando em MODO SLEEP.");
  Serial.println("--- O SISTEMA VAI PARAR AGORA. CLIQUE NO BOTAO PARA ACORDAR ---");
  Serial.flush(); // Garante que o texto saia antes de travar

  // --- A MÁGICA DA DUPLA PERSONALIDADE ---
  
  if (MODO_SIMULADOR) {
    // === COMPORTAMENTO PARA O WOKWI ===
    // Aqui nós "fingimos" o sono travando o código num loop infinito
    // O sistema para de responder (parece que dormiu).
    // Quando você aperta o botão, ele sai do loop e reinicia.
    
    while(digitalRead(PINO_WAKEUP) == LOW) {
      // Fica preso aqui eternamente gastando processamento (mas no simulador não importa)
      delay(50); 
    }
    
    // Se saiu do while, é porque apertaram o botão!
    Serial.println("\n>>> WOKWI: BOTAO DETECTADO! REINICIANDO... <<<");
    delay(500);
    ESP.restart(); // Reinicia o ESP32 para simular o "Acordar"

  } else {
    // === COMPORTAMENTO PARA O HARDWARE REAL (TCC) ===
    // Configura o despertar real (EXT1 é mais robusto)
    uint64_t mascara = (1ULL << GPIO_NUM_27);
    esp_sleep_enable_ext1_wakeup(mascara, ESP_EXT1_WAKEUP_ANY_HIGH);
    
    // Desliga o chip de verdade
    esp_deep_sleep_start();
  }
}

void loop() {
  // Nada aqui
}