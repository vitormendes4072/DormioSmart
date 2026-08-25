/*
 * envio-continuo.ino - fecha o laco coleta -> API -> banco -> dashboard
 *
 * INSTRUMENTO DE BANCADA, NAO FIRMWARE DE PRODUTO.
 * Nao dorme, nao usa botao, nao usa GPIO extra. Le o sensor e envia num
 * intervalo fixo, para sempre.
 *
 * -- POR QUE ELE EXISTE, SE JA HA O sketch.ino ---------------------------
 *
 * O sketch.ino envia UMA leitura e dorme esperando um sinal no GPIO 27. Isso
 * exige botao e resistor de pull-down de 10k, que a ligacao de bancada atual
 * (3V3, GND, SDA=21, SCL=22) nao tem. Com o pino flutuando, `digitalRead`
 * devolve ruido: ou reinicia sozinho, ou nunca acorda. Nao da para testar o
 * laco de dados com essa variavel solta no meio.
 *
 * Aqui o objetivo e outro e mais estreito: provar que a leitura sai do
 * sensor, passa pela validacao da API, chega ao Supabase carimbada com o dono
 * e aparece no painel. Nada de energia, nada de sono.
 *
 * -- FILTRO EM 21 Hz -----------------------------------------------------
 *
 * Igual ao sketch de caracterizacao, e diferente do sketch.ino, que nao chama
 * setFilterBandwidth e roda no padrao de 260 Hz. Movimento de corpo em cama e
 * fenomeno de poucos Hz; largura maior so deixa entrar vibracao de movel e
 * ruido do MEMS. Alinhar o firmware de producao e o item FW-06.
 *
 * -- O QUE ESTE SKETCH NAO CORRIGE ---------------------------------------
 *
 * A medicao de 2026-08-24 mostrou este sensor marcando |a| = 9,20 m/s2
 * PARADO, e nao 9,81. Isso e vies de hardware, e a correcao depende da
 * caracterizacao de 6 posicoes (CALC-02). Aqui o dado vai CRU, de proposito:
 * o objetivo e testar o transporte, e mascarar o vies agora esconderia
 * justamente o que precisa ser medido depois.
 *
 * Consequencia pratica: em repouso a intensidade vai aparecer perto de 0,6 no
 * painel, e nao de 0. O rotulo continua "Repouso" (0,6 < 1,2), mas a folga
 * para baixo fica menor que a folga para cima.
 *
 * -- COMO USAR -----------------------------------------------------------
 *
 * 1. Pareie um dispositivo do tipo "travesseiro" em Configuracoes e copie o
 *    token (ele aparece UMA vez).
 * 2. Copie secrets.example.h para secrets.h e preencha WIFI_SSID,
 *    WIFI_PASSWORD e DEVICE_TOKEN.
 * 3. Grave, abra o Monitor Serial em 115200 e acompanhe.
 * 4. Abra o painel. Cada linha do Serial vira um ponto no grafico.
 *
 * O painel mostra as 20 leituras mais recentes. Com INTERVALO_MS em 10 s,
 * isso e uma janela de pouco mais de 3 minutos.
 */

#include <WiFi.h>
#include <HTTPClient.h>
#include <WiFiClientSecure.h>
#include <Adafruit_MPU6050.h>
#include <Adafruit_Sensor.h>
#include <Wire.h>
#include <math.h>

// Credenciais e token. Arquivo NAO versionado: copie secrets.example.h para
// secrets.h e preencha. Build falhar por ausencia dele e intencional.
#include "secrets.h"

// --- Parametros ---------------------------------------------------------

const char *URL_API = "https://dormio-smart.vercel.app/api/data";

// Intervalo entre envios. 10 s enche a janela de 20 pontos do painel em
// ~3,3 min. Para o protocolo de 3 blocos do VIA-01 (2 min cada), 15 s da uma
// janela de 5 min e cabe os tres.
const unsigned long INTERVALO_MS = 10000;

// Espera maxima pelo Wi-Fi. O sketch.ino de producao trava em `while` infinito
// se a rede nao subir (item HW-05); aqui isso viraria uma placa muda sem
// explicacao, entao desistimos e dizemos por que.
const unsigned long TIMEOUT_WIFI_MS = 20000;

// --- Criterio de movimento (docs/DATA-CONTRACT.md secao 2.2) ------------
// Quem classifica e o DISPOSITIVO. O painel exibe o rotulo, nunca recalcula.
const float GRAVIDADE = 9.81;
const float LIMIAR_MOVIMENTO = 1.2;
const char *STATUS_REPOUSO = "Repouso";
const char *STATUS_MOVIMENTO = "Movimento";

// Parado na Terra, |a| vale ~9,81 em qualquer pose. Fora desta faixa nao e
// medida: e sensor mudo.
//
// POR QUE ISTO E CRITICO AQUI, E NAO SO UM AVISO:
//
// Com os registradores zerados, |a| = 0 e a intensidade vira |0 - 9,81| =
// 9,81 - muito acima do limiar. O aparelho classificaria como MOVIMENTO e
// enviaria. E o backend ACEITARIA: o payload e internamente coerente
// (0 = raiz de 0+0+0) e zero esta dentro da faixa fisica declarada.
//
// Ou seja: um fio de alimentacao solto encheria o banco de eventos de
// movimento FABRICADOS, a noite inteira. Pior que silencio - silencio se
// percebe, dado inventado nao.
//
// O caso classico e VCC mal encaixado: o MPU6050 sobrevive do vazamento dos
// pull-ups do I2C, responde no barramento (entao mpu.begin() PASSA) e nao
// mede. Delator: a temperatura marca exatamente 36,5 C, que e o que a
// biblioteca produz com o registrador zerado (raw/340 + 36,53).
const float MAGNITUDE_MINIMA_PLAUSIVEL = 3.0;
const float MAGNITUDE_MAXIMA_PLAUSIVEL = 20.0;

Adafruit_MPU6050 mpu;

bool sensorOnline = false;
unsigned long enviadas = 0;
unsigned long falhas = 0;
// Para o diagnostico completo sair uma vez, e nao a cada ciclo.
bool avisouSensorMudo = false;

// --- Wi-Fi --------------------------------------------------------------

bool conectarWiFi() {
  if (WiFi.status() == WL_CONNECTED) return true;

  Serial.print("Conectando ao WiFi");
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  unsigned long inicio = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - inicio < TIMEOUT_WIFI_MS) {
    delay(500);
    Serial.print(".");
  }
  Serial.println();

  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("FALHA: Wi-Fi nao conectou. Confira SSID e senha em secrets.h.");
    Serial.println("       Redes de 5 GHz nao funcionam: o ESP32 so fala 2,4 GHz.");
    return false;
  }

  Serial.print("WiFi conectado. IP: ");
  Serial.println(WiFi.localIP());
  return true;
}

// --- Envio --------------------------------------------------------------

void enviar(const String &payload, float intensidade, const char *status) {
  WiFiClientSecure client;
  // Ignora a validacao do certificado do servidor. Ver a nota SEC-05 no
  // roadmap: para um teste de bancada serve, para o produto nao.
  client.setInsecure();

  HTTPClient http;
  http.begin(client, URL_API);
  http.addHeader("Content-Type", "application/json");
  // Autenticacao do dispositivo (SEC-02). Sem o header a API responde 401.
  http.addHeader("X-Device-Token", DEVICE_TOKEN);

  int codigo = http.POST(payload);

  Serial.printf("  intensidade=%.2f  %-9s  -> HTTP %d  ", intensidade, status, codigo);

  if (codigo == 201) {
    enviadas++;
    Serial.printf("OK (total: %lu)\n", enviadas);
  } else {
    falhas++;
    if (codigo == 401) {
      Serial.println("NAO AUTORIZADO");
      Serial.println("     DEVICE_TOKEN ausente, revogado ou de outro dispositivo.");
      Serial.println("     Pareie de novo em Configuracoes e atualize secrets.h.");
    } else if (codigo == 400) {
      Serial.println("RECUSADO PELA VALIDACAO");
      Serial.println("     " + http.getString());
    } else if (codigo == 503) {
      Serial.println("BANCO INDISPONIVEL (a leitura nao foi gravada)");
    } else if (codigo > 0) {
      Serial.println("RESPOSTA INESPERADA");
      Serial.println("     " + http.getString());
    } else {
      Serial.printf("FALHA DE CONEXAO (%d)\n", codigo);
    }
  }

  http.end();
}

// --- Setup --------------------------------------------------------------

void setup() {
  Serial.begin(115200);
  while (!Serial) delay(10);
  delay(500);

  Serial.println();
  Serial.println("=====================================================");
  Serial.println(" ENVIO CONTINUO - laco coleta -> API -> banco -> painel");
  Serial.println("=====================================================");

  Wire.begin(21, 22);
  if (!mpu.begin()) {
    Serial.println("ERRO: MPU6050 nao encontrado.");
    Serial.println("      Confira 3V3, GND, SDA=21, SCL=22.");
    Serial.println("      Sem sensor nao ha o que enviar; parando aqui.");
    while (1) delay(1000);
  }

  sensorOnline = true;
  mpu.setAccelerometerRange(MPU6050_RANGE_8_G);
  mpu.setGyroRange(MPU6050_RANGE_500_DEG);
  mpu.setFilterBandwidth(MPU6050_BAND_21_HZ);  // ver nota FW-06 no cabecalho
  Serial.println("MPU6050: online (+-8 g, +-500 deg/s, filtro 21 Hz)");

  conectarWiFi();

  Serial.printf("Enviando a cada %lu s. Ctrl+C ou tirar da tomada para parar.\n",
                INTERVALO_MS / 1000);
  Serial.println("-----------------------------------------------------");
}

// --- Loop ---------------------------------------------------------------

void loop() {
  static unsigned long ultimoEnvio = 0;

  if (millis() - ultimoEnvio < INTERVALO_MS && ultimoEnvio != 0) {
    delay(50);
    return;
  }
  ultimoEnvio = millis();

  sensors_event_t a, g, temp;
  mpu.getEvent(&a, &g, &temp);

  // Magnitude COM a gravidade: ~9,81 em repouso, nao zero.
  // Contrato secao 2.1.
  float total = sqrt(a.acceleration.x * a.acceleration.x +
                     a.acceleration.y * a.acceleration.y +
                     a.acceleration.z * a.acceleration.z);

  float intensidade = fabs(total - GRAVIDADE);
  const char *status = (intensidade > LIMIAR_MOVIMENTO) ? STATUS_MOVIMENTO : STATUS_REPOUSO;

  Serial.printf("[%lu] ax=%6.2f ay=%6.2f az=%6.2f |a|=%6.2f %.1fC\n",
                enviadas + falhas + 1,
                a.acceleration.x, a.acceleration.y, a.acceleration.z,
                total, temp.temperature);

  // Nao envia leitura impossivel. Ver a nota nas constantes do topo.
  if (total < MAGNITUDE_MINIMA_PLAUSIVEL || total > MAGNITUDE_MAXIMA_PLAUSIVEL) {
    falhas++;
    Serial.printf("  |a| = %.2f e fisicamente impossivel - NAO ENVIADO
", total);
    if (!avisouSensorMudo) {
      avisouSensorMudo = true;
      Serial.println();
      Serial.println("  ====================================================");
      Serial.println("  O sensor responde no I2C mas nao esta medindo.");
      Serial.printf("  Temperatura em %.1f C. Se for 36,5, e o valor que a
",
                    temp.temperature);
      Serial.println("  biblioteca produz com o registrador ZERADO.");
      Serial.println();
      Serial.println("  CONFIRA, nesta ordem:");
      Serial.println("    1. 3V3 do ESP32 -> VCC do MPU6050  (o suspeito numero um)");
      Serial.println("    2. GND -> GND");
      Serial.println("    3. GPIO21 -> SDA   e   GPIO22 -> SCL");
      Serial.println();
      Serial.println("  Nada sera enviado enquanto isso. Reencaixe os jumpers:");
      Serial.println("  a coleta volta sozinha, sem precisar gravar de novo.");
      Serial.println("  ====================================================");
      Serial.println();
    }
    return;
  }

  if (avisouSensorMudo) {
    avisouSensorMudo = false;
    Serial.println("  sensor voltou a medir - retomando o envio");
  }

  // Duas casas decimais, como o contrato descreve. A tolerancia de coerencia
  // do backend e 0,5 m/s2, entao o arredondamento nao chega perto de
  // incomodar.
  String payload = "{";
  payload += "\"ax\":" + String(a.acceleration.x, 2) + ",";
  payload += "\"ay\":" + String(a.acceleration.y, 2) + ",";
  payload += "\"az\":" + String(a.acceleration.z, 2) + ",";
  payload += "\"gx\":" + String(g.gyro.x, 2) + ",";
  payload += "\"gy\":" + String(g.gyro.y, 2) + ",";
  payload += "\"gz\":" + String(g.gyro.z, 2) + ",";
  payload += "\"t\":" + String(temp.temperature, 1) + ",";
  payload += "\"total\":" + String(total, 2) + ",";
  payload += "\"status\":\"" + String(status) + "\"";
  payload += "}";

  if (!conectarWiFi()) {
    falhas++;
    Serial.println("  sem rede; leitura descartada");
    return;
  }

  enviar(payload, intensidade, status);
}
