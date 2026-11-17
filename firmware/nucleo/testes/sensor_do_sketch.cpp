// sensor_do_sketch.cpp -- o sketch.ino contra um MPU6050 FALSO (FW-11).
//
// ── POR QUE EXISTE ─────────────────────────────────────────────────────
//
// A calibracao e a vigia da FIFO estao no nucleo e sao testadas la
// (`testes_c2`). Mas quem as chama e o sketch: tirar a linha que calibra, ou
// a que confere o sensor, deixaria todos os testes do nucleo verdes e a noite
// errada. Aqui `drenar()`, `fechar_epocas()` e `conferir_sensor()` -- os do
// sketch, incluido nesta unidade -- conversam com um MPU6050 de mentira:
//
//   - ele guarda os registradores que o sketch escreve, e um reset
//     (PWR_MGMT_1 = 0x80) o devolve como o chip volta: DORMINDO e com a FIFO
//     desligada;
//   - acordado e com a FIFO ligada, entrega as amostras que o teste manda,
//     com o erro de Z medido na bancada de 11/11 (o eixo le -1,1541 g parado
//     de chip para baixo);
//   - `cair()` simula a queda de alimentacao: o sensor reinicia e para de
//     encher a FIFO;
//   - (FW-17, etapa 2) `travado` simula o sensor que segura o SDA: toda
//     transacao falha, e ele so solta depois de `pulsos_para_soltar` descidas
//     do SCL -- ou nunca (0), ate a energia voltar. Os pinos do sketch
//     (`pinMode`, `digitalWrite`, `digitalRead`) chegam aqui.
//
// O stub do `Wire` desta variante chama as funcoes `wire_*` abaixo; quem o
// monta e `verificar_laco_do_sketch.sh`, que tambem sabota o sketch.
#include <math.h>
#include <stdio.h>
#include <string.h>
#include <esp_sleep.h>
#include <esp_timer.h>
#include <freertos/FreeRTOS.h>
#include <freertos/task.h>

static int64_t relogio_us = 0;
int64_t esp_timer_get_time() { return relogio_us; }
int esp_sleep_enable_timer_wakeup(uint64_t) { return 0; }
int esp_light_sleep_start() { return 0; }
void vTaskDelay(const TickType_t) {}

// ── O MPU6050 falso ──────────────────────────────────────────────────────
struct MpuFalso {
  uint8_t regs[256];
  uint8_t tx[4];
  int n_tx;
  uint8_t ponteiro;
  uint8_t leitura[1024];
  uint32_t n_leitura, pos;
  uint16_t amostras_na_fifo;
  int16_t bruto_z;
  // FW-17: falhas injetadas. `falhas_pendentes` leituras do registrador
  // `falhar_registrador` voltam vazias (barramento falhou); `oflow` liga o bit
  // de transbordo; `contagem_forcada` >= 0 substitui FIFO_COUNT.
  uint8_t falhar_registrador;
  int falhas_pendentes;
  bool oflow;
  int32_t contagem_forcada;
  // FW-17, etapa 2: o barramento travado.
  bool travado;
  int pulsos_para_soltar;   // 0 = so volta com energia
  bool reinicia_ao_soltar;  // o VCC tinha caido junto: solta dormindo
  int descidas_de_scl;
  bool scl_alto;
  bool sda_puxado;          // o sketch segura o SDA baixo

  void reiniciar() {
    memset(regs, 0, sizeof(regs));
    regs[0x6B] = 0x40;  // PWR_MGMT_1: SLEEP, o padrao ao ligar
    regs[0x75] = 0x68;  // WHO_AM_I
    amostras_na_fifo = 0;
  }
  bool enchendo() const {
    return (regs[0x6B] & 0x40) == 0 && (regs[0x6A] & 0x40) != 0 && (regs[0x23] & 0x08) != 0;
  }
  void escrever(uint8_t reg, uint8_t v) {
    if (reg == 0x6B && (v & 0x80)) {  // DEVICE_RESET
      reiniciar();
      return;
    }
    if (reg == 0x6A && (v & 0x04)) amostras_na_fifo = 0;  // FIFO_RESET
    regs[reg] = static_cast<uint8_t>(v & ~0x04);
  }
  void preparar(uint32_t n) {
    n_leitura = 0;
    pos = 0;
    for (uint32_t i = 0; i < n && i < sizeof(leitura); i++) {
      uint8_t b = regs[static_cast<uint8_t>(ponteiro + i)];
      if (ponteiro == 0x72) {  // FIFO_COUNTH/L
        uint16_t bytes = enchendo() ? static_cast<uint16_t>(amostras_na_fifo * 6) : 0;
        if (contagem_forcada >= 0) bytes = static_cast<uint16_t>(contagem_forcada);
        b = i == 0 ? static_cast<uint8_t>(bytes >> 8) : static_cast<uint8_t>(bytes & 0xFF);
      } else if (ponteiro == 0x74) {  // FIFO_R_W: x = 0, y = 0, z = bruto_z
        const uint32_t k = i % 6;
        b = k < 4 ? 0 : (k == 4 ? static_cast<uint8_t>(bruto_z >> 8) : static_cast<uint8_t>(bruto_z & 0xFF));
      } else if (ponteiro == 0x41) {  // TEMP_OUT: ~30 graus C
        const int16_t t = static_cast<int16_t>((30.0 - 36.53) * 340.0);
        b = i == 0 ? static_cast<uint8_t>(t >> 8) : static_cast<uint8_t>(t & 0xFF);
      } else if (ponteiro == 0x3A) {
        b = oflow ? 0x10 : 0;  // INT_STATUS: FIFO_OFLOW so quando injetado
      }
      leitura[n_leitura++] = b;
    }
    if (ponteiro == 0x74) amostras_na_fifo = 0;  // o sketch le tudo que a contagem disse
  }
};
static MpuFalso mpu;

void wire_begin_tx(uint8_t) { mpu.n_tx = 0; }
void wire_write(uint8_t v) {
  if (mpu.n_tx < 4) mpu.tx[mpu.n_tx++] = v;
}
uint8_t wire_end_tx() {
  if (mpu.travado) return 2;  // ninguem confirma o endereco
  if (mpu.n_tx == 1) mpu.ponteiro = mpu.tx[0];
  if (mpu.n_tx == 2) mpu.escrever(mpu.tx[0], mpu.tx[1]);
  return 0;
}
uint8_t wire_request(size_t n) {
  if (mpu.travado) {
    mpu.n_leitura = 0;
    mpu.pos = 0;
    return 0;
  }
  if (mpu.falhas_pendentes > 0 && mpu.ponteiro == mpu.falhar_registrador) {
    mpu.falhas_pendentes--;
    mpu.n_leitura = 0;
    mpu.pos = 0;
    return 0;  // o barramento falhou: nenhum byte veio
  }
  mpu.preparar(static_cast<uint32_t>(n));
  return static_cast<uint8_t>(mpu.n_leitura);
}
int wire_read() { return mpu.pos < mpu.n_leitura ? mpu.leitura[mpu.pos++] : -1; }

// Os pinos: 21 = SDA, 22 = SCL (conferido contra o sketch no `main`).
void pinMode(int pino, int modo) {
  if (modo == INPUT_PULLUP && pino == 21) mpu.sda_puxado = false;
  if (modo == INPUT_PULLUP && pino == 22) mpu.scl_alto = true;
}
void digitalWrite(int pino, int v) {
  if (pino == 21) mpu.sda_puxado = v == LOW;
  if (pino != 22) return;
  const bool desceu = mpu.scl_alto && v == LOW;
  mpu.scl_alto = v != LOW;
  if (!desceu || !mpu.travado || mpu.pulsos_para_soltar == 0) return;
  if (++mpu.descidas_de_scl >= mpu.pulsos_para_soltar) {
    mpu.travado = false;
    if (mpu.reinicia_ao_soltar) mpu.reiniciar();
  }
}
int digitalRead(int pino) {
  if (pino == 21) return mpu.travado || mpu.sda_puxado ? LOW : HIGH;
  if (pino == 22) return mpu.scl_alto ? HIGH : LOW;
  return LOW;
}

#include SKETCH

static int falhas = 0;
static void conferir(bool ok, const char *msg) {
  printf("  %s %s\n", ok ? "ok   " : "FALHA", msg);
  if (!ok) falhas++;
}

// Uma volta da medicao, como `tarefa_de_medicao` faria: o tempo anda o
// intervalo da drenagem, a FIFO enche 85 amostras (50 Hz) se o sensor estiver
// medindo, e o sketch drena e fecha o que puder.
static void volta(bool sensor_enche) {
  relogio_us += INTERVALO_DE_DRENAGEM_US;
  if (sensor_enche && mpu.enchendo()) mpu.amostras_na_fifo = 85;
  drenar();
  fechar_epocas();
}

// FW-17: uma volta com a falha injetada tem de somar 1 no total e 1 so na
// causa esperada.
static void conferir_perda(int esperada, const char *rotulo) {
  uint32_t antes[N_CAUSAS_DE_PERDA];
  for (int i = 0; i < N_CAUSAS_DE_PERDA; i++) antes[i] = contadores.perdas[i].load();
  const uint32_t total = contadores.transbordos.load();
  volta(true);
  bool ok = contadores.transbordos.load() == total + 1;
  for (int i = 0; i < N_CAUSAS_DE_PERDA; i++) {
    ok = ok && contadores.perdas[i].load() == antes[i] + (i == esperada ? 1u : 0u);
  }
  conferir(ok, rotulo);
}

static double media_de_z_da_grade() {
  double s = 0;
  for (uint32_t i = 0; i < AMOSTRAS_NA_GRADE; i++) s += grade_z[i];
  return s / AMOSTRAS_NA_GRADE;
}

int main() {
  mutex_fila = xSemaphoreCreateMutex();
  mutex_parede = xSemaphoreCreateMutex();
  mpu.reiniciar();
  mpu.contagem_forcada = -1;  // FW-17: sem falha injetada ate a secao dela
  mpu.bruto_z = static_cast<int16_t>(lround(-1.1541 * LSB_POR_G));  // chip para baixo, com o erro de Z

  printf("o sketch contra um MPU6050 falso -- FW-11\n");
  calibracao = calibracao_da_unidade();
  conferir(configurar_mpu() && mpu.enchendo(), "configurar_mpu acorda o sensor e liga a FIFO");
  origem_us = 0;
  cadeia.iniciar(origem_us);

  printf("a calibracao da unidade, nas amostras da noite\n");
  for (int i = 0; i < 45; i++) volta(true);
  const double z = media_de_z_da_grade();
  char msg[160];
  snprintf(msg, sizeof(msg), "a grade da epoca le Z = %.4f g (o sensor le -1,1541 g; calibrado, -1 g)", z);
  conferir(fabs(z + 1.0) < 0.003, msg);
  // A epoca 0 nao tem sinal antes dela para o filtro (a origem e o boot), e e
  // recusada no sketch de verdade tambem; as seguintes nao.
  snprintf(msg, sizeof(msg), "so a epoca 0 recusada com o sensor medindo (recusadas: %u)",
           static_cast<unsigned>(contadores.recusadas.load()));
  conferir(contadores.recusadas.load() <= 1, msg);

  printf("o sensor cai no meio da noite\n");
  const uint32_t antes = contadores.reacordados.load();
  mpu.reiniciar();  // queda de alimentacao: volta dormindo, FIFO desligada
  volta(true);
  volta(true);
  conferir(contadores.reacordados.load() == antes, "duas drenagens vazias ainda nao mexem");
  volta(true);
  conferir(contadores.reacordados.load() == antes + 1, "a terceira manda conferir, e o sensor e reacordado");
  conferir(mpu.enchendo(), "depois de reacordado, o sensor mede e enche a FIFO");
  volta(true);
  conferir(mpu.amostras_na_fifo == 0 && vigia.vazias() == 0, "a drenagem seguinte traz amostras de novo");

  printf("FIFO vazia com o sensor acordado nao reconfigura\n");
  const uint32_t depois = contadores.reacordados.load();
  for (int i = 0; i < 6; i++) volta(false);
  conferir(contadores.reacordados.load() == depois, "6 drenagens vazias, sensor acordado: nada");

  printf("FW-17: cada drenagem descartada conta na sua causa\n");
  {
    const uint32_t total = contadores.transbordos.load();
    volta(true);
    conferir(contadores.transbordos.load() == total, "sem falha injetada, nenhuma perda");
  }
  mpu.falhar_registrador = 0x3A;  // INT_STATUS
  mpu.falhas_pendentes = 1;
  conferir_perda(PERDA_I2C_NO_ESTADO, "o barramento falha no INT_STATUS: i2c no estado");
  mpu.oflow = true;
  conferir_perda(PERDA_TRANSBORDO_BIT, "FIFO_OFLOW ligado: transbordo (bit)");
  mpu.oflow = false;
  mpu.contagem_forcada = 1024;
  conferir_perda(PERDA_TRANSBORDO_TETO, "contagem 1024 sem o bit: transbordo (teto)");
  mpu.contagem_forcada = 511;
  conferir_perda(PERDA_DESALINHADA, "contagem 511: desalinhada");
  mpu.contagem_forcada = -1;
  mpu.falhar_registrador = 0x74;  // FIFO_R_W
  mpu.falhas_pendentes = 1;
  conferir_perda(PERDA_I2C_NA_LEITURA, "o barramento falha nos bytes da FIFO: i2c na leitura");
  {
    const uint32_t total = contadores.transbordos.load();
    volta(true);
    conferir(contadores.transbordos.load() == total, "depois das falhas, a drenagem volta ao normal");
  }

  printf("FW-17, etapa 2: o sensor que trava o barramento\n");
  conferir(PINO_SDA == 21 && PINO_SCL == 22, "o MPU6050 falso esta nos pinos do sketch");
  conferir(contadores.liberacoes.load() == 0, "as falhas isoladas acima nao liberaram o barramento");
  // A: solta com 4 pulsos, e tinha reiniciado junto (o VCC caiu por um instante).
  mpu.travado = true;
  mpu.pulsos_para_soltar = 4;
  mpu.reinicia_ao_soltar = true;
  mpu.descidas_de_scl = 0;
  volta(true);
  volta(true);
  conferir(contadores.liberacoes.load() == 0, "duas drenagens sem resposta ainda nao liberam");
  volta(true);
  conferir(contadores.liberacoes.load() == 1 && contadores.liberacoes_com_resposta.load() == 1 &&
               !mpu.travado,
           "a terceira libera: os pulsos no SCL soltam o sensor, e ele responde");
  conferir(mpu.enchendo(), "o sensor que reiniciou junto sai da liberacao reconfigurado");
  {
    const uint32_t total = contadores.transbordos.load();
    volta(true);
    conferir(contadores.transbordos.load() == total && mpu.amostras_na_fifo == 0,
             "a drenagem seguinte ja traz amostras");
  }
  // B: so volta com energia. As tentativas recuam: 3, +6, +12, +24 = 4 em 60.
  mpu.travado = true;
  mpu.pulsos_para_soltar = 0;
  mpu.reinicia_ao_soltar = false;
  {
    const uint32_t lib = contadores.liberacoes.load();
    const uint32_t resp = contadores.liberacoes_com_resposta.load();
    for (int i = 0; i < 60; i++) volta(true);
    snprintf(msg, sizeof(msg), "sensor mudo: %u tentativas em 60 drenagens (4, com recuo), nenhuma resposta",
             static_cast<unsigned>(contadores.liberacoes.load() - lib));
    conferir(contadores.liberacoes.load() - lib == 4 && contadores.liberacoes_com_resposta.load() == resp,
             msg);
  }
  {
    const uint32_t reac = contadores.reacordados.load();
    mpu.travado = false;
    mpu.reiniciar();  // a energia volta: o sensor acorda dormindo
    for (int i = 0; i < 4; i++) volta(true);
    conferir(mpu.enchendo() && contadores.reacordados.load() == reac + 1,
             "com a energia de volta, a vigia do FW-11 reacorda o sensor");
  }
  // C: depois de uma resposta, o recuo zerou -- um travamento novo libera em 3.
  mpu.travado = true;
  mpu.pulsos_para_soltar = 1;
  mpu.descidas_de_scl = 0;
  {
    const uint32_t lib = contadores.liberacoes.load();
    for (int i = 0; i < 3; i++) volta(true);
    conferir(contadores.liberacoes.load() == lib + 1 && !mpu.travado,
             "um travamento novo libera em 3 drenagens, sem o recuo do anterior");
    volta(true);
  }
  // D: falhas separadas por respostas nao somam.
  {
    const uint32_t lib = contadores.liberacoes.load();
    for (int k = 0; k < 4; k++) {
      mpu.falhar_registrador = 0x3A;
      mpu.falhas_pendentes = 2;
      volta(true);
      volta(true);
      volta(true);
    }
    conferir(contadores.liberacoes.load() == lib, "pares de falhas com uma resposta no meio nao liberam");
  }

  printf("%d falhas\n", falhas);
  return falhas == 0 ? 0 : 1;
}
