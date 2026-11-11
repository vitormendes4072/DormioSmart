// testes_calibracao.cpp -- a autocalibracao (CAL-03) contra o dourado do ml/.
//
// Le `ml/testes/dourado_calibracao.json`, gravado por
// `ml/testes/test_calibracao.py` com a referencia `ml/src/calibracao.py`. Para
// cada caso (esfera, deitado, so para cima, ruidoso, poucos pontos), estima a
// calibracao com os MESMOS pontos e confere: se aceitou, os modos, se usou a
// temperatura, os nove parametros, o erro antes e depois, e tres amostras de
// conferencia calibradas por `aplicar_calibracao`.
//
// A tolerancia e de conta, nao de metodo: os dois lados resolvem as mesmas
// equacoes normais em double, e a diferenca e de arredondamento (a soma do
// numpy e em pares, a daqui e sequencial). 1e-8 fica muito acima dela e muito
// abaixo de qualquer sabotagem (`verificar_calibracao_por_mutacao.sh`).

#include <math.h>
#include <stdio.h>
#include <string.h>

#include "../calibracao.h"
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

static const double TOL = 1e-8;
static const uint32_t MAX_PONTOS = 512;

struct Esperado {
  bool aceita, usou_temperatura;
  uint8_t modos[3];
  double desvio[3], escala[3], coef_temp[3], temp_ref_c, erro_antes_g, erro_depois_g;
};

struct Caso {
  char nome[32];
  double pontos[MAX_PONTOS][3];
  double temp_c[MAX_PONTOS];
  uint32_t n, n_temp;
  Esperado esperado;
  double conferir[3][3], conferir_temp_c[3], conferir_calibrado[3][3];
};

static uint8_t modo_de(const char *s) {
  if (strcmp(s, "completo") == 0) return EIXO_COMPLETO;
  if (strcmp(s, "desvio") == 0) return EIXO_DESVIO;
  return EIXO_FIXO;
}

static bool ler_matriz3(LeitorJson &l, double m[][3], uint32_t maximo, uint32_t *n) {
  *n = 0;
  if (!l.entrar_array()) return false;
  while (l.proximo_elemento()) {
    if (*n >= maximo || !l.ler_array_de_numeros(m[*n], 3)) return false;
    (*n)++;
  }
  return true;
}

static bool ler_vetor(LeitorJson &l, double *v, uint32_t maximo, uint32_t *n) {
  *n = 0;
  if (!l.entrar_array()) return false;
  while (l.proximo_elemento()) {
    if (*n >= maximo || !l.ler_numero(&v[*n])) return false;
    (*n)++;
  }
  return true;
}

static bool ler_esperado(LeitorJson &l, Esperado *e) {
  char k[32];
  if (!l.entrar_objeto()) return false;
  while (l.proxima_chave(k, sizeof(k))) {
    if (strcmp(k, "aceita") == 0) {
      l.ler_booleano(&e->aceita);
    } else if (strcmp(k, "usou_temperatura") == 0) {
      l.ler_booleano(&e->usou_temperatura);
    } else if (strcmp(k, "modos") == 0) {
      l.entrar_array();
      int i = 0;
      while (l.proximo_elemento()) {
        char s[16];
        l.ler_string(s, sizeof(s));
        if (i < 3) e->modos[i] = modo_de(s);
        i++;
      }
    } else if (strcmp(k, "desvio") == 0) {
      l.ler_array_de_numeros(e->desvio, 3);
    } else if (strcmp(k, "escala") == 0) {
      l.ler_array_de_numeros(e->escala, 3);
    } else if (strcmp(k, "coef_temp") == 0) {
      l.ler_array_de_numeros(e->coef_temp, 3);
    } else if (strcmp(k, "temp_ref_c") == 0) {
      l.ler_numero(&e->temp_ref_c);
    } else if (strcmp(k, "erro_antes_g") == 0) {
      l.ler_numero(&e->erro_antes_g);
    } else if (strcmp(k, "erro_depois_g") == 0) {
      l.ler_numero(&e->erro_depois_g);
    } else {
      l.pular_valor();
    }
  }
  return !l.erro();
}

static bool ler_caso(LeitorJson &l, Caso *c) {
  char k[32];
  memset(c, 0, sizeof(*c));
  if (!l.entrar_objeto()) return false;
  while (l.proxima_chave(k, sizeof(k))) {
    uint32_t n = 0;
    if (strcmp(k, "nome") == 0) {
      l.ler_string(c->nome, sizeof(c->nome));
    } else if (strcmp(k, "pontos") == 0) {
      if (!ler_matriz3(l, c->pontos, MAX_PONTOS, &c->n)) return false;
    } else if (strcmp(k, "temp_c") == 0) {
      if (!ler_vetor(l, c->temp_c, MAX_PONTOS, &c->n_temp)) return false;
    } else if (strcmp(k, "esperado") == 0) {
      if (!ler_esperado(l, &c->esperado)) return false;
    } else if (strcmp(k, "conferir") == 0) {
      if (!ler_matriz3(l, c->conferir, 3, &n)) return false;
    } else if (strcmp(k, "conferir_temp_c") == 0) {
      if (!ler_vetor(l, c->conferir_temp_c, 3, &n)) return false;
    } else if (strcmp(k, "conferir_calibrado") == 0) {
      if (!ler_matriz3(l, c->conferir_calibrado, 3, &n)) return false;
    } else {
      l.pular_valor();
    }
  }
  return !l.erro();
}

static bool perto(double a, double b) { return fabs(a - b) <= TOL; }

static void conferir(const Caso &c) {
  const Esperado &e = c.esperado;
  VERIFICAR(c.n == c.n_temp, "[%s] %u pontos e %u temperaturas", c.nome, c.n, c.n_temp);
  const Calibracao r = estimar_calibracao(c.pontos, c.temp_c, c.n);

  VERIFICAR(r.aceita == e.aceita, "[%s] aceita %d, esperado %d", c.nome, r.aceita, e.aceita);
  VERIFICAR(r.usou_temperatura == e.usou_temperatura, "[%s] usou_temperatura %d, esperado %d",
            c.nome, r.usou_temperatura, e.usou_temperatura);
  for (int k = 0; k < 3; k++) {
    VERIFICAR(r.modos[k] == e.modos[k], "[%s] modo do eixo %d: %u, esperado %u", c.nome, k,
              r.modos[k], e.modos[k]);
    VERIFICAR(perto(r.desvio[k], e.desvio[k]), "[%s] desvio %d: %.12g, esperado %.12g", c.nome, k,
              r.desvio[k], e.desvio[k]);
    VERIFICAR(perto(r.escala[k], e.escala[k]), "[%s] escala %d: %.12g, esperado %.12g", c.nome, k,
              r.escala[k], e.escala[k]);
    VERIFICAR(perto(r.coef_temp[k], e.coef_temp[k]), "[%s] coef_temp %d: %.12g, esperado %.12g",
              c.nome, k, r.coef_temp[k], e.coef_temp[k]);
  }
  // A referencia so calcula temp_ref e os erros quando passa da contagem
  // minima; abaixo dela os dois lados ficam em zero.
  VERIFICAR(perto(r.temp_ref_c, e.temp_ref_c), "[%s] temp_ref %.12g, esperado %.12g", c.nome,
            r.temp_ref_c, e.temp_ref_c);
  VERIFICAR(perto(r.erro_antes_g, e.erro_antes_g), "[%s] erro antes %.12g, esperado %.12g",
            c.nome, r.erro_antes_g, e.erro_antes_g);
  VERIFICAR(perto(r.erro_depois_g, e.erro_depois_g), "[%s] erro depois %.12g, esperado %.12g",
            c.nome, r.erro_depois_g, e.erro_depois_g);

  for (int i = 0; i < 3; i++) {
    double cal[3], volta[3];
    aplicar_calibracao(r, c.conferir_temp_c[i], c.conferir[i], cal);
    desfazer_calibracao(r, c.conferir_temp_c[i], cal, volta);
    for (int k = 0; k < 3; k++) {
      VERIFICAR(perto(cal[k], c.conferir_calibrado[i][k]),
                "[%s] amostra %d eixo %d: %.12g, esperado %.12g", c.nome, i, k, cal[k],
                c.conferir_calibrado[i][k]);
      VERIFICAR(fabs(volta[k] - c.conferir[i][k]) < 1e-12, "[%s] desfazer nao volta: %.15g",
                c.nome, volta[k]);
    }
  }
  printf("  %-14s aceita %d  modos %u%u%u  temp %d  erro %.3f -> %.3f mg\n", c.nome, r.aceita,
         r.modos[0], r.modos[1], r.modos[2], r.usou_temperatura, 1000.0 * r.erro_antes_g,
         1000.0 * r.erro_depois_g);
}

static void rodar(const char *caminho) {
  uint32_t tamanho = 0;
  char *texto = dormio::testes::ler_arquivo_inteiro(caminho, &tamanho);
  VERIFICAR(texto != 0, "nao abriu %s -- o dourado e gravado pela suite do ml/", caminho);
  if (texto == 0) return;

  LeitorJson l(texto);
  static Caso caso;
  uint32_t casos = 0;
  char k[32];
  l.entrar_objeto();
  while (!l.erro() && l.proxima_chave(k, sizeof(k))) {
    if (strcmp(k, "casos") == 0) {
      l.entrar_array();
      while (l.proximo_elemento()) {
        if (!ler_caso(l, &caso)) break;
        conferir(caso);
        casos++;
      }
    } else {
      l.pular_valor();
    }
  }
  VERIFICAR(!l.erro(), "JSON invalido: %s (posicao %u)", l.mensagem(), l.posicao());
  VERIFICAR(casos == 5, "%u casos no dourado, esperados 5", casos);
  dormio::testes::liberar_arquivo(texto);
}

// O que nao depende do dourado: a identidade nao mexe, e uma estimativa sem
// pontos nao inventa calibracao.
static void testes_proprios() {
  Calibracao id;
  const double a[3] = {0.1, -0.2, 0.97};
  double b[3];
  aplicar_calibracao(id, 30.0, a, b);
  VERIFICAR(b[0] == a[0] && b[1] == a[1] && b[2] == a[2], "a identidade mexeu na amostra");
  const Calibracao vazia = estimar_calibracao(0, 0, 0);
  VERIFICAR(!vazia.aceita, "estimativa sem pontos aceitou");
}

int main(int argc, char **argv) {
  printf("Autocalibracao contra o dourado -- CAL-03\n");
  printf("=========================================\n");
  testes_proprios();
  rodar(argc > 1 ? argv[1] : "../../ml/testes/dourado_calibracao.json");
  printf("\n-----------------------------------------\n");
  printf("%d verificacoes, %d falhas\n", total, falhas);
  return falhas == 0 ? 0 : 1;
}
