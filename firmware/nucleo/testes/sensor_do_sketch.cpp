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
//     encher a FIFO.
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
        const uint16_t bytes = enchendo() ? static_cast<uint16_t>(amostras_na_fifo * 6) : 0;
        b = i == 0 ? static_cast<uint8_t>(bytes >> 8) : static_cast<uint8_t>(bytes & 0xFF);
      } else if (ponteiro == 0x74) {  // FIFO_R_W: x = 0, y = 0, z = bruto_z
        const uint32_t k = i % 6;
        b = k < 4 ? 0 : (k == 4 ? static_cast<uint8_t>(bruto_z >> 8) : static_cast<uint8_t>(bruto_z & 0xFF));
      } else if (ponteiro == 0x41) {  // TEMP_OUT: ~30 graus C
        const int16_t t = static_cast<int16_t>((30.0 - 36.53) * 340.0);
        b = i == 0 ? static_cast<uint8_t>(t >> 8) : static_cast<uint8_t>(t & 0xFF);
      } else if (ponteiro == 0x3A) {
        b = 0;  // INT_STATUS: sem transbordo
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
  if (mpu.n_tx == 1) mpu.ponteiro = mpu.tx[0];
  if (mpu.n_tx == 2) mpu.escrever(mpu.tx[0], mpu.tx[1]);
  return 0;
}
uint8_t wire_request(size_t n) {
  mpu.preparar(static_cast<uint32_t>(n));
  return static_cast<uint8_t>(mpu.n_leitura);
}
int wire_read() { return mpu.pos < mpu.n_leitura ? mpu.leitura[mpu.pos++] : -1; }

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

static double media_de_z_da_grade() {
  double s = 0;
  for (uint32_t i = 0; i < AMOSTRAS_NA_GRADE; i++) s += grade_z[i];
  return s / AMOSTRAS_NA_GRADE;
}

int main() {
  mutex_fila = xSemaphoreCreateMutex();
  mutex_parede = xSemaphoreCreateMutex();
  mpu.reiniciar();
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

  printf("%d falhas\n", falhas);
  return falhas == 0 ? 0 : 1;
}
