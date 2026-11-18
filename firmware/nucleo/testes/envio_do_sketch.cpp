// envio_do_sketch.cpp -- o envio REAL do sketch.ino contra um servidor falso (FW-14).
//
// ── POR QUE EXISTE ─────────────────────────────────────────────────────
//
// A fila, o lote e a resposta do servidor estao no nucleo e sao testados la
// (`testes_c2`, `testes_fila_flash`). Mas quem abre a conexao, monta a volta
// e decide quando parar e `enviar_pendentes()`, no sketch -- e ate 17/11 ele
// nao tinha teste nenhum. O FW-14 mudou justamente isso: uma conexao TLS
// para a volta inteira, em vez de uma por lote. Aqui o sketch, incluido nesta
// unidade, conversa com:
//
//   - uma particao `dormio` de mentira, em RAM, com a fila de verdade em cima;
//   - um `WiFiClientSecure` que so sabe se esta conectado; o servidor conta
//     um handshake cada vez que um POST encontra a conexao fechada;
//   - um `HTTPClient` que imita o do core do ESP32 no que importa: com
//     `setReuse(true)`, `end()` deixa a conexao aberta; sem, fecha.
//
// O servidor responde `aceitas` para todas as leituras, e o teste pode mandar
// ele fechar a conexao depois de cada resposta ou falhar um POST.
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <esp_partition.h>
#include <esp_sleep.h>
#include <esp_timer.h>
#include <freertos/FreeRTOS.h>
#include <freertos/task.h>
#include <HTTPClient.h>
#include <WiFiClientSecure.h>

int64_t esp_timer_get_time() { return 0; }
int esp_sleep_enable_timer_wakeup(uint64_t) { return 0; }
int esp_light_sleep_start() { return 0; }
void vTaskDelay(const TickType_t) {}
// FW-14, etapa 2: o `loop()` tem de apagar a propria tarefa.
static int tarefas_apagadas = 0;
static bool apagou_a_propria = false;
void vTaskDelete(TaskHandle_t t) {
  tarefas_apagadas++;
  apagou_a_propria = (t == 0);
}

// ── A particao `dormio`, em RAM ─────────────────────────────────────────
static const uint32_t TAMANHO_DA_PARTICAO = 0x200000;
static uint8_t *flash = 0;
static esp_partition_t particao;
const esp_partition_t *esp_partition_find_first(esp_partition_type_t, esp_partition_subtype_t,
                                                const char *) {
  particao.size = TAMANHO_DA_PARTICAO;
  return &particao;
}
esp_err_t esp_partition_read(const esp_partition_t *, size_t a, void *d, size_t n) {
  memcpy(d, flash + a, n);
  return ESP_OK;
}
esp_err_t esp_partition_write(const esp_partition_t *, size_t a, const void *o, size_t n) {
  const uint8_t *b = static_cast<const uint8_t *>(o);
  for (size_t i = 0; i < n; i++) flash[a + i] &= b[i];  // NOR: so derruba bits
  return ESP_OK;
}
esp_err_t esp_partition_erase_range(const esp_partition_t *, size_t a, size_t n) {
  memset(flash + a, 0xFF, n);
  return ESP_OK;
}

// ── O servidor falso ─────────────────────────────────────────────────────
static int handshakes = 0;
static int fechar_depois_de_cada = 0;  // 1 = o servidor nao mantem a conexao
static int falhar_o_post = 0;          // n > 0: o n-esimo POST falha (-1)
static char resposta[1024];

void wcs_stop(bool *conectado) { *conectado = false; }

// HW-10: um ADC falso. Guarda o pino lido e quantos POSTs ja tinham saido
// quando o sketch leu a bateria pela primeira vez na volta.
static uint32_t adc_falso_mv = 0;
static int pino_lido = -1;
static int posts_na_primeira_leitura = -1;
static int posts = 0;
uint32_t analogReadMilliVolts(uint8_t pino) {
  pino_lido = pino;
  if (posts_na_primeira_leitura < 0) posts_na_primeira_leitura = posts;
  return adc_falso_mv;
}

int http_post(bool *conectado, const uint8_t *corpo, size_t n) {
  posts++;
  if (!*conectado) {
    handshakes++;
    *conectado = true;
  }
  if (falhar_o_post == posts) {
    *conectado = false;  // a conexao caiu no meio
    resposta[0] = '\0';
    return -1;
  }
  // Uma leitura por "total" no envelope: o servidor aceita todas.
  int leituras = 0;
  const char *p = reinterpret_cast<const char *>(corpo);
  const char *fim = p + n;
  for (; p < fim; p++) {
    if (fim - p > 8 && strncmp(p, "\"total\":", 8) == 0) leituras++;
  }
  int k = snprintf(resposta, sizeof(resposta), "{\"aceitas\":[");
  for (int i = 0; i < leituras; i++) {
    k += snprintf(resposta + k, sizeof(resposta) - k, i ? ",%d" : "%d", i);
  }
  snprintf(resposta + k, sizeof(resposta) - k, "],\"pendentes\":[],\"rejeitadas\":[]}");
  if (fechar_depois_de_cada) *conectado = false;
  return 200;
}
const char *http_corpo() { return resposta; }

#include SKETCH

static int falhas = 0;
static void conferir(bool ok, const char *msg) {
  printf("  %s %s\n", ok ? "ok   " : "FALHA", msg);
  if (!ok) falhas++;
}

static InstanteDaEpoca no_mono(uint32_t s) {
  InstanteDaEpoca i;
  i.e_parede = false;
  i.segundos = s;
  return i;
}

static Epoca fabricar(uint32_t indice) {
  Epoca e;
  e.indice = indice;
  e.pico_total = 9.85f;
  e.pico_ax = 0;
  e.pico_ay = 0;
  e.pico_az = 9.85f;
  e.temp_pico = 25.0f;
  e.amostras = 1500;
  e.esperadas = 1500;
  e.duracao_s = DURACAO_EPOCA_BASE_S;
  e.nivel = 0;
  e.flags = 0;
  return e;
}

static uint32_t proxima = 0;
static void guardar(uint32_t n) {
  for (uint32_t i = 0; i < n; i++, proxima++) fila.guardar(fabricar(proxima), 0, no_mono(proxima * 30u));
}

static void zerar() {
  posts = 0;
  handshakes = 0;
  fechar_depois_de_cada = 0;
  falhar_o_post = 0;
}

int main() {
  flash = static_cast<uint8_t *>(malloc(TAMANHO_DA_PARTICAO));
  memset(flash, 0xFF, TAMANHO_DA_PARTICAO);
  mutex_fila = xSemaphoreCreateMutex();
  mutex_parede = xSemaphoreCreateMutex();
  json_do_lote = static_cast<char *>(malloc(TAMANHO_JSON_DO_LOTE));
  fila_ok = midia.abrir() && fila.montar();
  conferir(fila_ok, "a fila monta na particao de mentira");

  printf("FW-14: uma conexao TLS para a volta inteira\n");
  guardar(50);
  zerar();
  bool ok = enviar_pendentes();
  conferir(ok && fila.pendentes() == 0, "50 epocas, a volta termina e a fila esvazia");
  conferir(posts == 3, "em 3 lotes (20 + 20 + 10)");
  char msg[160];
  snprintf(msg, sizeof(msg), "um handshake so para os 3 lotes (foram %d)", handshakes);
  conferir(handshakes == 1, msg);
  conferir(contadores.lotes.load() == 3 && contadores.conexoes_tls.load() == 1,
           "o log conta 3 lotes e 1 conexao");
  conferir(contadores.maior_lote.load() > 0 && contadores.maior_lote.load() <= TAMANHO_JSON_DO_LOTE,
           "o maior lote e medido, e cabe no buffer");

  printf("o servidor nao mantem a conexao\n");
  guardar(50);
  zerar();
  fechar_depois_de_cada = 1;
  ok = enviar_pendentes();
  conferir(ok && fila.pendentes() == 0, "a volta termina do mesmo jeito, sem perder epoca");
  snprintf(msg, sizeof(msg), "cada lote reconecta sozinho (%d handshakes para %d lotes)", handshakes, posts);
  conferir(handshakes == 3 && posts == 3, msg);

  printf("o POST falha no meio da volta\n");
  guardar(50);
  zerar();
  falhar_o_post = 2;
  ok = enviar_pendentes();
  conferir(!ok, "a volta termina em falha (a politica de reconexao recua)");
  conferir(posts == 2, "e para no lote que falhou, sem insistir");
  conferir(fila.pendentes() == 30, "o lote que falhou volta para a fila: 30 pendentes");
  zerar();
  ok = enviar_pendentes();
  conferir(ok && fila.pendentes() == 0 && handshakes == 1,
           "a volta seguinte abre uma conexao nova e manda o resto");

  printf("FW-14, etapa 2: memoria que o sketch nao segura a toa\n");
  loop();
  conferir(tarefas_apagadas == 1 && apagou_a_propria,
           "o loop() apaga a propria tarefa (a pilha de 8 KB volta ao heap)");
  printf("HW-10: a bateria no envio\n");
  adc_falso_mv = 1640;
  conferir(medir_bateria_mv() == 3280 && pino_lido == 35,
           "16 amostras do GPIO35, vezes o divisor: 3 280 mV");
  guardar(30);
  zerar();
  posts_na_primeira_leitura = -1;
  adc_falso_mv = 1610;
  enviar_pendentes();
  conferir(bateria_no_envio_mv == 3220, "a leitura sob carga sai na volta: 3 220 mV");
  conferir(posts_na_primeira_leitura == 1,
           "e e feita logo depois do primeiro POST, com o radio ligado");

  conferir(TAMANHO_JSON_DO_LOTE == tamanho_do_lote(LEITURAS_POR_LOTE_NO_ESP32),
           "o buffer do lote e o do pior caso de 20 leituras, nao uma estimativa");

  printf("%d falhas\n", falhas);
  return falhas == 0 ? 0 : 1;
}
