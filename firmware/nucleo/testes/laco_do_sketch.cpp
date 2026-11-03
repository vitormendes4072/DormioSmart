// laco_do_sketch.cpp -- roda o laco REAL do sketch.ino no host (FW-10).
//
// ── POR QUE EXISTE ─────────────────────────────────────────────────────
//
// A logica do prazo da drenagem e da deriva do relogio esta no nucleo e e
// testada la. Mas quem CHAMA essas funcoes e o sketch, e o `make sintaxe` so
// prova que ele compila e liga: trocar a ordem de duas linhas no laco
// devolveria o defeito do FW-10 sem nenhum teste notar. Aqui o laco roda de
// verdade, com um relogio falso:
//
//   - o sono leve e o `vTaskDelay` avancam o relogio pelo que o sketch pediu;
//   - a primeira leitura I2C de cada volta e a drenagem: registra o instante
//     e soma o "trabalho" daquela volta (drenar + fechar + gravar na flash);
//   - `gettimeofday` devolve a hora que o teste manda, para o NTP.
//
// O sketch e incluido NESTA unidade de compilacao (`#include SKETCH`), para
// os testes lerem `contadores` e chamarem `tarefa_de_medicao`, que sao
// `static`. Os stubs com relogio sao montados por
// `verificar_laco_do_sketch.sh`, que tambem sabota o sketch e confere que
// este programa acusa.
#include <setjmp.h>
#include <stdio.h>
#include <sys/time.h>
#include <esp_sleep.h>
#include <esp_timer.h>
#include <freertos/FreeRTOS.h>
#include <freertos/task.h>

static int64_t relogio_us = 0;
static uint64_t despertar_pedido_us = 0;
static uint64_t trabalho_us[64];
static uint64_t drenagens_us[64];
static uint32_t voltas = 0, n_voltas = 0;
static int64_t unix_falso_ms = 0;
static jmp_buf fim;

int64_t esp_timer_get_time() { return relogio_us; }
int esp_sleep_enable_timer_wakeup(uint64_t us) {
  despertar_pedido_us = us;
  return 0;
}
int esp_light_sleep_start() {
  relogio_us += static_cast<int64_t>(despertar_pedido_us);
  return 0;
}
void vTaskDelay(const TickType_t t) { relogio_us += static_cast<int64_t>(t) * 1000; }
void gancho_i2c() {
  drenagens_us[voltas] = static_cast<uint64_t>(relogio_us);
  relogio_us += static_cast<int64_t>(trabalho_us[voltas]);
  if (++voltas >= n_voltas) longjmp(fim, 1);
}
static int gettimeofday_falso(struct timeval *tv, void *) {
  tv->tv_sec = unix_falso_ms / 1000;
  tv->tv_usec = (unix_falso_ms % 1000) * 1000;
  return 0;
}
#define gettimeofday gettimeofday_falso

#include SKETCH

static int falhas = 0;
static void conferir(bool ok, const char *msg) {
  printf("  %s %s\n", ok ? "ok   " : "FALHA", msg);
  if (!ok) falhas++;
}

struct Resultado {
  double media_s, menor_s;
};

static Resultado rodar(const uint64_t *trabalho, uint32_t n, bool radio_ocupado) {
  for (uint32_t i = 0; i < n; i++) trabalho_us[i] = trabalho[i];
  n_voltas = n;
  voltas = 0;
  relogio_us = 0;
  contadores.prazos_estourados.store(0);
  contadores.trabalho_max_us.store(0);
  cadeia.iniciar(0);
  if (radio_ocupado) {
    radio.pedir_envio();
  } else {
    radio.liberar();
  }
  if (setjmp(fim) == 0) tarefa_de_medicao(0);
  Resultado r;
  r.media_s = (drenagens_us[n - 1] - drenagens_us[0]) / 1e6 / (n - 1);
  r.menor_s = 1e9;
  for (uint32_t i = 5; i < n; i++) {
    const double d = (drenagens_us[i] - drenagens_us[i - 1]) / 1e6;
    if (d < r.menor_s) r.menor_s = d;
  }
  return r;
}

static bool no_intervalo(double s) {
  return s >= INTERVALO_DE_DRENAGEM_US / 1e6 &&
         s < (INTERVALO_DE_DRENAGEM_US + VARIACAO_DA_DRENAGEM_US) / 1e6;
}

int main() {
  mutex_fila = xSemaphoreCreateMutex();
  mutex_parede = xSemaphoreCreateMutex();

  printf("laco da medicao -- o trabalho nao empurra o despertar\n");
  const uint64_t cargas[] = {0, 400000, 1000000};
  for (int radio_ligado = 0; radio_ligado < 2; radio_ligado++) {
    for (int c = 0; c < 3; c++) {
      uint64_t t[40];
      for (int i = 0; i < 40; i++) t[i] = cargas[c];
      const Resultado r = rodar(t, 40, radio_ligado == 1);
      char msg[160];
      snprintf(msg, sizeof(msg), "%s, trabalho %4.0f ms: media %.3f s entre drenagens",
               radio_ligado ? "radio ligado (vTaskDelay)" : "sono leve", cargas[c] / 1000.0,
               r.media_s);
      conferir(no_intervalo(r.media_s), msg);
      conferir(contadores.prazos_estourados.load() == 0, "  ...sem prazo estourado");
      conferir(contadores.trabalho_max_us.load() == cargas[c], "  ...trabalho max = o injetado");
    }
  }

  printf("um trabalho de 4 s\n");
  uint64_t t[14];
  for (int i = 0; i < 14; i++) t[i] = 100000;
  t[3] = 4000000;
  const Resultado r = rodar(t, 14, false);
  conferir(contadores.prazos_estourados.load() == 1, "estoura o prazo uma vez, e o contador ve");
  conferir(r.menor_s >= INTERVALO_DE_DRENAGEM_US / 1e6, "depois do estouro, sem rajada");
  conferir(contadores.trabalho_max_us.load() == 4000000u, "trabalho max = 4 s");

  printf("deriva do relogio a cada NTP\n");
  relogio_us = 1000LL * 1000000;
  unix_falso_ms = 1758000000000LL;
  sincronizar_relogio();
  conferir(!deriva_acumulada.valida, "primeira sincronia: nada a medir");
  // 600 s no relogio interno; o NTP diz 600,06 s: o relogio atrasou 60 ms.
  relogio_us += 600LL * 1000000;
  unix_falso_ms += 600060;
  sincronizar_relogio();
  conferir(deriva_no_intervalo.valida && deriva_no_intervalo.deriva_ms == 60 &&
               deriva_no_intervalo.decorrido_ms == 600000,
           "deriva contra a sincronia anterior: +60 ms em 600 s");
  relogio_us += 600LL * 1000000;
  unix_falso_ms += 600060;
  sincronizar_relogio();
  conferir(deriva_no_intervalo.deriva_ms == 60, "segundo intervalo: +60 ms");
  conferir(deriva_acumulada.deriva_ms == 120 && deriva_acumulada.decorrido_ms == 1200000,
           "acumulada desde a primeira: +120 ms em 1200 s");

  printf("%d falhas\n", falhas);
  return falhas == 0 ? 0 : 1;
}
