/*
 * envio-continuo.ino - fecha o laco coleta -> API -> banco -> dashboard
 *
 * INSTRUMENTO DE BANCADA, NAO FIRMWARE DE PRODUTO.
 * Nao dorme, nao usa botao, nao usa GPIO extra. Le o sensor e agrega em
 * epocas de 30 s, para sempre.
 *
 * -- POR QUE ELE EXISTE, SE JA HA O sketch.ino ---------------------------
 *
 * O sketch.ino envia UMA leitura e dorme esperando um sinal no GPIO 27. Isso
 * exige botao e resistor de pull-down de 10k, que a ligacao de bancada atual
 * (3V3, GND, SDA=21, SCL=22) nao tem. Com o pino flutuando, `digitalRead`
 * devolve ruido: ou reinicia sozinho, ou nunca acorda. Nao da para testar o
 * laco de dados com essa variavel solta no meio.
 *
 * Como o sketch.ino tambem nao faz amostragem periodica -- uma amostra por
 * boot, e so --, ele nao registraria uma noite nem com rede perfeita. Este e
 * o sketch que roda numa captacao de verdade ate o FW-07 sair.
 *
 * -- O QUE MUDOU EM 2026-09-22 (HW-05) -----------------------------------
 *
 * Ate esta data o laco era:
 *
 *     medir -> montar payload -> conectarWiFi() -> enviar
 *
 * com `conectarWiFi()` gastando ate 20 s em `delay(500)` DENTRO do laco de
 * amostragem, e a leitura sendo DESCARTADA quando a rede nao subia.
 *
 * Os dois problemas, na ordem de gravidade:
 *
 * 1. A CADENCIA COLAPSAVA. Com intervalo de 10 s e 20 s de bloqueio, cada
 *    ciclo passava a levar 20-30 s. A serie continuava saindo, com aparencia
 *    normal, e a base de tempo derivada. Para actigrafia -- cuja unidade E a
 *    epoca fixa de 30 s -- isso e pior que lacuna: a lacuna a analise ve, a
 *    deriva nao. Dado distorcido que parece valido e o modo de falha mais
 *    caro que existe aqui.
 *
 * 2. O dado era perdido. Grave, mas menos: perda declarada e perda visivel.
 *
 * Agora sao dois raciocinios independentes no mesmo laco. A MEDICAO nunca
 * espera por rede, por serial, nem por sensor. A REDE trabalha no tempo que
 * conseguir, e o que ela nao entrega fica no buffer de epocas.
 *
 * A logica toda vive em `firmware/nucleo/`, em C++ puro, com 341
 * verificacoes rodando no host (`cd firmware/nucleo && make`). Este arquivo
 * so liga o nucleo ao hardware.
 *
 * -- FILTRO EM 21 Hz -----------------------------------------------------
 *
 * Igual ao sketch de caracterizacao e, desde o FW-06, igual tambem ao
 * sketch.ino -- que ate entao nao chamava setFilterBandwidth e rodava no
 * padrao de 260 Hz. Movimento de corpo em cama e fenomeno de poucos Hz;
 * largura maior so deixa entrar vibracao de movel e ruido do MEMS. Os tres
 * sketches medindo na mesma banda e o que torna o resultado de um
 * transferivel para o outro.
 *
 * -- O QUE ESTE SKETCH NAO CORRIGE ---------------------------------------
 *
 * A medicao de 2026-08-24 mostrou este sensor marcando |a| = 9,20 m/s2
 * PARADO, e nao 9,81. Isso e vies de hardware, e a correcao depende da
 * caracterizacao de 6 posicoes (CALC-02). Aqui o dado vai CRU, de proposito:
 * o objetivo e testar o transporte, e mascarar o vies agora esconderia
 * justamente o que precisa ser medido depois.
 *
 * -- COMO USAR -----------------------------------------------------------
 *
 * 1. Pareie um dispositivo do tipo "travesseiro" em Configuracoes e copie o
 *    token (ele aparece UMA vez).
 * 2. Copie secrets.example.h para secrets.h e preencha WIFI_SSID,
 *    WIFI_PASSWORD e DEVICE_TOKEN.
 * 3. Grave, abra o Monitor Serial em 115200 e acompanhe.
 * 4. Abra o painel. Cada EPOCA de 30 s vira um ponto no grafico.
 *
 * Agora que o dado sai agregado, um ponto do painel = 30 s de medicao, nao
 * um instante. Uma noite de 8 h sao 960 pontos.
 */

#include <WiFi.h>
#include <HTTPClient.h>
#include <WiFiClientSecure.h>
#include <Adafruit_MPU6050.h>
#include <Adafruit_Sensor.h>
#include <Wire.h>
#include <math.h>
#include <time.h>

// Credenciais e token. Arquivo NAO versionado: copie secrets.example.h para
// secrets.h e preencha. Build falhar por ausencia dele e intencional.
#include "secrets.h"

// Nucleo em C++ puro. Zero Arduino, zero WiFi -- e por isso que ele roda no
// host com g++. Ver firmware/nucleo/README.md.
#include "../nucleo/buffer.h"
#include "../nucleo/cadencia.h"
#include "../nucleo/epoca.h"
#include "../nucleo/payload.h"
#include "../nucleo/reconexao.h"
#include "../nucleo/relogio.h"

using namespace dormio;

// --- Parametros ---------------------------------------------------------

static const char *URL_API = "https://dormio-smart.vercel.app/api/data";

// Intervalo entre AMOSTRAS. Com epoca de 30 s, 10 s da 3 amostras por epoca.
// Pouco para o FW-05 (que pede >= 42 Hz), suficiente para o que este sketch
// testa. Mudar aqui muda automaticamente o `esperadas` de cada epoca.
static const uint32_t INTERVALO_AMOSTRA_MS = 10000;

// Capacidade do buffer, em EPOCAS. 1024 epocas x 32 B = 32 KB.
//
// Nao e chute: `firmware/nucleo/capacidade.cpp` mede. 1024 epocas cobrem
// 8,53 h em resolucao CHEIA de 30 s -- uma noite inteira sem degradar uma vez
// sequer -- e 543 h se a degradacao entrar. Esta placa nao dorme neste
// sketch, entao nao ha razao para espremer no RTC.
static const uint32_t CAPACIDADE_EPOCAS = 1024;

// Quanto tempo um POST pode custar. Curto de proposito: a drenagem so comeca
// se houver esta folga ate o proximo tick de amostragem (ver `drenar`).
static const uint16_t ORCAMENTO_POST_MS = 4000;

// Teto de POSTs por volta do laco. Drenar 960 epocas de uma noite sao 960
// handshakes TLS; fazer isso de enfiada seguraria o laco por minutos. Em
// rajadas pequenas, a drenagem cede o passo para a medicao. O endpoint de
// lote (item API-03) e o que resolve isso de verdade.
static const uint8_t MAXIMO_POSTS_POR_VOLTA = 3;

// Reinicializacao do sensor quando ele nao responde. NAO trava o laco.
static const uint32_t RETENTATIVA_SENSOR_MS = 5000;

// --- Estado -------------------------------------------------------------

Adafruit_MPU6050 mpu;

static RelogioMonotonico relogio;
static ControleDeCadencia cadencia;
static AcumuladorDeEpoca acumulador;
static BufferDeEpocas<CAPACIDADE_EPOCAS> buffer;
static PoliticaDeReconexao rede;
static ResolucaoDeParede parede;

static bool sensor_online = false;
static uint64_t proxima_tentativa_sensor = 0;
static bool avisou_sensor_mudo = false;

static uint64_t tentativa_wifi_expira_em = 0;
static bool tentativa_wifi_em_curso = false;

static uint32_t enviadas = 0;
static uint32_t recusadas = 0;
static uint32_t falhas_de_envio = 0;
static uint32_t lacunas_puladas = 0;
static uint64_t proximo_relatorio = 0;

// --- Sensor -------------------------------------------------------------

// Tenta subir o MPU6050. NAO bloqueia: devolve o resultado e o laco tenta de
// novo mais tarde.
//
// Antes aqui havia `while (1) delay(1000);` -- o firmware parava para sempre
// se o sensor nao respondesse no boot. Um jumper mal encaixado no instante do
// boot custava a noite inteira, e o aparelho ficava mudo sem dizer por que.
// Agora ele segue vivo, avisa, e retoma sozinho quando o jumper voltar.
static bool tentar_iniciar_sensor() {
  if (!mpu.begin()) return false;
  mpu.setAccelerometerRange(MPU6050_RANGE_8_G);
  mpu.setGyroRange(MPU6050_RANGE_500_DEG);
  mpu.setFilterBandwidth(MPU6050_BAND_21_HZ);  // ver nota FW-06 no cabecalho
  return true;
}

static void explicar_sensor_mudo(float temperatura) {
  if (avisou_sensor_mudo) return;
  avisou_sensor_mudo = true;
  Serial.println();
  Serial.println("  ====================================================");
  Serial.println("  O sensor responde no I2C mas nao esta medindo.");
  Serial.printf("  Temperatura em %.1f C. Se for 36,5, e o valor que a\n", temperatura);
  Serial.println("  biblioteca produz com o registrador ZERADO.");
  Serial.println();
  Serial.println("  CONFIRA, nesta ordem:");
  Serial.println("    1. 3V3 do ESP32 -> VCC do MPU6050  (o suspeito numero um)");
  Serial.println("    2. GND -> GND");
  Serial.println("    3. GPIO21 -> SDA   e   GPIO22 -> SCL");
  Serial.println();
  Serial.println("  A amostragem CONTINUA: as epocas saem marcadas com amostra");
  Serial.println("  invalida, entao a noite nao vira silencio -- vira uma noite");
  Serial.println("  com o defeito registrado. Reencaixe os jumpers e a coleta");
  Serial.println("  volta sozinha, sem precisar gravar de novo.");
  Serial.println("  ====================================================");
  Serial.println();
}

// --- Buffer -------------------------------------------------------------

// Chamado pelo acumulador a cada epoca fechada.
static void ao_fechar_epoca(const Epoca &e, void * /*contexto*/) {
  bool ok = buffer.guardar(e);

  if (e.vazia()) {
    Serial.printf("[epoca %lu] LACUNA -- nenhuma amostra em %u s\n",
                  (unsigned long)e.indice, e.duracao_s);
  } else {
    Serial.printf("[epoca %lu] pico |a|=%.2f  %s  %u/%u amostras%s%s\n",
                  (unsigned long)e.indice, e.pico_total, classificar(e.pico_total),
                  e.amostras, e.esperadas,
                  e.incompleta() ? "  INCOMPLETA" : "",
                  (e.flags & EPOCA_COM_AMOSTRA_INVALIDA) ? "  SENSOR-MUDO" : "");
  }

  if (!ok) {
    Serial.println("  !! buffer saturado ate o teto do contrato: epoca DESCARTADA");
  }
}

// --- Rede (nao bloqueante) ---------------------------------------------

// Nenhuma funcao daqui para baixo espera por nada. A unica chamada que
// realmente bloqueia e `http.POST`, e ela so acontece quando ha folga
// suficiente ate o proximo tick -- ver `drenar`.
static void cuidar_da_rede(uint64_t agora) {
  bool conectado_agora = (WiFi.status() == WL_CONNECTED);

  if (conectado_agora) {
    if (!rede.conectado()) {
      rede.registrar_sucesso(agora);
      tentativa_wifi_em_curso = false;
      Serial.print("WiFi conectado. IP: ");
      Serial.println(WiFi.localIP());
    }
    return;
  }

  if (rede.conectado()) {
    rede.registrar_queda(agora);
    tentativa_wifi_em_curso = false;
    Serial.println("WiFi caiu. A amostragem continua; as epocas vao para o buffer.");
    return;
  }

  // Tentativa em curso: so desiste quando o orcamento estoura.
  if (tentativa_wifi_em_curso) {
    if (agora >= tentativa_wifi_expira_em) {
      tentativa_wifi_em_curso = false;
      rede.registrar_falha(agora);
      Serial.printf("WiFi nao subiu em %u ms. Nova tentativa em %.1f s. ",
                    rede.parametros().orcamento_ms, rede.espera_atual() / 1000.0);
      Serial.printf("Buffer: %lu epocas (%.2f h).\n",
                    (unsigned long)buffer.tamanho(), buffer.horas_cobertas());
    }
    return;
  }

  if (rede.deve_tentar(agora)) {
    WiFi.disconnect();
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
    tentativa_wifi_em_curso = true;
    tentativa_wifi_expira_em = agora + rede.parametros().orcamento_ms;
  }
}

// Sincroniza a hora de parede quando a rede sobe. Ate isso acontecer, as
// epocas saem SEM o campo `ts` e o backend usa o `created_at` do recebimento.
// Carimbar hora inventada seria pior: o backend aceitaria, e a noite ficaria
// arquivada com um horario que ninguem mais consegue corrigir.
static void cuidar_do_relogio(uint64_t agora) {
  if (parede.valida || !rede.conectado()) return;

  static bool pediu_ntp = false;
  if (!pediu_ntp) {
    configTime(0, 0, "pool.ntp.org", "time.nist.gov");  // UTC; o backend guarda UTC
    pediu_ntp = true;
    return;
  }

  // `time()` devolve um valor pequeno ate o NTP responder. Consulta sem
  // bloquear: se ainda nao chegou, tentamos na proxima volta.
  time_t t = time(nullptr);
  if (t > 1600000000L) {  // depois de 2020: o NTP respondeu
    parede.sincronizar(agora, (int64_t)t * 1000LL);
    Serial.println("Hora sincronizada. As epocas passam a sair carimbadas com `ts`.");
    Serial.printf("  %lu epocas no buffer serao resolvidas para tras a partir daqui.\n",
                  (unsigned long)buffer.tamanho());
  }
}

// --- Envio --------------------------------------------------------------

// Devolve true quando a epoca pode sair da fila (entregue ou definitivamente
// recusada pelo backend -- reenviar um 400 para sempre seria travar a fila).
static bool postar(const char *payload) {
  WiFiClientSecure client;
  // Ignora a validacao do certificado do servidor. Ver a nota SEC-05 no
  // roadmap: para um teste de bancada serve, para o produto nao.
  client.setInsecure();
  client.setTimeout(ORCAMENTO_POST_MS / 1000);

  HTTPClient http;
  http.setTimeout(ORCAMENTO_POST_MS);
  http.begin(client, URL_API);
  http.addHeader("Content-Type", "application/json");
  // Autenticacao do dispositivo (SEC-02). Sem o header a API responde 401.
  http.addHeader("X-Device-Token", DEVICE_TOKEN);

  int codigo = http.POST(payload);
  bool sai_da_fila = false;

  if (codigo == 201) {
    enviadas++;
    sai_da_fila = true;
  } else if (codigo == 400) {
    // Recusa de validacao e determinística: o mesmo payload sera recusado
    // para sempre. Mante-lo na fila entupiria a drenagem e faria o buffer
    // saturar por causa de UMA epoca malformada.
    recusadas++;
    sai_da_fila = true;
    Serial.println("  [400] RECUSADO PELA VALIDACAO (epoca descartada da fila)");
    Serial.println("     " + http.getString());
  } else if (codigo == 401) {
    falhas_de_envio++;
    Serial.println("  [401] NAO AUTORIZADO");
    Serial.println("     DEVICE_TOKEN ausente, revogado ou de outro dispositivo.");
    Serial.println("     Pareie de novo em Configuracoes e atualize secrets.h.");
    Serial.println("     O dado FICA no buffer: e problema de credencial, nao de dado.");
  } else if (codigo == 503) {
    // O backend responde 503 quando nao conseguiu gravar (FIX-02). O dado
    // fica na fila: e exatamente para isso que a fila existe.
    falhas_de_envio++;
    Serial.println("  [503] BANCO INDISPONIVEL -- a epoca continua no buffer");
  } else {
    falhas_de_envio++;
    Serial.printf("  [%d] falha de envio -- a epoca continua no buffer\n", codigo);
  }

  http.end();
  return sai_da_fila;
}

// Drena o buffer em rajada limitada, e SO se houver folga ate o proximo tick.
//
// Esta e a linha de defesa da cadencia. `http.POST` e a unica chamada
// bloqueante que sobrou no laco -- nao da para torna-la assincrona sem
// reescrever a pilha HTTP. Entao ela nao e evitada: e ORCADA. Se faltam menos
// de ORCAMENTO_POST_MS para a proxima amostra, nao se posta nesta volta. O
// dado espera; a medida, nao.
static void drenar(uint64_t agora) {
  if (!rede.conectado() || buffer.vazio()) return;

  for (uint8_t i = 0; i < MAXIMO_POSTS_POR_VOLTA && !buffer.vazio(); i++) {
    if (cadencia.ms_ate_o_proximo(agora) < ORCAMENTO_POST_MS) return;

    Epoca e;
    if (!buffer.primeira(&e)) return;

    // Instante monotonico do INICIO da epoca, reconstruido da grade -- nunca
    // acumulado. E o que mantem `ts[k+1] - ts[k] == epoca_s`.
    uint64_t inicio = acumulador.inicio_do_slot(e.primeiro_slot());

    char corpo[256];
    uint32_t n = 0;
    ResultadoDeMontagem r = montar_payload(e, parede, inicio, corpo, sizeof(corpo), &n);

    if (r == PAYLOAD_EPOCA_VAZIA) {
      // Lacuna nao se envia: `ax/ay/az` sao obrigatorios e inventa-los seria
      // fabricar medida. Ela ja cumpriu o papel dela -- manter a grade
      // intacta no buffer -- e no backend a lacuna aparece como o intervalo
      // entre dois `ts`, que e o que ela e.
      buffer.confirmar_entrega();
      lacunas_puladas++;
      continue;
    }
    if (r != PAYLOAD_OK) {
      buffer.confirmar_entrega();
      recusadas++;
      Serial.printf("  epoca %lu nao virou payload (motivo %d) -- descartada\n",
                    (unsigned long)e.indice, (int)r);
      continue;
    }

    if (postar(corpo)) {
      buffer.confirmar_entrega();
    } else {
      return;  // falha transitoria: para a rajada, tenta na proxima volta
    }

    agora = relogio.atualizar(millis());
  }
}

// --- Relatorio ----------------------------------------------------------

static void relatar(uint64_t agora) {
  if (agora < proximo_relatorio) return;
  proximo_relatorio = agora + 60000;

  const EstatisticasDoBuffer &s = buffer.estatisticas();
  Serial.println("-----------------------------------------------------");
  Serial.printf("cadencia : %llu ticks servidos, %llu perdidos, maior atraso %llu ms\n",
                (unsigned long long)cadencia.ticks_servidos(),
                (unsigned long long)cadencia.ticks_perdidos(),
                (unsigned long long)cadencia.maior_atraso_ms());
  Serial.printf("buffer   : %lu/%lu epocas (%.2f h), nivel max %u, %lu fusoes, %lu descartes\n",
                (unsigned long)buffer.tamanho(), (unsigned long)buffer.capacidade(),
                buffer.horas_cobertas(), s.nivel_maximo,
                (unsigned long)s.fusoes, (unsigned long)s.descartes);
  Serial.printf("envio    : %lu ok, %lu recusadas, %lu falhas, %lu lacunas puladas\n",
                (unsigned long)enviadas, (unsigned long)recusadas,
                (unsigned long)falhas_de_envio, (unsigned long)lacunas_puladas);
  Serial.printf("rede     : %s | hora de parede: %s\n",
                rede.conectado() ? "conectada" : "fora",
                parede.valida ? "sincronizada" : "NAO sincronizada (sem `ts`)");
  Serial.println("-----------------------------------------------------");
}

// --- Setup --------------------------------------------------------------

void setup() {
  Serial.begin(115200);
  // Antes havia `while (!Serial) delay(10);` aqui. Numa placa alimentada por
  // powerbank -- que e como uma captacao noturna acontece -- nao ha monitor
  // serial nenhum, e esse laco nunca sai. O firmware ficava esperando um
  // humano que nao ia chegar, a noite inteira. Nada da medicao pode depender
  // de alguem estar olhando.
  delay(100);

  Serial.println();
  Serial.println("=====================================================");
  Serial.println(" ENVIO CONTINUO - epocas de 30 s, buffer local (HW-05)");
  Serial.println("=====================================================");

  Wire.begin(21, 22);
  sensor_online = tentar_iniciar_sensor();
  if (sensor_online) {
    Serial.println("MPU6050: online (+-8 g, +-500 deg/s, filtro 21 Hz)");
  } else {
    Serial.println("MPU6050 nao respondeu. Confira 3V3, GND, SDA=21, SCL=22.");
    Serial.println("Seguindo assim mesmo: o laco tenta de novo a cada 5 s e a");
    Serial.println("grade de epocas ja comeca a correr, registrando as lacunas.");
  }

  // Rede em modo estacao, sem esperar. `WiFi.begin` nao bloqueia; quem espera
  // e quem fica olhando `WiFi.status()` num laco -- e ninguem aqui faz isso.
  WiFi.mode(WIFI_STA);

  uint64_t agora = relogio.atualizar(millis());
  cadencia.iniciar(agora, INTERVALO_AMOSTRA_MS);
  acumulador.iniciar(agora, cadencia.amostras_por_epoca(DURACAO_EPOCA_BASE_S),
                     ao_fechar_epoca, nullptr);
  rede.iniciar(agora);
  proximo_relatorio = agora + 60000;

  Serial.printf("Amostra a cada %lu s, epoca de %u s (%u amostras por epoca).\n",
                (unsigned long)(INTERVALO_AMOSTRA_MS / 1000), DURACAO_EPOCA_BASE_S,
                cadencia.amostras_por_epoca(DURACAO_EPOCA_BASE_S));
  Serial.printf("Buffer: %lu epocas = %.1f h em resolucao cheia.\n",
                (unsigned long)CAPACIDADE_EPOCAS,
                (CAPACIDADE_EPOCAS * DURACAO_EPOCA_BASE_S) / 3600.0);
  Serial.println("-----------------------------------------------------");
}

// --- Loop ---------------------------------------------------------------

void loop() {
  uint64_t agora = relogio.atualizar(millis());

  // ── 1. MEDIR ──────────────────────────────────────────────────────────
  // Primeiro, sempre, e sem depender de nada. Nem de rede, nem de serial,
  // nem de o sensor estar vivo.

  if (!sensor_online && agora >= proxima_tentativa_sensor) {
    proxima_tentativa_sensor = agora + RETENTATIVA_SENSOR_MS;
    sensor_online = tentar_iniciar_sensor();
    if (sensor_online) {
      Serial.println("MPU6050 voltou. Retomando a medicao.");
      avisou_sensor_mudo = false;
    }
  }

  if (cadencia.deve_amostrar(agora)) {
    if (!sensor_online) {
      acumulador.amostrar_invalida(agora);
    } else {
      sensors_event_t a, g, temp;
      mpu.getEvent(&a, &g, &temp);

      // Magnitude COM a gravidade: ~9,81 em repouso, nao zero. Contrato 2.1.
      float total = sqrtf(a.acceleration.x * a.acceleration.x +
                          a.acceleration.y * a.acceleration.y +
                          a.acceleration.z * a.acceleration.z);

      if (!magnitude_plausivel(total)) {
        // Parado na Terra, |a| vale ~9,81 em qualquer pose. Com os
        // registradores zerados, |a| = 0 e a intensidade vira 9,81 -- acima
        // do limiar. O aparelho classificaria como MOVIMENTO, e o backend
        // ACEITARIA: o payload e internamente coerente e zero esta na faixa
        // fisica declarada. Um fio de VCC solto encheria o banco de eventos
        // FABRICADOS a noite inteira. Pior que silencio: silencio se percebe.
        acumulador.amostrar_invalida(agora);
        explicar_sensor_mudo(temp.temperature);
      } else {
        if (avisou_sensor_mudo) {
          avisou_sensor_mudo = false;
          Serial.println("  sensor voltou a medir");
        }
        acumulador.amostrar(agora, a.acceleration.x, a.acceleration.y,
                            a.acceleration.z, total, temp.temperature);
      }
    }
  }

  // Fecha o que venceu, mesmo sem ter amostrado nesta volta. E o que faz uma
  // noite com o sensor solto produzir lacunas DECLARADAS em vez de nada.
  acumulador.fechar_ate(agora);

  // ── 2. REDE ───────────────────────────────────────────────────────────
  // Outro raciocinio. Nada aqui pode alcancar o bloco de cima.

  cuidar_da_rede(agora);
  cuidar_do_relogio(agora);
  drenar(agora);
  relatar(agora);

  // ── 3. CEDER O PROCESSADOR, SEM PERDER O TICK ─────────────────────────
  // Espera curta, e nunca alem do proximo tick. 20 ms de teto mantem o laco
  // responsivo sem queimar CPU a toa.
  uint32_t falta = cadencia.ms_ate_o_proximo(relogio.atualizar(millis()));
  delay(falta > 20 ? 20 : (falta == 0 ? 1 : falta));
}
