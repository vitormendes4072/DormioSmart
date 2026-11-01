// sketch.ino -- o firmware de produto do Dormio, na arquitetura C2 (FW-07 b).
//
// ── O QUE MUDOU ────────────────────────────────────────────────────────
//
// Ate 31/10 este sketch tirava UMA amostra por boot e voltava ao Deep Sleep:
// nao registraria uma noite nem com rede perfeita. A arquitetura decidida no
// ARQ-01 (C2, `docs/DECISAO-ARQ-01-CADENCIA.md`) e outra: o MPU6050 amostra a
// 50 Hz sozinho, guardando na propria FIFO, e o ESP32 acorda do SONO LEVE a
// cada ~1,7 s para esvazia-la. Toda a logica disso mora no nucleo
// (`nucleo/`), testada no host; este arquivo so liga as pecas ao hardware.
//
//   FIFO do MPU --(I2C)--> CadeiaC2 --> grade de 960 pontos por epoca
//        |                                  |
//        |                    features (AcumuladorDeFeatures) + Epoca
//        |                                  |
//        +---- a cada 10 min ----  FilaNaFlash (particao `dormio`)
//                                           |
//                         POST /api/data/lote, confirma o prefixo aceito
//
// ── DUAS TAREFAS, UMA EM CADA NUCLEO ───────────────────────────────────
//
// A FIFO guarda 3,4 s e e esvaziada a cada 1,7 s. Um POST por HTTPS leva de 1
// a 3 s. No mesmo laco, o envio faria a FIFO transbordar e a epoca seria
// recusada. Por isso:
//
//   - `tarefa_de_medicao` (nucleo 1, prioridade alta) so esvazia a FIFO,
//     fecha epocas e grava na fila. Entre drenagens dorme em sono leve --
//     a menos que o Wi-Fi esteja ligado, porque o sono leve derruba a
//     conexao; ai espera acordada, mas no mesmo ritmo.
//   - `tarefa_de_envio` (nucleo 0) dorme ate a medicao avisar que e hora,
//     liga o Wi-Fi, acerta o relogio por NTP, envia lotes e desliga.
//
// A fila e a resolucao do relogio sao compartilhadas, cada uma atras de um
// mutex.
//
// ⚠️ NAO EXERCITADO NA PLACA. Este arquivo so passa pelo `make sintaxe` (com
// stubs). Nao se sabe ainda se o I2C le a FIFO como o nucleo espera, se o
// sono leve acorda no tempo certo, nem quanto tempo a montagem da fila leva
// no boot. E a parte (c) do FW-07, junto com o FW-05, e precisa da solda.
//
// ⚠️ O Wokwi pode nao simular a FIFO do MPU6050 (a documentacao dele nao
// diz). O `envio-continuo` continua sendo o sketch que roda no simulador.

#include <HTTPClient.h>
#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <Wire.h>
#include <esp_sleep.h>
#include <esp_timer.h>
#include <freertos/FreeRTOS.h>
#include <freertos/semphr.h>
#include <freertos/task.h>
#include <sys/time.h>
#include <time.h>

#include "midia_flash_esp32.h"
#include "nucleo/cadeia_c2.h"
#include "nucleo/caracteristicas.h"
#include "nucleo/envio_da_fila.h"
#include "nucleo/epoca_c2.h"
#include "nucleo/fifo_mpu.h"
#include "nucleo/fila_flash.h"
#include "nucleo/reamostragem.h"
#include "nucleo/radio.h"
#include "nucleo/reconexao.h"
#include "nucleo/relogio.h"

// Credenciais e token do dispositivo. Arquivo NAO versionado: copie
// secrets.example.h para secrets.h e preencha. O build falhar por ausencia
// dele e intencional -- melhor nao compilar do que hardcodar segredo.
#include "secrets.h"

using namespace dormio;

// ── Configuracao ───────────────────────────────────────────────────────

static const char *URL_LOTE = "https://dormio-smart.vercel.app/api/data/lote";

static const int PINO_SDA = 21;
static const int PINO_SCL = 22;
static const uint8_t ENDERECO_MPU = 0x68;

// Registradores de energia do MPU6050. Fora de `fifo_mpu.h` porque so o
// sketch os toca: reset, relogio interno, giroscopio em espera (a C2 nao usa
// o giro, e ele e a maior parte do consumo do sensor).
static const uint8_t MPU_REG_PWR_MGMT_1 = 0x6B;
static const uint8_t MPU_REG_PWR_MGMT_2 = 0x6C;
static const uint8_t PWR1_RESET = 0x80;
static const uint8_t PWR1_RELOGIO_INTERNO = 0x00;
static const uint8_t PWR2_GIRO_EM_ESPERA = 0x07;

// O buffer do `Wire` no ESP32 tem 128 B; 120 sao 20 amostras inteiras.
static const uint16_t BLOCO_I2C_BYTES = 120;

// A cada quanto tempo a medicao acorda a tarefa de envio: ~20 epocas, um
// lote. Mais curto gasta radio a toa; mais longo deixa o painel atrasado.
static const uint64_t INTERVALO_DE_ENVIO_US = 10ull * 60ull * 1000000ull;

static const uint32_t TIMEOUT_WIFI_MS = 20000;
static const uint32_t TIMEOUT_NTP_MS = 5000;
static const uint16_t TIMEOUT_POST_MS = 8000;
// Teto de lotes por volta de envio: uma noite inteira acumulada sao ~16
// lotes, e o Wi-Fi ligado impede o sono leve da medicao.
static const uint32_t LOTES_POR_VOLTA = 20;

// ── Estado compartilhado ───────────────────────────────────────────────
//
// Estatico, nao heap: firmware que fragmenta memoria a noite inteira falha
// no pior momento. Os grandes (~90 KB juntos) ficam aqui e nao na pilha das
// tarefas.

static MidiaFlashEsp32 midia;
static FilaNaFlash fila(&midia);
static bool fila_ok = false;
static SemaphoreHandle_t mutex_fila;

static ResolucaoDeParede parede;
static SemaphoreHandle_t mutex_parede;

// Quem pode usar o radio (FW-09): a medicao o reserva ANTES de avisar o
// envio, e o envio o devolve. Ver `nucleo/radio.h`.
static CoordenacaoDoRadio radio;
static TaskHandle_t tarefa_envio = 0;

static CadeiaC2 cadeia;
static AcumuladorDeFeatures acumulador;
static float grade_x[AMOSTRAS_NA_GRADE], grade_y[AMOSTRAS_NA_GRADE], grade_z[AMOSTRAS_NA_GRADE];
static uint64_t origem_us = 0;

static RegistroDeEpoca rascunho[MAX_LEITURAS_POR_LOTE];
static char json_do_lote[MAX_LEITURAS_POR_LOTE * 520];

struct Contadores {
  uint32_t epocas_gravadas;
  uint32_t sem_features;
  uint32_t recusadas;
  uint32_t transbordos;
  uint32_t falhas_na_fila;
  uint32_t descartadas_no_envio;
};
static Contadores contadores = {0, 0, 0, 0, 0, 0};

static ResolucaoDeParede copia_da_parede() {
  xSemaphoreTake(mutex_parede, portMAX_DELAY);
  const ResolucaoDeParede p = parede;
  xSemaphoreGive(mutex_parede);
  return p;
}

static uint64_t agora_ms() { return static_cast<uint64_t>(esp_timer_get_time()) / 1000ull; }

// ── I2C ────────────────────────────────────────────────────────────────

static bool escrever_registrador(uint8_t reg, uint8_t valor) {
  Wire.beginTransmission(ENDERECO_MPU);
  Wire.write(reg);
  Wire.write(valor);
  return Wire.endTransmission() == 0;
}

static bool ler_registradores(uint8_t reg, uint8_t *destino, uint16_t n) {
  Wire.beginTransmission(ENDERECO_MPU);
  Wire.write(reg);
  if (Wire.endTransmission(false) != 0) return false;
  if (Wire.requestFrom(ENDERECO_MPU, static_cast<size_t>(n)) != n) return false;
  for (uint16_t i = 0; i < n; i++) destino[i] = static_cast<uint8_t>(Wire.read());
  return true;
}

// Os registradores da C2 (`fifo_mpu.h`), na ordem que a folha pede: acordar,
// configurar taxa e filtro, e so entao zerar e ligar a FIFO.
static bool configurar_mpu() {
  if (!escrever_registrador(MPU_REG_PWR_MGMT_1, PWR1_RESET)) return false;
  delay(100);
  bool ok = escrever_registrador(MPU_REG_PWR_MGMT_1, PWR1_RELOGIO_INTERNO);
  ok = ok && escrever_registrador(MPU_REG_PWR_MGMT_2, PWR2_GIRO_EM_ESPERA);
  ok = ok && escrever_registrador(MPU_REG_SMPLRT_DIV, C2_SMPLRT_DIV);
  ok = ok && escrever_registrador(MPU_REG_CONFIG, C2_DLPF_CFG);
  ok = ok && escrever_registrador(MPU_REG_ACCEL_CONFIG, C2_ACCEL_CONFIG);
  ok = ok && escrever_registrador(MPU_REG_USER_CTRL, MPU_USER_CTRL_FIFO_RESET);
  ok = ok && escrever_registrador(MPU_REG_USER_CTRL, MPU_USER_CTRL_FIFO_EN);
  ok = ok && escrever_registrador(MPU_REG_FIFO_EN, C2_FIFO_EN);
  return ok;
}

static void resetar_fifo() {
  escrever_registrador(MPU_REG_USER_CTRL, MPU_USER_CTRL_FIFO_RESET | MPU_USER_CTRL_FIFO_EN);
}

static float ler_temperatura_c() {
  uint8_t b[2];
  if (!ler_registradores(MPU_REG_TEMP_OUT_H, b, 2)) return 0.0f;
  return temperatura_mpu_c(static_cast<int16_t>((b[0] << 8) | b[1]));
}

// Uma drenagem. O instante e o da leitura de FIFO_COUNT: e com ele que a
// contagem acumulada entra na regressao da linha do tempo (`cadeia_c2.h`).
// So os bytes contados sao lidos -- uma amostra que chegue durante a leitura
// fica para a proxima drenagem, e a contagem continua dizendo a verdade.
static void drenar() {
  static uint8_t bytes[FIFO_CAPACIDADE_AMOSTRAS * BYTES_POR_AMOSTRA];
  static AmostraBruta amostras[FIFO_CAPACIDADE_AMOSTRAS];

  uint8_t estado = 0;
  uint8_t contagem[2] = {0, 0};
  const uint64_t t_us = static_cast<uint64_t>(esp_timer_get_time());
  if (!ler_registradores(MPU_REG_INT_STATUS, &estado, 1) ||
      !ler_registradores(MPU_REG_FIFO_COUNTH, contagem, 2)) {
    cadeia.registrar_drenagem(t_us, 0, 0, true);
    contadores.transbordos++;
    return;
  }
  const uint16_t n_fifo = static_cast<uint16_t>((contagem[0] << 8) | contagem[1]);
  if (avaliar_fifo(n_fifo, estado) != LEITURA_OK) {
    resetar_fifo();
    cadeia.registrar_drenagem(t_us, 0, 0, true);
    contadores.transbordos++;
    return;
  }

  const uint16_t a_ler = bytes_para_ler(n_fifo, sizeof(bytes));
  uint16_t lidos = 0;
  while (lidos < a_ler) {
    uint16_t bloco = static_cast<uint16_t>(a_ler - lidos);
    if (bloco > BLOCO_I2C_BYTES) bloco = BLOCO_I2C_BYTES;
    if (!ler_registradores(MPU_REG_FIFO_R_W, bytes + lidos, bloco)) {
      // Leitura pela metade: o fluxo perdeu o alinhamento com a contagem.
      resetar_fifo();
      cadeia.registrar_drenagem(t_us, 0, 0, true);
      contadores.transbordos++;
      return;
    }
    lidos = static_cast<uint16_t>(lidos + bloco);
  }
  const uint16_t n = decodificar_fifo(bytes, lidos, amostras, FIFO_CAPACIDADE_AMOSTRAS);
  cadeia.registrar_drenagem(t_us, amostras, n, false);
}

// Fecha todas as epocas que a cadeia ja consegue fechar e grava cada uma.
static void fechar_epocas() {
  for (;;) {
    EpocaReamostrada info;
    const ResultadoDaEpoca r = cadeia.proxima_epoca(&info, grade_x, grade_y, grade_z);
    if (r == EPOCA_AINDA_NAO) return;
    if (r != EPOCA_PRONTA) {
      // Recusada (transbordo, taxa, poucas drenagens): nao e gravada. No
      // servidor ela aparece como intervalo entre dois `ts`, que e o que ela
      // e -- uma lacuna, e nao uma medida inventada.
      contadores.recusadas++;
      Serial.printf("[epoca %u] recusada (motivo %d)\n", static_cast<unsigned>(info.indice),
                    static_cast<int>(r));
      continue;
    }

    acumulador.iniciar();
    for (uint32_t i = 0; i < AMOSTRAS_NA_GRADE; i++) {
      acumulador.amostrar(grade_x[i], grade_y[i], grade_z[i]);
    }
    FeaturesDeEpoca f;
    const bool tem_features = acumulador.fechar(TAXA_DA_GRADE_HZ, &f);
    VetorDeFeatures v;
    if (tem_features) v = quantizar(f);

    const Epoca e = epoca_da_grade(info.indice, grade_x, grade_y, grade_z, AMOSTRAS_NA_GRADE,
                                   ler_temperatura_c());
    const InstanteDaEpoca instante =
        instante_para_gravar(copia_da_parede(), inicio_da_epoca_c2_ms(origem_us, info.indice));

    ResultadoDaGuarda g = FILA_NAO_MONTADA;
    if (fila_ok) {
      xSemaphoreTake(mutex_fila, portMAX_DELAY);
      g = fila.guardar(e, tem_features ? &v : 0, instante);
      xSemaphoreGive(mutex_fila);
    }
    if (g == GUARDADO) {
      contadores.epocas_gravadas++;
      if (!tem_features) contadores.sem_features++;
    } else {
      contadores.falhas_na_fila++;
    }
    Serial.printf("[epoca %u] total %.2f m/s2, taxa %.2f Hz, %s, fila: %d\n",
                  static_cast<unsigned>(info.indice), static_cast<double>(e.pico_total),
                  1.0 / info.linha.b_s, tem_features ? "com f" : "SEM f", static_cast<int>(g));
  }
}

// ── Tarefa de medicao (nucleo 1) ───────────────────────────────────────

static void tarefa_de_medicao(void *) {
  uint32_t xorshift = 0x9E3779B9u;
  uint64_t proximo_envio_us = static_cast<uint64_t>(esp_timer_get_time()) + INTERVALO_DE_ENVIO_US;

  for (;;) {
    const uint32_t intervalo_us = intervalo_de_drenagem_us(&xorshift);
    // Sono leve so com o Wi-Fi desligado: ele derrubaria a conexao. Com o
    // Wi-Fi ligado, espera acordada -- no mesmo ritmo, e e isso que impede a
    // FIFO de transbordar enquanto o POST esta no ar.
    if (!radio.pode_dormir()) {
      vTaskDelay(pdMS_TO_TICKS(intervalo_us / 1000u));
    } else {
      esp_sleep_enable_timer_wakeup(intervalo_us);
      esp_light_sleep_start();
    }

    drenar();
    fechar_epocas();

    const uint64_t agora_us = static_cast<uint64_t>(esp_timer_get_time());
    // Reservar o radio ANTES do aviso (FW-09): ate 01/11 a flag era ligada
    // pela tarefa de envio depois de acordar, e na janela a medicao entrava
    // em sono leve com o Wi-Fi subindo.
    if (agora_us >= proximo_envio_us && tarefa_envio != 0 && radio.pedir_envio()) {
      proximo_envio_us = agora_us + INTERVALO_DE_ENVIO_US;
      xTaskNotifyGive(tarefa_envio);
    }
  }
}

// ── Tarefa de envio (nucleo 0) ─────────────────────────────────────────

static bool conectar_wifi() {
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  const uint64_t inicio = agora_ms();
  while (WiFi.status() != WL_CONNECTED && agora_ms() - inicio < TIMEOUT_WIFI_MS) {
    vTaskDelay(pdMS_TO_TICKS(250));
  }
  return WiFi.status() == WL_CONNECTED;
}

static void desligar_wifi() {
  WiFi.disconnect(true);
  WiFi.mode(WIFI_OFF);
}

// NTP a cada volta: o relogio interno anda no sono leve, mas deriva, e e a
// sincronia que permite gravar hora de parede nas epocas seguintes.
static void sincronizar_relogio() {
  configTime(0, 0, "pool.ntp.org", "time.nist.gov");  // UTC; o backend guarda UTC
  const uint64_t inicio = agora_ms();
  while (agora_ms() - inicio < TIMEOUT_NTP_MS) {
    struct timeval tv;
    gettimeofday(&tv, 0);
    if (tv.tv_sec > 1700000000) {  // depois de 2023: o NTP respondeu
      const int64_t unix_ms = static_cast<int64_t>(tv.tv_sec) * 1000 + tv.tv_usec / 1000;
      xSemaphoreTake(mutex_parede, portMAX_DELAY);
      parede.sincronizar(agora_ms(), unix_ms);
      xSemaphoreGive(mutex_parede);
      return;
    }
    vTaskDelay(pdMS_TO_TICKS(200));
  }
  Serial.println("NTP nao respondeu: as epocas seguem com o relogio monotonico.");
}

// Envia ate `LOTES_POR_VOLTA` lotes. Devolve false se a volta terminou em
// falha (para a politica de reconexao recuar).
static bool enviar_pendentes() {
  uint32_t max_no_lote = MAX_LEITURAS_POR_LOTE;
  for (uint32_t volta = 0; volta < LOTES_POR_VOLTA; volta++) {
    const ResolucaoDeParede p = copia_da_parede();
    xSemaphoreTake(mutex_fila, portMAX_DELAY);
    const PreparoDoLote preparo =
        preparar_lote(&fila, p, rascunho, max_no_lote, json_do_lote, sizeof(json_do_lote));
    xSemaphoreGive(mutex_fila);
    contadores.descartadas_no_envio += preparo.descartados;
    if (preparo.no_lote == 0) {
      if (preparo.descartados > 0) continue;  // a frente saiu; o resto pode ir
      return true;                            // fila vazia
    }

    WiFiClientSecure cliente;
    cliente.setInsecure();  // mesmo regime dos outros sketches; ver SEC-* no backlog
    HTTPClient http;
    http.setTimeout(TIMEOUT_POST_MS);
    http.begin(cliente, URL_LOTE);
    http.addHeader("Content-Type", "application/json");
    http.addHeader("X-Device-Token", DEVICE_TOKEN);
    const int status = http.POST(reinterpret_cast<uint8_t *>(json_do_lote), preparo.tamanho);
    const String corpo = http.getString();
    http.end();

    xSemaphoreTake(mutex_fila, portMAX_DELAY);
    const DecisaoDoLote d = aplicar_resposta(&fila, status, corpo.c_str(),
                                             static_cast<uint32_t>(strlen(corpo.c_str())),
                                             preparo.no_lote);
    xSemaphoreGive(mutex_fila);
    Serial.printf("[lote] HTTP %d: %u aceitas, %u rejeitadas, %u pendentes\n", status,
                  static_cast<unsigned>(d.aceitas), static_cast<unsigned>(d.rejeitadas),
                  static_cast<unsigned>(d.pendentes));

    if (d.acao == LOTE_DIVIDIR) {
      max_no_lote = max_no_lote > 1 ? max_no_lote / 2 : 1;
      continue;
    }
    if (d.acao == LOTE_RECUAR || d.recuar_depois) return false;
  }
  return true;
}

static void tarefa_de_envio(void *) {
  PoliticaDeReconexao reconexao(0xD0A10u);
  reconexao.iniciar(agora_ms());
  for (;;) {
    ulTaskNotifyTake(pdTRUE, portMAX_DELAY);
    // A medicao ja reservou o radio ao avisar. Desistir sem devolve-lo
    // deixaria a medicao acordada para sempre (FW-09).
    if (!fila_ok || !reconexao.deve_tentar(agora_ms())) {
      radio.liberar();
      continue;
    }

    bool ok = conectar_wifi();
    if (ok) {
      sincronizar_relogio();
      ok = enviar_pendentes();
    } else {
      Serial.println("Wi-Fi nao subiu em 20 s (SSID, senha, ou rede de 5 GHz).");
    }
    desligar_wifi();
    radio.liberar();  // so depois de o radio estar desligado

    if (ok) {
      reconexao.registrar_sucesso(agora_ms());
      // O "conectado" da politica e da volta, nao do radio, que acabou de
      // desligar: a proxima volta pode tentar de imediato.
      reconexao.registrar_queda(agora_ms());
    } else {
      reconexao.registrar_falha(agora_ms());
    }
    Serial.printf("[envio] %s; gravadas %u, sem f %u, recusadas %u, transbordos %u, "
                  "falhas na fila %u, descartadas %u\n",
                  ok ? "ok" : "FALHOU", static_cast<unsigned>(contadores.epocas_gravadas),
                  static_cast<unsigned>(contadores.sem_features),
                  static_cast<unsigned>(contadores.recusadas),
                  static_cast<unsigned>(contadores.transbordos),
                  static_cast<unsigned>(contadores.falhas_na_fila),
                  static_cast<unsigned>(contadores.descartadas_no_envio));
  }
}

// ── setup / loop ───────────────────────────────────────────────────────

void setup() {
  Serial.begin(115200);
  Serial.println("\n=== Dormio -- captacao C2 ===");

  mutex_fila = xSemaphoreCreateMutex();
  mutex_parede = xSemaphoreCreateMutex();

  // Sem a particao, o sketch segue medindo e avisa: parar aqui perderia a
  // noite inteira por uma tabela gravada errado, e o log diz o que fazer.
  fila_ok = midia.abrir() && fila.montar();
  if (fila_ok) {
    Serial.printf("Fila na flash: %u pendentes, sessao %u, %u corrompidos na montagem.\n",
                  static_cast<unsigned>(fila.pendentes()), static_cast<unsigned>(fila.sessao()),
                  static_cast<unsigned>(fila.estatisticas().corrompidos_na_montagem));
  } else {
    Serial.println("ERRO: particao `dormio` nao encontrada. Grave com firmware/partitions.csv.");
    Serial.println("      Medindo assim mesmo, mas NADA sera guardado nem enviado.");
  }

  Wire.begin(PINO_SDA, PINO_SCL);
  Wire.setClock(400000);
  if (!configurar_mpu()) {
    Serial.println("ERRO: MPU6050 nao respondeu no I2C (0x68). Confira a solda e os fios.");
  }
  origem_us = static_cast<uint64_t>(esp_timer_get_time());
  cadeia.iniciar(origem_us);

  xTaskCreatePinnedToCore(tarefa_de_envio, "envio", 16384, 0, 1, &tarefa_envio, 0);
  xTaskCreatePinnedToCore(tarefa_de_medicao, "medicao", 8192, 0, 5, 0, 1);
}

// Todo o trabalho esta nas duas tarefas.
void loop() { vTaskDelay(portMAX_DELAY); }
