#include <WiFi.h>
#include <HTTPClient.h>
#include <WiFiClientSecure.h> // Essencial para conectar no Vercel (HTTPS)
#include <Adafruit_MPU6050.h>
#include <Adafruit_Sensor.h>
#include <Wire.h>

// --- CONFIGURAÇÃO MESTRA ---
// Deixe como 'true' para usar no Wokwi. 
// Mude para 'false' quando for gravar na placa real do TCC.
#define MODO_SIMULADOR true 

// --- CREDENCIAIS DA REDE ---
const char* ssid = "Wokwi-GUEST"; // No hardware real, coloque o nome do seu Wi-Fi
const char* password = "";        // No hardware real, coloque a senha do seu Wi-Fi
String serverName = "https://dormio-smart.vercel.app/api/data"; // Endereço Oficial

Adafruit_MPU6050 mpu;
#define PINO_WAKEUP GPIO_NUM_27

void setup() {
  Serial.begin(115200);
  pinMode(PINO_WAKEUP, INPUT); // Resistor físico de 10k garante o LOW

  // Verifica quem acordou (Funciona no Hardware Real)
  esp_sleep_wakeup_cause_t causa = esp_sleep_get_wakeup_cause();

  Serial.println("\n=====================================");
  if(causa == ESP_SLEEP_WAKEUP_EXT1 || causa == ESP_SLEEP_WAKEUP_EXT0){
    Serial.println(">>> HARDWARE: ACORDEI PELO MOVIMENTO/BOTAO! <<<");
  } else {
    Serial.println(">>> INICIO DO SISTEMA (Ligado na Tomada) <<<");
  }

  // 1. Inicializa o Sensor
  if (!mpu.begin()) {
    Serial.println("Sensor MPU6050: Offline (Seguindo sem ele)...");
  } else {
    Serial.println("Sensor MPU6050: Online.");
    mpu.setAccelerometerRange(MPU6050_RANGE_8_G);
    mpu.setGyroRange(MPU6050_RANGE_500_DEG);
  }

  // 2. Conecta ao Wi-Fi
  Serial.print("Conectando ao WiFi...");
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWiFi Conectado! IP: " + WiFi.localIP().toString());

  // 3. Coleta os Dados (Mesmo se for simulado, mandamos os dados do Wokwi)
  sensors_event_t a, g, temp;
  mpu.getEvent(&a, &g, &temp);

  float total_mov = sqrt(pow(a.acceleration.x, 2) + pow(a.acceleration.y, 2) + pow(a.acceleration.z, 2));
  String status_sono = (total_mov > 11.0 || total_mov < 8.0) ? "Movimento Detectado!" : "Dormindo";

  // 4. Prepara o Payload (O Pacote JSON)
  String jsonPayload = "{";
  jsonPayload += "\"ax\":" + String(a.acceleration.x) + ",";
  jsonPayload += "\"ay\":" + String(a.acceleration.y) + ",";
  jsonPayload += "\"az\":" + String(a.acceleration.z) + ",";
  jsonPayload += "\"gx\":" + String(g.gyro.x) + ",";
  jsonPayload += "\"gy\":" + String(g.gyro.y) + ",";
  jsonPayload += "\"gz\":" + String(g.gyro.z) + ",";
  jsonPayload += "\"t\":" + String(temp.temperature) + ",";
  jsonPayload += "\"total\":" + String(total_mov) + ",";
  jsonPayload += "\"status\":\"" + status_sono + "\"";
  jsonPayload += "}";

  // 5. Envia para a Vercel via HTTPS
  WiFiClientSecure client;
  client.setInsecure(); // Isso é a "Mágica" para o ESP32 ignorar a burocracia do SSL
  HTTPClient http;
  
  Serial.println("Enviando dados para a Nuvem...");
  http.begin(client, serverName);
  http.addHeader("Content-Type", "application/json");
  
  int httpResponseCode = http.POST(jsonPayload);
  
  if (httpResponseCode > 0) {
    Serial.println("✅ [SUCESSO] Dados salvos no Supabase! Codigo HTTP: " + String(httpResponseCode));
  } else {
    Serial.println("❌ [ERRO] Falha ao enviar para Vercel: " + String(httpResponseCode));
  }
  http.end();

  // 6. Preparação para Dormir
  delay(100);
  if (digitalRead(PINO_WAKEUP) == HIGH) {
    Serial.println("ALERTA: Botao ainda pressionado! Solte o botao.");
    while(digitalRead(PINO_WAKEUP) == HIGH) delay(10);
  }

  Serial.println("Zzz... Entrando em MODO SLEEP.");
  Serial.println("--- O SISTEMA PAROU. PRESSIONE O BOTAO (OU MOVA O SENSOR) PARA ACORDAR ---");
  Serial.flush(); // Garante que o texto saia no monitor serial antes de apagar a placa

  // --- A MÁGICA DA DUPLA PERSONALIDADE (Deep Sleep) ---
  if (MODO_SIMULADOR) {
    // WOKWI: Trava num loop infinito simulando o sono
    while(digitalRead(PINO_WAKEUP) == LOW) { delay(50); }
    Serial.println("\n>>> WOKWI: BOTAO DETECTADO! REINICIANDO... <<<");
    delay(500);
    ESP.restart(); 
  } else {
    // HARDWARE REAL: Configura o interruptor e apaga o processador
    uint64_t mascara = (1ULL << GPIO_NUM_27);
    esp_sleep_enable_ext1_wakeup(mascara, ESP_EXT1_WAKEUP_ANY_HIGH);
    esp_deep_sleep_start();
  }
}

void loop() {
  // Totalmente vazio! Um dispositivo IoT de verdade passa a maior parte da vida no setup() e dormindo.
}