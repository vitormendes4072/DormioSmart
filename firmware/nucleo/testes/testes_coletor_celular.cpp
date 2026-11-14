// testes_coletor_celular.cpp -- o coletor do celular (APP-02) contra o dourado da C2.
//
// O celular entrega o INSTANTE de cada amostra, que a placa nao tem. Este
// teste le o mesmo `ml/testes/vetor_dourado_cadeia_c2.json` do
// `testes_cadeia_c2.cpp`, entrega cada amostra ao `ColetorCelular` no seu
// instante verdadeiro (em m/s^2, como o Android entrega), e confere as
// features de cada epoca contra o `esperado` -- o pipeline do `ml/` com o
// tempo verdadeiro -- com as MESMAS tolerancias de validade da placa.
//
// A regua de exatidao do teste da cadeia (linha do tempo e grade contra o
// `estilo_firmware`) nao se aplica: as drenagens do celular nao sao as da
// FIFO. O que tem de valer e a validade: as features do celular e as da placa
// medem o mesmo sinal dentro da mesma tolerancia.
//
// Depois, os casos que o dourado nao cobre: jitter de carimbo, taxa que a
// cadeia recusa, amostra fora de ordem, um buraco de minutos e o payload.

#include <math.h>
#include <stdio.h>
#include <string.h>

#include "../coletor_celular.h"
#include "../epoca_c2.h"
#include "../reamostragem.h"
#include "leitor_json.h"

using namespace dormio;
using dormio::testes::LeitorJson;

static int falhas = 0;
static int total = 0;

#define VERIFICAR(cond, ...)                                        \
  do {                                                              \
    total++;                                                        \
    if (!(cond)) {                                                  \
      falhas++;                                                     \
      printf("  FALHOU  ");                                         \
      printf(__VA_ARGS__);                                          \
      printf("\n          (%s:%d)  %s\n", __FILE__, __LINE__, #cond); \
    }                                                               \
  } while (0)

struct Tolerancias {
  double enmo_abs_g, enmo_max_abs_g, mag_din_rel, zcr_cruzamentos, p_frac_amostras,
      g_angulo_graus;
};

static const uint32_t MAX_AMOSTRAS = 4096;
static const uint32_t MAX_DRENAGENS = 64;
static const uint32_t MAX_EPOCAS = 4;

// O gerador do dourado comeca o sinal 2 s antes da epoca 0
// (`gerar_caso(inicio_s=-2.0)` em `ml/testes/dourado_cadeia_c2.py`). O arquivo
// nao grava o instante de cada amostra -- a placa nao o tem --, entao este
// teste o reconstroi e CONFERE a reconstrucao contra as drenagens do arquivo.
static const double INICIO_DO_DOURADO_S = -2.0;

struct Caso {
  double seed, fs_real_hz, origem_us;
  uint32_t n_amostras;
  int16_t lsb[MAX_AMOSTRAS][3];
  uint32_t n_drenagens;
  double drenagem_t_us[MAX_DRENAGENS];
  uint32_t drenagem_n[MAX_DRENAGENS];
  uint32_t n_epocas;
  double esperado[MAX_EPOCAS][6];
  double g[MAX_EPOCAS][3];
};

static const char *const ORDEM[6] = {"enmo_media", "enmo_desvio", "enmo_max",
                                     "mag_din_media", "zcr", "p_frac"};

static bool ler_esperado(LeitorJson &l, Caso *c) {
  char k[48];
  if (!l.entrar_objeto()) return false;
  while (l.proxima_chave(k, sizeof(k))) {
    if (strcmp(k, "esperado") == 0) {
      if (!l.entrar_objeto()) return false;
      char k2[48];
      while (l.proxima_chave(k2, sizeof(k2))) {
        bool achou = false;
        for (int i = 0; i < 6; i++) {
          if (strcmp(k2, ORDEM[i]) == 0) {
            l.ler_numero(&c->esperado[c->n_epocas][i]);
            achou = true;
          }
        }
        if (!achou) {
          if (strcmp(k2, "g") == 0) l.ler_array_de_numeros(c->g[c->n_epocas], 3);
          else l.pular_valor();
        }
        if (l.erro()) return false;
      }
    } else {
      l.pular_valor();
    }
    if (l.erro()) return false;
  }
  return !l.erro();
}

static bool ler_caso(LeitorJson &l, Caso *c) {
  char k[48];
  c->n_amostras = 0;
  c->n_drenagens = 0;
  c->n_epocas = 0;
  if (!l.entrar_objeto()) return false;
  while (l.proxima_chave(k, sizeof(k))) {
    if (strcmp(k, "seed") == 0) l.ler_numero(&c->seed);
    else if (strcmp(k, "fs_real_hz") == 0) l.ler_numero(&c->fs_real_hz);
    else if (strcmp(k, "origem_us") == 0) l.ler_numero(&c->origem_us);
    else if (strcmp(k, "drenagens") == 0) {
      if (!l.entrar_array()) return false;
      while (l.proximo_elemento()) {
        double par[2];
        if (c->n_drenagens >= MAX_DRENAGENS || !l.ler_array_de_numeros(par, 2)) {
          l.falhar("drenagens demais ou malformadas");
          return false;
        }
        c->drenagem_t_us[c->n_drenagens] = par[0];
        c->drenagem_n[c->n_drenagens] = static_cast<uint32_t>(par[1]);
        c->n_drenagens++;
      }
    } else if (strcmp(k, "amostras_lsb") == 0) {
      if (!l.entrar_array()) return false;
      while (l.proximo_elemento()) {
        double v[3];
        if (c->n_amostras >= MAX_AMOSTRAS || !l.ler_array_de_numeros(v, 3)) {
          l.falhar("amostras demais ou malformadas");
          return false;
        }
        for (int i = 0; i < 3; i++) c->lsb[c->n_amostras][i] = static_cast<int16_t>(v[i]);
        c->n_amostras++;
      }
    } else if (strcmp(k, "epocas") == 0) {
      if (!l.entrar_array()) return false;
      while (l.proximo_elemento()) {
        if (c->n_epocas >= MAX_EPOCAS || !ler_esperado(l, c)) {
          l.falhar("epoca malformada ou epocas demais");
          return false;
        }
        c->n_epocas++;
      }
    } else {
      l.pular_valor();
    }
    if (l.erro()) return false;
  }
  return !l.erro();
}

static double instante_verdadeiro_us(const Caso &c, uint32_t k) {
  return c.origem_us + (INICIO_DO_DOURADO_S + k / c.fs_real_hz) * 1e6;
}

// A reconstrucao do tempo tem de ser a do gerador: cada drenagem do arquivo
// aconteceu depois da ultima amostra que ela levou e antes da seguinte.
static void conferir_reconstrucao(const Caso &c) {
  uint32_t acumulado = 0;
  uint32_t ruins = 0;
  for (uint32_t d = 0; d < c.n_drenagens; d++) {
    acumulado += c.drenagem_n[d];
    if (acumulado == 0) continue;
    const double antes = instante_verdadeiro_us(c, acumulado - 1);
    const double depois = instante_verdadeiro_us(c, acumulado);
    if (!(antes <= c.drenagem_t_us[d] + 1.0 && c.drenagem_t_us[d] <= depois + 1.0)) ruins++;
  }
  VERIFICAR(ruins == 0, "[%.1f Hz] %u drenagens fora do intervalo das amostras: o instante "
            "reconstruido nao e o do gerador", c.fs_real_hz, ruins);
}

static ResolucaoDeParede parede_de_teste(uint64_t origem_us) {
  ResolucaoDeParede p;
  // 2026-11-08T00:00:00Z na origem monotonica.
  p.sincronizar(origem_us / 1000u, 1794096000000LL);
  return p;
}

static double pior[6] = {0, 0, 0, 0, 0, 0};
static double pior_ang = 0;

// Roda um caso pelo coletor. `jitter_us` > 0 soma ao carimbo um desvio
// deterministico em [-jitter, +jitter]. Confere todas as epocas do dourado.
static void rodar_caso(const Caso &c, const Tolerancias &tol, double jitter_us) {
  static ColetorCelular coletor;
  const uint64_t origem = static_cast<uint64_t>(c.origem_us);
  coletor.iniciar(origem, parede_de_teste(origem));
  coletor.definir_temperatura(31.5f);

  bool fechada[MAX_EPOCAS] = {false, false, false, false};
  uint32_t proxima = 0;
  static char json[TAMANHO_DO_PAYLOAD];
  uint32_t xorshift = 0x9E3779B9u ^ static_cast<uint32_t>(c.seed);

  for (uint32_t k = 0; k < c.n_amostras; k++) {
    double t = instante_verdadeiro_us(c, k);
    if (jitter_us > 0) {
      xorshift ^= xorshift << 13;
      xorshift ^= xorshift >> 17;
      xorshift ^= xorshift << 5;
      t += jitter_us * (2.0 * (xorshift / 4294967295.0) - 1.0);
    }
    const float ms2 = G_PADRAO_MS2 / LSB_POR_G;
    coletor.amostrar(static_cast<uint64_t>(llround(t)), c.lsb[k][0] * ms2, c.lsb[k][1] * ms2,
                     c.lsb[k][2] * ms2);

    for (;;) {
      uint32_t n = 0;
      const ResultadoDoColetor r = coletor.proximo(json, sizeof(json), &n);
      if (r == COLETOR_NADA) break;
      const uint32_t e = proxima++;
      if (e >= c.n_epocas) continue;
      VERIFICAR(r == COLETOR_PAYLOAD, "[%.1f Hz, jitter %.0f us] epoca %u sem payload (%d)",
                c.fs_real_hz, jitter_us, e, static_cast<int>(r));
      if (r != COLETOR_PAYLOAD) continue;
      fechada[e] = true;

      const FeaturesDeEpoca &f = coletor.ultimas_features();
      VERIFICAR(coletor.ultima_teve_features(), "[%.1f Hz] epoca %u sem features", c.fs_real_hz,
                e);
      const double v[3] = {f.enmo_media, f.enmo_desvio, f.enmo_max};
      for (int i = 0; i < 3; i++) {
        const double d = fabs(v[i] - c.esperado[e][i]);
        const double lim = (i == 2) ? tol.enmo_max_abs_g : tol.enmo_abs_g;
        if (d > pior[i]) pior[i] = d;
        VERIFICAR(d <= lim, "[%.1f Hz, jitter %.0f us, ep %u] %s diverge %.3e g (tol %.1e)",
                  c.fs_real_hz, jitter_us, e, ORDEM[i], d, lim);
      }
      const double rel = fabs(f.mag_din_media - c.esperado[e][3]) / c.esperado[e][3];
      if (rel > pior[3]) pior[3] = rel;
      VERIFICAR(rel <= tol.mag_din_rel, "[%.1f Hz, jitter %.0f us, ep %u] mag_din %.2f %%",
                c.fs_real_hz, jitter_us, e, 100.0 * rel);
      const double zcr = fabs(f.zcr - c.esperado[e][4]) * (AMOSTRAS_NA_GRADE - 1);
      if (zcr > pior[4]) pior[4] = zcr;
      VERIFICAR(zcr <= tol.zcr_cruzamentos + 1e-9, "[%.1f Hz, ep %u] zcr diverge %.1f",
                c.fs_real_hz, e, zcr);
      const double pf = fabs(f.p_frac - c.esperado[e][5]) * AMOSTRAS_NA_GRADE;
      if (pf > pior[5]) pior[5] = pf;
      VERIFICAR(pf <= tol.p_frac_amostras + 1e-9, "[%.1f Hz, ep %u] p_frac diverge %.1f",
                c.fs_real_hz, e, pf);
      double dot = f.gx * c.g[e][0] + f.gy * c.g[e][1] + f.gz * c.g[e][2];
      if (dot > 1.0) dot = 1.0;
      const double ang = acos(dot) * 180.0 / 3.141592653589793;
      if (ang > pior_ang) pior_ang = ang;
      VERIFICAR(ang <= tol.g_angulo_graus, "[%.1f Hz, ep %u] g diverge %.4f grau",
                c.fs_real_hz, e, ang);

      // O payload: o formato da placa, com `ts` no inicio da epoca e o vetor.
      char ts[32];
      const ResolucaoDeParede p = parede_de_teste(origem);
      formatar_iso8601_utc(p.resolver(inicio_da_epoca_c2_ms(origem, e)), ts, sizeof(ts));
      char chave[48];
      snprintf(chave, sizeof(chave), "\"ts\":\"%s\"", ts);
      VERIFICAR(strstr(json, chave) != 0, "epoca %u: payload sem %s: %s", e, chave, json);
      VERIFICAR(strstr(json, "\"epoca_s\":30,") != 0, "epoca %u: epoca_s", e);
      VERIFICAR(strstr(json, "\"f\":[") != 0 && strstr(json, "\"fs\":32,") != 0,
                "epoca %u: payload sem o vetor: %s", e, json);
      // CAL-03: a norma da gravidade media, a da epoca antes da quantizacao, e
      // a marca de que nenhuma calibracao foi aplicada (o dourado nao define).
      char gn[48];
      snprintf(gn, sizeof(gn), "\"gn\":%.9g,\"cal\":0}", f.gn);
      VERIFICAR(strstr(json, gn) != 0, "epoca %u: payload sem %s: %s", e, gn, json);
      VERIFICAR(strstr(json, "\"t\":31.5,") != 0, "epoca %u: temperatura do aparelho", e);
      // O vetor e o da placa: a ida e volta pela quantizacao da fila de flash.
      const FeaturesDeEpoca q =
          desquantizar(quantizar(f), static_cast<uint16_t>(AMOSTRAS_NA_GRADE));
      char vetor[160];
      snprintf(vetor, sizeof(vetor), "\"f\":[%.9g,%.9g,%.9g,%.9g,%.9g,%.9g]", q.enmo_media,
               q.enmo_desvio, q.enmo_max, q.mag_din_media, q.zcr, q.p_frac);
      VERIFICAR(strstr(json, vetor) != 0, "epoca %u: o vetor nao e o quantizado da placa: %s", e,
                json);
      VERIFICAR(n == strlen(json), "epoca %u: escritos %u, strlen %u", e, n,
                static_cast<unsigned>(strlen(json)));
    }
  }
  for (uint32_t e = 0; e < c.n_epocas; e++) {
    VERIFICAR(fechada[e], "[%.1f Hz, jitter %.0f us] a epoca %u nunca fechou", c.fs_real_hz,
              jitter_us, e);
  }
  VERIFICAR(coletor.amostras_fora_de_ordem() == 0, "jitter desordenou amostras");
}

static void rodar_dourado(const char *caminho) {
  uint32_t tamanho = 0;
  char *texto = dormio::testes::ler_arquivo_inteiro(caminho, &tamanho);
  VERIFICAR(texto != 0, "nao abriu %s -- o dourado e gravado pela suite do ml/", caminho);
  if (texto == 0) return;

  LeitorJson l(texto);
  Tolerancias tol;
  memset(&tol, 0, sizeof(tol));
  uint32_t casos = 0;
  static Caso caso;
  char k[48];
  l.entrar_objeto();
  while (!l.erro() && l.proxima_chave(k, sizeof(k))) {
    if (strcmp(k, "tolerancias") == 0) {
      l.entrar_objeto();
      char t[48];
      while (l.proxima_chave(t, sizeof(t))) {
        if (strcmp(t, "enmo_abs_g") == 0) l.ler_numero(&tol.enmo_abs_g);
        else if (strcmp(t, "enmo_max_abs_g") == 0) l.ler_numero(&tol.enmo_max_abs_g);
        else if (strcmp(t, "mag_din_rel") == 0) l.ler_numero(&tol.mag_din_rel);
        else if (strcmp(t, "zcr_cruzamentos") == 0) l.ler_numero(&tol.zcr_cruzamentos);
        else if (strcmp(t, "p_frac_amostras") == 0) l.ler_numero(&tol.p_frac_amostras);
        else if (strcmp(t, "g_angulo_graus") == 0) l.ler_numero(&tol.g_angulo_graus);
        else l.pular_valor();
      }
    } else if (strcmp(k, "casos") == 0) {
      VERIFICAR(tol.enmo_abs_g > 0 && tol.mag_din_rel > 0,
                "tolerancias tem de vir antes dos casos");
      l.entrar_array();
      while (l.proximo_elemento()) {
        if (!ler_caso(l, &caso)) break;
        casos++;
        printf("  caso %.0f: %.1f Hz, %u amostras, %u epocas\n", caso.seed, caso.fs_real_hz,
               caso.n_amostras, caso.n_epocas);
        conferir_reconstrucao(caso);
        rodar_caso(caso, tol, 0.0);
        // Carimbo de celular real tem jitter de milissegundos; a regressao da
        // linha do tempo tem de absorve-lo.
        rodar_caso(caso, tol, 2000.0);
      }
    } else {
      l.pular_valor();
    }
  }
  VERIFICAR(!l.erro(), "JSON do dourado: %s (posicao %u)", l.mensagem(), l.posicao());
  VERIFICAR(casos == 4, "esperava 4 casos, li %u", casos);
  dormio::testes::liberar_arquivo(texto);
  printf("  piso do celular: enmo %.2e g, enmo_max %.2e g, mag_din %.2f %%, zcr %.0f, "
         "p_frac %.0f, g %.4f grau\n",
         pior[0] > pior[1] ? pior[0] : pior[1], pior[2], 100.0 * pior[3], pior[4], pior[5],
         pior_ang);
}

// ── Casos que o dourado nao cobre ──────────────────────────────────────────

// O sinal sintetico comeca antes da origem, como o app faz
// (`ANTECEDENCIA_DA_ORIGEM_US`): sem isso a epoca 0 sai recusada, e com razao.
static const double INICIO_SINTETICO_S = ANTECEDENCIA_DA_ORIGEM_US / 1e6;

// Um sinal parado com um balanco pequeno, em m/s^2, a `fs` Hz.
static void alimentar(ColetorCelular *c, uint64_t origem, double ini_s, double fim_s, double fs,
                      uint32_t *payloads, uint32_t *recusadas) {
  static char json[TAMANHO_DO_PAYLOAD];
  for (double t = ini_s; t < fim_s; t += 1.0 / fs) {
    const double ang = 0.05 * sin(2.0 * 3.141592653589793 * 0.3 * t);
    c->amostrar(static_cast<uint64_t>(static_cast<int64_t>(origem) + llround(t * 1e6)),
                static_cast<float>(G_PADRAO_MS2 * sin(ang)), 0.0f,
                static_cast<float>(G_PADRAO_MS2 * cos(ang)));
    for (;;) {
      uint32_t n = 0;
      const ResultadoDoColetor r = c->proximo(json, sizeof(json), &n);
      if (r == COLETOR_NADA) break;
      if (r == COLETOR_PAYLOAD) (*payloads)++;
      if (r == COLETOR_EPOCA_RECUSADA) (*recusadas)++;
    }
  }
}

static void testar_taxa_fora_da_faixa() {
  static ColetorCelular c;
  const uint64_t origem = 50000000u;
  c.iniciar(origem, parede_de_teste(origem));
  uint32_t p = 0, r = 0;
  alimentar(&c, origem, -INICIO_SINTETICO_S, 95.0, 100.0, &p, &r);
  VERIFICAR(p == 0, "a 100 Hz saiu payload (%u): a cadeia so aceita 40 a 60 Hz", p);
  VERIFICAR(r >= 2 && c.recusadas_por_taxa() == r,
            "a 100 Hz: %u recusadas, %u por taxa", r, c.recusadas_por_taxa());

  c.iniciar(origem, parede_de_teste(origem));
  p = r = 0;
  alimentar(&c, origem, -INICIO_SINTETICO_S, 95.0, 50.0, &p, &r);
  VERIFICAR(p >= 2 && r == 0, "a 50 Hz: %u payloads, %u recusadas", p, r);
  VERIFICAR(fabs(c.ultima_taxa_hz() - 50.0) < 0.05, "taxa medida %.4f Hz", c.ultima_taxa_hz());
}

static void testar_fora_de_ordem() {
  static ColetorCelular c;
  const uint64_t origem = 50000000u;
  c.iniciar(origem, parede_de_teste(origem));
  c.amostrar(origem + 1000, 0, 0, G_PADRAO_MS2);
  c.amostrar(origem + 1000, 0, 0, G_PADRAO_MS2);  // repetida
  c.amostrar(origem + 500, 0, 0, G_PADRAO_MS2);   // para tras
  c.amostrar(origem + 21000, 0, 0, G_PADRAO_MS2);
  VERIFICAR(c.amostras_fora_de_ordem() == 2 && c.amostras_recebidas() == 2,
            "fora de ordem %u, recebidas %llu", c.amostras_fora_de_ordem(),
            static_cast<unsigned long long>(c.amostras_recebidas()));
}

static void testar_buraco() {
  // O sistema parou o sensor por 5 minutos no meio da noite. As epocas do
  // buraco nao viram payload, e as de depois voltam a fechar.
  static ColetorCelular c;
  const uint64_t origem = 50000000u;
  c.iniciar(origem, parede_de_teste(origem));
  uint32_t p_antes = 0, r_antes = 0, p_depois = 0, r_depois = 0;
  alimentar(&c, origem, -INICIO_SINTETICO_S, 95.0, 50.0, &p_antes, &r_antes);
  alimentar(&c, origem, 395.0, 520.0, 50.0, &p_depois, &r_depois);
  VERIFICAR(r_antes == 0 && p_antes >= 2, "antes do buraco: %u payloads, %u recusadas", p_antes,
            r_antes);
  VERIFICAR(r_depois >= 9, "o buraco de 300 s tem de recusar ~10 epocas, recusou %u", r_depois);
  VERIFICAR(p_depois >= 2, "depois do buraco nenhuma epoca voltou a fechar (%u)", p_depois);
  VERIFICAR(c.recusadas_por_taxa() == 0,
            "o buraco recusa por falta de amostras, nao por taxa: %u por taxa",
            c.recusadas_por_taxa());
  VERIFICAR(c.epocas_com_payload() + c.epocas_recusadas() + c.epocas_sem_payload() ==
                p_antes + p_depois + r_antes + r_depois,
            "contadores nao fecham");
}

static void testar_quantizacao() {
  VERIFICAR(g_para_lsb(1.0f) == 4096, "1 g = %d LSB", g_para_lsb(1.0f));
  VERIFICAR(g_para_lsb(-0.5f) == -2048, "-0,5 g = %d LSB", g_para_lsb(-0.5f));
  VERIFICAR(g_para_lsb(9.0f) == 32767, "acima de 8 g satura: %d", g_para_lsb(9.0f));
  VERIFICAR(g_para_lsb(-9.0f) == -32768, "abaixo de -8 g satura: %d", g_para_lsb(-9.0f));
  VERIFICAR(g_para_lsb(NAN) == 0, "NaN vira 0: %d", g_para_lsb(NAN));
  VERIFICAR(g_para_lsb(1.6f / 4096.0f) == 2 && g_para_lsb(-1.6f / 4096.0f) == -2,
            "arredonda ao LSB mais proximo, nao trunca: %d, %d", g_para_lsb(1.6f / 4096.0f),
            g_para_lsb(-1.6f / 4096.0f));
}

// CAL-03: o celular parado de tela para baixo, com o erro do eixo z do Moto
// E7 medido na bancada (escala +1,17 %, desvio -7,6 mg). Sem calibracao, a
// norma da 1,019 g e o ENMO le ~19 mg de movimento que nao existe; com a
// calibracao inversa, a norma volta a 1 g e o ENMO a zero.
static const double ESCALA_Z = 1.0117;
static const double DESVIO_Z_G = -0.0076;

static void alimentar_parado(ColetorCelular *c, uint64_t origem, double fim_s, char *ultimo,
                             uint32_t *payloads) {
  static char json[TAMANHO_DO_PAYLOAD];
  const float z = static_cast<float>(G_PADRAO_MS2 * (ESCALA_Z * -1.0 + DESVIO_Z_G));
  for (double t = -INICIO_SINTETICO_S; t < fim_s; t += 1.0 / 50.0) {
    c->amostrar(static_cast<uint64_t>(static_cast<int64_t>(origem) + llround(t * 1e6)), 0.0f,
                0.0f, z);
    for (;;) {
      uint32_t n = 0;
      const ResultadoDoColetor r = c->proximo(json, sizeof(json), &n);
      if (r == COLETOR_NADA) break;
      if (r == COLETOR_PAYLOAD) {
        (*payloads)++;
        memcpy(ultimo, json, n + 1);
      }
    }
  }
}

static void testar_calibracao() {
  static ColetorCelular c;
  static char ultimo[TAMANHO_DO_PAYLOAD];
  const uint64_t origem = 70000000u;

  c.iniciar(origem, parede_de_teste(origem));
  uint32_t p = 0;
  alimentar_parado(&c, origem, 65.0, ultimo, &p);
  VERIFICAR(p >= 2 && c.ultima_teve_features(), "sem calibracao: %u payloads", p);
  const double enmo_sem = c.ultimas_features().enmo_media;
  const double gn_sem = c.ultimas_features().gn;
  VERIFICAR(enmo_sem > 0.015, "sem calibracao o ENMO parado devia ler o erro: %.4f g", enmo_sem);
  VERIFICAR(fabs(gn_sem - (ESCALA_Z - DESVIO_Z_G)) < 0.001, "gn sem calibracao %.5f", gn_sem);
  VERIFICAR(strstr(ultimo, "\"cal\":0}") != 0, "sem calibracao o payload diz cal 0: %s", ultimo);

  Calibracao cal;
  cal.aceita = true;
  cal.modos[2] = EIXO_COMPLETO;
  cal.escala[2] = 1.0 / ESCALA_Z;
  cal.desvio[2] = -DESVIO_Z_G / ESCALA_Z;
  c.iniciar(origem, parede_de_teste(origem));
  c.definir_calibracao(cal);
  p = 0;
  alimentar_parado(&c, origem, 65.0, ultimo, &p);
  VERIFICAR(p >= 2 && c.ultima_teve_features(), "com calibracao: %u payloads", p);
  const double enmo_com = c.ultimas_features().enmo_media;
  const double gn_com = c.ultimas_features().gn;
  VERIFICAR(enmo_com < 0.0005, "com calibracao o ENMO parado devia ser ~0: %.5f g", enmo_com);
  VERIFICAR(fabs(gn_com - 1.0) < 0.0005, "gn com calibracao %.5f", gn_com);
  VERIFICAR(strstr(ultimo, "\"cal\":1}") != 0, "com calibracao o payload diz cal 1: %s", ultimo);

  // Uma calibracao recusada nao mexe: o mesmo ENMO de sem calibracao.
  cal.aceita = false;
  c.iniciar(origem, parede_de_teste(origem));
  c.definir_calibracao(cal);
  p = 0;
  alimentar_parado(&c, origem, 65.0, ultimo, &p);
  VERIFICAR(fabs(c.ultimas_features().enmo_media - enmo_sem) < 1e-12,
            "calibracao recusada mexeu no ENMO: %.6f contra %.6f", c.ultimas_features().enmo_media,
            enmo_sem);
  VERIFICAR(strstr(ultimo, "\"cal\":0}") != 0, "recusada: o payload diz cal 0: %s", ultimo);

  // Etapa 2: a epoca parada e um ponto de calibracao, e o ponto vem no BRUTO
  // mesmo quando a noite saiu calibrada -- e o que a proxima estimativa usa.
  double ponto[4];
  cal.aceita = true;
  c.iniciar(origem, parede_de_teste(origem));
  c.definir_calibracao(cal);
  // DATA-14: o ponto so existe com a temperatura informada (o app a informa
  // antes da primeira amostra). Ate 13/11 este teste contava com os 25,0 C
  // que o coletor inventava sozinho.
  c.definir_temperatura(25.0f);
  p = 0;
  alimentar_parado(&c, origem, 65.0, ultimo, &p);
  VERIFICAR(c.ponto_parado(ponto), "a epoca parada calibrada nao deu ponto");
  const double bruto_z = ESCALA_Z * -1.0 + DESVIO_Z_G;
  VERIFICAR(fabs(ponto[2] - bruto_z) < 0.0005 && fabs(ponto[0]) < 1e-3 && fabs(ponto[1]) < 1e-3,
            "o ponto devia ser o bruto (0, 0, %.4f): (%.5f, %.5f, %.5f)", bruto_z, ponto[0],
            ponto[1], ponto[2]);
  VERIFICAR(ponto[3] == 25.0, "o ponto leva a temperatura da noite: %.2f", ponto[3]);
  // Uma epoca em movimento nao e ponto: o sinal do `testar_taxa_fora_da_faixa`
  // balanca 0,05 rad a 0,3 Hz, bem acima dos 10 mg de movimento dinamico.
  {
    static ColetorCelular m;
    m.iniciar(origem, parede_de_teste(origem));
    // Com a temperatura informada: sem ela, a trava do DATA-14 tambem
    // impediria o ponto, e o teste deixaria de exercitar a regra do
    // movimento (medido em 13/11: a sabotagem do movimento passou).
    m.definir_temperatura(25.0f);
    uint32_t pm = 0, rm = 0;
    alimentar(&m, origem, -INICIO_SINTETICO_S, 65.0, 50.0, &pm, &rm);
    VERIFICAR(pm >= 2 && m.ultima_teve_features(), "em movimento: %u payloads", pm);
    VERIFICAR(m.ultimas_features().mag_din_media >= LIMIAR_PARADO_G,
              "o sinal de teste devia ser movimento: %.4f g", m.ultimas_features().mag_din_media);
    VERIFICAR(!m.ponto_parado(ponto), "epoca em movimento virou ponto de calibracao");
  }
  printf("  calibracao: ENMO parado %.2f mg -> %.3f mg, gn %.4f -> %.5f g\n", 1000.0 * enmo_sem,
         1000.0 * enmo_com, gn_sem, gn_com);
}

// DATA-14 (13/11): sem `definir_temperatura`, a temperatura e desconhecida.
// O payload sai SEM `t` (e JSON valido: nada de "nan"), e nenhuma epoca parada
// vira ponto de calibracao -- ate 13/11 o coletor inventava 25,0 C e mandava
// isso como medida.
static void testar_temperatura_desconhecida() {
  printf("\n-- temperatura desconhecida (DATA-14) --\n");
  static ColetorCelular c;
  static char ultimo[TAMANHO_DO_PAYLOAD];
  const uint64_t origem = 70000000u;
  c.iniciar(origem, parede_de_teste(origem));
  Calibracao cal;
  cal.aceita = true;
  cal.modos[2] = EIXO_COMPLETO;
  cal.escala[2] = 1.0 / ESCALA_Z;
  cal.desvio[2] = -DESVIO_Z_G / ESCALA_Z;
  c.definir_calibracao(cal);
  uint32_t p = 0;
  alimentar_parado(&c, origem, 65.0, ultimo, &p);
  VERIFICAR(p >= 2, "sem temperatura: %u payloads (a medicao nao pode parar por isso)", p);
  VERIFICAR(strstr(ultimo, "\"t\":") == 0, "sem temperatura o payload nao leva t: %s", ultimo);
  VERIFICAR(strstr(ultimo, "nan") == 0 && strstr(ultimo, "inf") == 0,
            "sem temperatura o payload nao pode ter nan/inf: %s", ultimo);
  VERIFICAR(strstr(ultimo, "\"az\":") != 0 && strstr(ultimo, ",\"total\":") != 0,
            "sem t o resto do payload segue no lugar: %s", ultimo);
  double ponto[4];
  VERIFICAR(!c.ponto_parado(ponto), "sem temperatura nao pode haver ponto de calibracao");

  // Informada depois, ela entra no payload seguinte e o ponto volta a existir.
  c.iniciar(origem, parede_de_teste(origem));
  c.definir_calibracao(cal);
  c.definir_temperatura(30.5f);
  p = 0;
  alimentar_parado(&c, origem, 65.0, ultimo, &p);
  VERIFICAR(strstr(ultimo, "\"t\":30.5,") != 0, "informada, a temperatura entra: %s", ultimo);
  VERIFICAR(c.ponto_parado(ponto) && ponto[3] == 30.5, "informada, o ponto volta: %.2f", ponto[3]);
}

int main(int argc, char **argv) {
  printf("Coletor do celular contra o dourado da C2 -- APP-02\n");
  printf("===================================================\n");
  printf("memoria do coletor: %u bytes (%.1f KiB)\n",
         static_cast<unsigned>(sizeof(ColetorCelular)),
         static_cast<double>(sizeof(ColetorCelular)) / 1024.0);
  const char *caminho = (argc > 1) ? argv[1] : "../../ml/testes/vetor_dourado_cadeia_c2.json";
  rodar_dourado(caminho);
  testar_taxa_fora_da_faixa();
  testar_fora_de_ordem();
  testar_buraco();
  testar_quantizacao();
  testar_calibracao();
  testar_temperatura_desconhecida();
  printf("\n-----------------------------------------\n");
  printf("%d verificacoes, %d falhas\n", total, falhas);
  return falhas == 0 ? 0 : 1;
}
