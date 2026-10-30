// testes_cadeia_c2.cpp -- a cadeia C2 inteira contra o dourado (FW-07).
//
// Le `ml/testes/vetor_dourado_cadeia_c2.json`: um registro de FIFO sintetico
// por taxa (42,5; 47; 50; 55 Hz) com as drenagens que o ESP32 teria feito.
// Para cada caso, os inteiros viram BYTES big-endian, os bytes passam por
// `decodificar_fifo`, as drenagens entram na `CadeiaC2` uma a uma -- como no
// dispositivo, com a epoca fechando quando a folga chega --, e a grade de cada
// epoca vai para o `AcumuladorDeFeatures`. Duas reguas:
//
//   EXATIDAO  contra `estilo_firmware` (a mesma conta em Python): linha do
//             tempo, indices da janela e a grade de 8 em 8 amostras. E esta
//             que pega as sabotagens (`verificar_cadeia_por_mutacao.sh`).
//   VALIDADE  contra `esperado` (o pipeline do ml/ com o tempo verdadeiro):
//             as 6 features e `g`, com tolerancias derivadas do piso medido.
//
// O porque de duas reguas esta no cabecalho de
// `ml/testes/test_dourado_cadeia_c2.py`. As tolerancias sao LIDAS do arquivo,
// como no `testes_dourado.cpp`: uma regua so, nos dois lados.

#include <math.h>
#include <stdio.h>
#include <string.h>

#include "../cadeia_c2.h"
#include "../caracteristicas.h"
#include "../fifo_mpu.h"
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
  double linha_do_tempo_s, grade_g, enmo_abs_g, enmo_max_abs_g, mag_din_rel;
  double zcr_cruzamentos, p_frac_amostras, g_angulo_graus;
};

static const uint32_t MAX_AMOSTRAS = 4096;
static const uint32_t MAX_DRENAGENS = 64;
static const uint32_t MAX_EPOCAS = 4;
static const uint32_t MAX_PONTOS_DA_GRADE = AMOSTRAS_NA_GRADE;

struct EpocaDoDourado {
  double a_s, b_s, n_drenagens, k_ini, k_fim;
  double grade[MAX_PONTOS_DA_GRADE][3];
  uint32_t n_grade;
  double esperado[6];  // ordem de FEATURES_DO_DISPOSITIVO
  double g[3];
};

struct Caso {
  double seed, fs_real_hz, origem_us;
  uint32_t n_amostras;
  int16_t lsb[MAX_AMOSTRAS][3];
  uint32_t n_drenagens;
  double drenagem_t_us[MAX_DRENAGENS];
  uint32_t drenagem_n[MAX_DRENAGENS];
  uint32_t n_epocas;
  EpocaDoDourado epocas[MAX_EPOCAS];
};

static const char *const ORDEM[6] = {"enmo_media", "enmo_desvio", "enmo_max",
                                     "mag_din_media", "zcr", "p_frac"};

// Maiores divergencias vistas, para imprimir o piso do C++ no fim.
static double pior_a = 0, pior_b = 0, pior_grade = 0, pior_ang = 0, pior_mag = 0;
static double pior_enmo = 0, pior_enmo_max = 0, pior_zcr = 0, pior_pfrac = 0;

static bool ler_epoca(LeitorJson &l, EpocaDoDourado *e) {
  char k[48];
  if (!l.entrar_objeto()) return false;
  while (l.proxima_chave(k, sizeof(k))) {
    if (strcmp(k, "estilo_firmware") == 0) {
      if (!l.entrar_objeto()) return false;
      char k2[48];
      while (l.proxima_chave(k2, sizeof(k2))) {
        if (strcmp(k2, "a_s") == 0) l.ler_numero(&e->a_s);
        else if (strcmp(k2, "b_s") == 0) l.ler_numero(&e->b_s);
        else if (strcmp(k2, "n_drenagens") == 0) l.ler_numero(&e->n_drenagens);
        else if (strcmp(k2, "k_ini") == 0) l.ler_numero(&e->k_ini);
        else if (strcmp(k2, "k_fim") == 0) l.ler_numero(&e->k_fim);
        else if (strcmp(k2, "grade_amostrada") == 0) {
          e->n_grade = 0;
          if (!l.entrar_array()) return false;
          while (l.proximo_elemento()) {
            if (e->n_grade >= MAX_PONTOS_DA_GRADE ||
                !l.ler_array_de_numeros(e->grade[e->n_grade], 3)) {
              l.falhar("grade_amostrada maior que o esperado ou malformada");
              return false;
            }
            e->n_grade++;
          }
        } else {
          l.pular_valor();
        }
        if (l.erro()) return false;
      }
    } else if (strcmp(k, "esperado") == 0) {
      if (!l.entrar_objeto()) return false;
      char k2[48];
      while (l.proxima_chave(k2, sizeof(k2))) {
        bool achou = false;
        for (int i = 0; i < 6; i++) {
          if (strcmp(k2, ORDEM[i]) == 0) {
            l.ler_numero(&e->esperado[i]);
            achou = true;
          }
        }
        if (!achou) {
          if (strcmp(k2, "g") == 0) l.ler_array_de_numeros(e->g, 3);
          else l.pular_valor();  // inclinacao_rel e d_angulo: do servidor
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
        if (c->n_epocas >= MAX_EPOCAS || !ler_epoca(l, &c->epocas[c->n_epocas])) {
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

static float grade_[MAX_EPOCAS][3][AMOSTRAS_NA_GRADE];
static EpocaReamostrada info_[MAX_EPOCAS];
static bool fechada_[MAX_EPOCAS];

static void rodar_cadeia(const Caso &c) {
  static CadeiaC2 cadeia;
  cadeia.iniciar(static_cast<uint64_t>(c.origem_us));
  for (uint32_t i = 0; i < MAX_EPOCAS; i++) fechada_[i] = false;

  uint32_t lidas = 0;
  static uint8_t bytes[FIFO_CAPACIDADE_BYTES];
  static AmostraBruta amostras[FIFO_CAPACIDADE_AMOSTRAS];
  for (uint32_t d = 0; d < c.n_drenagens; d++) {
    const uint32_t n = c.drenagem_n[d];
    // O que o sketch faria: FIFO_COUNT, avaliar, ler bytes, decodificar.
    const uint16_t contagem = static_cast<uint16_t>(n * BYTES_POR_AMOSTRA);
    VERIFICAR(avaliar_fifo(contagem, 0) == LEITURA_OK,
              "drenagem %u com %u amostras transbordaria a FIFO", d, n);
    const uint16_t a_ler = bytes_para_ler(contagem, FIFO_CAPACIDADE_BYTES);
    for (uint32_t i = 0; i < n; i++) {
      for (int eixo = 0; eixo < 3; eixo++) {
        const uint16_t v = static_cast<uint16_t>(c.lsb[lidas + i][eixo]);
        bytes[i * 6 + 2 * eixo] = static_cast<uint8_t>(v >> 8);
        bytes[i * 6 + 2 * eixo + 1] = static_cast<uint8_t>(v & 0xFF);
      }
    }
    const uint16_t m = decodificar_fifo(bytes, a_ler, amostras, FIFO_CAPACIDADE_AMOSTRAS);
    VERIFICAR(m == n, "decodificou %u de %u amostras", m, n);
    lidas += n;
    cadeia.registrar_drenagem(static_cast<uint64_t>(c.drenagem_t_us[d]), amostras, m, false);

    for (;;) {
      EpocaReamostrada info;
      const uint32_t k = cadeia.epoca_seguinte();
      float *gx = k < MAX_EPOCAS ? grade_[k][0] : 0;
      float *gy = k < MAX_EPOCAS ? grade_[k][1] : 0;
      float *gz = k < MAX_EPOCAS ? grade_[k][2] : 0;
      const ResultadoDaEpoca r = cadeia.proxima_epoca(&info, gx, gy, gz);
      if (r == EPOCA_AINDA_NAO) break;
      if (k < MAX_EPOCAS) {
        info_[k] = info;
        fechada_[k] = true;
      }
    }
  }
}

static void conferir_epoca(const Caso &c, uint32_t k, const Tolerancias &tol, uint32_t passo) {
  const EpocaDoDourado &e = c.epocas[k];
  const EpocaReamostrada &r = info_[k];
  const double fs = c.fs_real_hz;

  VERIFICAR(fechada_[k], "[%.1f Hz] a epoca %u nunca fechou", fs, k);
  if (!fechada_[k]) return;
  VERIFICAR(r.resultado == EPOCA_PRONTA, "[%.1f Hz] epoca %u recusada (%d)", fs, k,
            static_cast<int>(r.resultado));
  if (r.resultado != EPOCA_PRONTA) return;

  // ── Exatidao: a linha do tempo e a janela ──
  const double da = fabs(r.linha.a_s - e.a_s);
  // `b` pesa multiplicado pelo indice: o erro de tempo que ele causa no fim da
  // janela e |db| * k_fim.
  const double db = fabs(r.linha.b_s - e.b_s) * e.k_fim;
  if (da > pior_a) pior_a = da;
  if (db > pior_b) pior_b = db;
  VERIFICAR(da <= tol.linha_do_tempo_s, "[%.1f Hz, ep %u] a diverge %.3e s", fs, k, da);
  VERIFICAR(db <= tol.linha_do_tempo_s, "[%.1f Hz, ep %u] b diverge %.3e s no fim", fs, k, db);
  VERIFICAR(r.linha.n_drenagens == static_cast<uint32_t>(e.n_drenagens),
            "[%.1f Hz, ep %u] %u drenagens no ajuste, a referencia usou %.0f", fs, k,
            r.linha.n_drenagens, e.n_drenagens);
  VERIFICAR(r.k_ini == static_cast<int64_t>(e.k_ini) && r.k_fim == static_cast<int64_t>(e.k_fim),
            "[%.1f Hz, ep %u] janela [%lld, %lld], referencia [%.0f, %.0f]", fs, k,
            static_cast<long long>(r.k_ini), static_cast<long long>(r.k_fim), e.k_ini, e.k_fim);

  // ── Exatidao: a grade ──
  double pior = 0.0;
  for (uint32_t i = 0; i < e.n_grade; i++) {
    for (int eixo = 0; eixo < 3; eixo++) {
      const double d = fabs(static_cast<double>(grade_[k][eixo][i * passo]) - e.grade[i][eixo]);
      if (d > pior) pior = d;
    }
  }
  if (pior > pior_grade) pior_grade = pior;
  VERIFICAR(e.n_grade == AMOSTRAS_NA_GRADE / passo, "[%.1f Hz, ep %u] %u pontos de grade", fs,
            k, e.n_grade);
  VERIFICAR(pior <= tol.grade_g, "[%.1f Hz, ep %u] grade diverge %.3e g da referencia", fs, k,
            pior);

  // ── Validade: as features contra o pipeline ──
  static AcumuladorDeFeatures acc;
  acc.iniciar();
  for (uint32_t j = 0; j < AMOSTRAS_NA_GRADE; j++) {
    acc.amostrar(grade_[k][0][j], grade_[k][1][j], grade_[k][2][j]);
  }
  FeaturesDeEpoca f;
  const bool ok = acc.fechar(TAXA_DA_GRADE_HZ, &f);
  VERIFICAR(ok, "[%.1f Hz, ep %u] o acumulador recusou 960 amostras", fs, k);
  if (!ok) return;

  const double enmo[3] = {f.enmo_media, f.enmo_desvio, f.enmo_max};
  for (int i = 0; i < 3; i++) {
    const double d = fabs(enmo[i] - e.esperado[i]);
    const double t = (i == 2) ? tol.enmo_max_abs_g : tol.enmo_abs_g;
    if (i == 2 && d > pior_enmo_max) pior_enmo_max = d;
    if (i != 2 && d > pior_enmo) pior_enmo = d;
    VERIFICAR(d <= t, "[%.1f Hz, ep %u] %s diverge %.3e g (tol %.1e)", fs, k, ORDEM[i], d, t);
  }
  const double rel = fabs(f.mag_din_media - e.esperado[3]) / e.esperado[3];
  if (rel > pior_mag) pior_mag = rel;
  VERIFICAR(rel <= tol.mag_din_rel, "[%.1f Hz, ep %u] mag_din_media diverge %.2f %%", fs, k,
            100.0 * rel);
  const double zcr = fabs(f.zcr - e.esperado[4]) * (AMOSTRAS_NA_GRADE - 1);
  if (zcr > pior_zcr) pior_zcr = zcr;
  VERIFICAR(zcr <= tol.zcr_cruzamentos + 1e-9, "[%.1f Hz, ep %u] zcr diverge %.1f cruzamentos",
            fs, k, zcr);
  const double pf = fabs(f.p_frac - e.esperado[5]) * AMOSTRAS_NA_GRADE;
  if (pf > pior_pfrac) pior_pfrac = pf;
  VERIFICAR(pf <= tol.p_frac_amostras + 1e-9, "[%.1f Hz, ep %u] p_frac diverge %.1f amostras",
            fs, k, pf);
  double dot = f.gx * e.g[0] + f.gy * e.g[1] + f.gz * e.g[2];
  if (dot > 1.0) dot = 1.0;
  const double ang = acos(dot) * 180.0 / 3.141592653589793;
  if (ang > pior_ang) pior_ang = ang;
  VERIFICAR(ang <= tol.g_angulo_graus, "[%.1f Hz, ep %u] g diverge %.4f grau", fs, k, ang);
}

static void rodar(const char *caminho) {
  uint32_t tamanho = 0;
  char *texto = dormio::testes::ler_arquivo_inteiro(caminho, &tamanho);
  VERIFICAR(texto != 0, "nao abriu %s -- o dourado e gravado pela suite do ml/", caminho);
  if (texto == 0) return;

  LeitorJson l(texto);
  Tolerancias tol;
  memset(&tol, 0, sizeof(tol));
  double passo = 0;
  uint32_t casos = 0;
  static Caso caso;
  char k[48];

  l.entrar_objeto();
  while (!l.erro() && l.proxima_chave(k, sizeof(k))) {
    double v = 0;
    // As constantes do arquivo tem de ser as compiladas: um corte ou uma
    // margem diferentes entre os lados nao apareceriam como erro obvio, e sim
    // como uma divergencia de grade "um pouco maior".
    if (strcmp(k, "lsb_por_g") == 0) {
      l.ler_numero(&v);
      VERIFICAR(v == LSB_POR_G, "lsb_por_g %.1f no arquivo", v);
    } else if (strcmp(k, "taxa_nominal_hz") == 0) {
      l.ler_numero(&v);
      VERIFICAR(v == TAXA_NOMINAL_C2_HZ, "taxa nominal %.3f no arquivo", v);
    } else if (strcmp(k, "taxa_da_grade_hz") == 0) {
      l.ler_numero(&v);
      VERIFICAR(v == TAXA_DA_GRADE_HZ, "grade %.3f Hz no arquivo", v);
    } else if (strcmp(k, "corte_antialiasing_hz") == 0) {
      l.ler_numero(&v);
      VERIFICAR(fabs(v - CORTE_ANTIALIASING_HZ) < 1e-6, "corte %.6f Hz no arquivo", v);
    } else if (strcmp(k, "duracao_epoca_s") == 0) {
      l.ler_numero(&v);
      VERIFICAR(v == DURACAO_EPOCA_C2_S, "epoca de %.1f s no arquivo", v);
    } else if (strcmp(k, "margem_s") == 0) {
      l.ler_numero(&v);
      VERIFICAR(v == MARGEM_S, "margem de %.3f s no arquivo", v);
    } else if (strcmp(k, "folga_do_ajuste_s") == 0) {
      l.ler_numero(&v);
      VERIFICAR(v == FOLGA_DO_AJUSTE_S, "folga de %.3f s no arquivo", v);
    } else if (strcmp(k, "minimo_de_drenagens") == 0) {
      l.ler_numero(&v);
      VERIFICAR(v == MINIMO_DE_DRENAGENS, "minimo de %.0f drenagens no arquivo", v);
    } else if (strcmp(k, "passo_da_grade_amostrada") == 0) {
      l.ler_numero(&passo);
    } else if (strcmp(k, "tolerancias") == 0) {
      l.entrar_objeto();
      char t[48];
      while (l.proxima_chave(t, sizeof(t))) {
        if (strcmp(t, "linha_do_tempo_s") == 0) l.ler_numero(&tol.linha_do_tempo_s);
        else if (strcmp(t, "grade_g") == 0) l.ler_numero(&tol.grade_g);
        else if (strcmp(t, "enmo_abs_g") == 0) l.ler_numero(&tol.enmo_abs_g);
        else if (strcmp(t, "enmo_max_abs_g") == 0) l.ler_numero(&tol.enmo_max_abs_g);
        else if (strcmp(t, "mag_din_rel") == 0) l.ler_numero(&tol.mag_din_rel);
        else if (strcmp(t, "zcr_cruzamentos") == 0) l.ler_numero(&tol.zcr_cruzamentos);
        else if (strcmp(t, "p_frac_amostras") == 0) l.ler_numero(&tol.p_frac_amostras);
        else if (strcmp(t, "g_angulo_graus") == 0) l.ler_numero(&tol.g_angulo_graus);
        else l.pular_valor();
      }
    } else if (strcmp(k, "casos") == 0) {
      VERIFICAR(tol.grade_g > 0 && tol.linha_do_tempo_s > 0 && passo > 0,
                "tolerancias e passo tem de vir antes dos casos");
      l.entrar_array();
      while (l.proximo_elemento()) {
        if (!ler_caso(l, &caso)) break;
        casos++;
        printf("\n  caso %.0f: %.1f Hz, %u amostras, %u drenagens, %u epocas\n", caso.seed,
               caso.fs_real_hz, caso.n_amostras, caso.n_drenagens, caso.n_epocas);
        rodar_cadeia(caso);
        for (uint32_t e = 0; e < caso.n_epocas; e++) {
          conferir_epoca(caso, e, tol, static_cast<uint32_t>(passo));
          printf("    epoca %u: %.4f Hz medidos, janela [%lld, %lld]\n", e,
                 1.0 / info_[e].linha.b_s, static_cast<long long>(info_[e].k_ini),
                 static_cast<long long>(info_[e].k_fim));
        }
      }
    } else {
      l.pular_valor();
    }
  }
  VERIFICAR(!l.erro(), "JSON do dourado: %s (posicao %u)", l.mensagem(), l.posicao());
  VERIFICAR(casos == 4, "esperava 4 casos (uma taxa cada), li %u", casos);
  dormio::testes::liberar_arquivo(texto);

  printf("\n  piso do C++ (maior divergencia vista):\n");
  printf("    EXATIDAO  a %.2e s   b*k_fim %.2e s   grade %.2e g\n", pior_a, pior_b, pior_grade);
  printf("    VALIDADE  enmo %.2e g   enmo_max %.2e g   mag_din %.2f %%   zcr %.0f   p_frac %.0f"
         "   g %.4f grau\n",
         pior_enmo, pior_enmo_max, 100.0 * pior_mag, pior_zcr, pior_pfrac, pior_ang);
}

int main(int argc, char **argv) {
  printf("Cadeia C2 contra o dourado -- FW-07\n");
  printf("===================================\n");
  printf("memoria da cadeia: %u bytes (%.1f KiB)\n", static_cast<unsigned>(sizeof(CadeiaC2)),
         static_cast<double>(sizeof(CadeiaC2)) / 1024.0);
  const char *caminho = (argc > 1) ? argv[1] : "../../ml/testes/vetor_dourado_cadeia_c2.json";
  rodar(caminho);
  printf("\n-----------------------------------------\n");
  printf("%d verificacoes, %d falhas\n", total, falhas);
  return falhas == 0 ? 0 : 1;
}
