// testes_dourado.cpp -- A PROVA DE PARIDADE: C++ contra o vetor dourado.
//
// Este e o alvo que faltava. Ate aqui o `DATA-07c` havia deixado o registro
// explicito de que "a paridade continua garantida de um lado so: enquanto o
// firmware nao consumir o JSON, o dourado e uma especificacao que ninguem
// leu". Este arquivo e quem le.
//
// ── O QUE E CONFERIDO, E O QUE DELIBERADAMENTE NAO E ──────────────────
//
// CONFERIDO: as 6 features intra-epoca e o vetor `g`, por caso do dourado.
//
// NAO CONFERIDO: `inclinacao_rel` e `d_angulo`. Elas estao no arquivo (valendo
// 0, porque cada caso tem uma epoca so) e o firmware **nao as calcula nem
// deve**. Sao derivadas no SERVIDOR, a partir de `g`, sobre a noite inteira:
// `g_ref` e a mediana geometrica de todas as epocas, e quando o dispositivo
// envia a epoca 12 as epocas 13..960 ainda nao existem. Qualquer estimativa
// incremental no firmware seria um ESTIMADOR DIFERENTE -- nao uma aproximacao
// com tolerancia, outra formula -- e divergiria em silencio. Ver contrato
// secao 2.6 e a FRONTEIRA B do dourado, que tem arquivo proprio
// (`vetor_dourado_sequencias.json`) e e conferida no pytest.
//
// Por isso este alvo confere que as duas vem ZERO no arquivo: se um dia elas
// deixarem de vir zero aqui, o dourado do dispositivo mudou de natureza e
// este teste tem de ser revisto, em vez de continuar ignorando dois campos.
//
// ── AS TOLERANCIAS SAO LIDAS DO ARQUIVO, NAO ESCRITAS AQUI ────────────
//
// E a decisao de projeto deste alvo. Se as constantes estivessem copiadas
// neste .cpp, haveria duas declaracoes da mesma tolerancia -- e no dia em que
// o `test_as_tolerancias_ainda_cercam_o_piso` do Python medisse um piso maior
// e apertasse a constante, o lado C++ continuaria conferindo contra a regua
// velha, verde e desatualizado. Lendo do arquivo, a regua e uma so.
//
// O mesmo vale para `limiar_p_frac_g` e `corte_gravidade_hz`: o teste CONFERE
// que os numeros do arquivo batem com os compilados no firmware, em vez de
// assumir. Um corte de filtro diferente entre os dois lados nao apareceria
// como erro de paridade obvio -- apareceria como um residuo de borda maior,
// que e indistinguivel de "o filtro esta certo e a borda e assim".

#include <math.h>
#include <stdio.h>
#include <string.h>

#include "../caracteristicas.h"
#include "../epoca.h"
#include "../filtro.h"
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

static void secao(const char *nome) { printf("\n== %s\n", nome); }

// ── A ordem canonica, escrita para ser CONFERIDA ──────────────────────
//
// Trocar a ordem das features e mudanca MAJOR do contrato: um vetor na ordem
// errada passa em toda validacao de faixa e produz um modelo errado em
// silencio. Entao o teste nao assume a ordem -- ele le `ordem_features` do
// dourado e compara com esta lista.
static const char *const ORDEM_CANONICA[8] = {
    "enmo_media", "enmo_desvio", "enmo_max", "mag_din_media",
    "zcr",        "p_frac",      "inclinacao_rel", "d_angulo"};

struct Tolerancias {
  double enmo_abs_g;
  double zcr_abs;
  double mag_din_rel;
  double p_frac_abs_amostras;
  double g_componente_abs;
  double g_angulo_graus;
  bool completas;
  Tolerancias()
      : enmo_abs_g(0), zcr_abs(0), mag_din_rel(0), p_frac_abs_amostras(0),
        g_componente_abs(0), g_angulo_graus(0), completas(false) {}
};

// O pior caso visto em todos os casos, para o relatorio do fim. O numero
// medido vale mais que o "passou": ele diz QUANTA folga sobrou.
struct PiorCaso {
  double enmo_abs;
  double zcr_abs;
  double mag_din_rel;
  double p_frac_amostras;
  double g_componente;
  double g_angulo;
  double quant_enmo_media;
  double quant_enmo_desvio;
  double quant_enmo_max;
  double quant_mag_din;
  double quant_g_angulo;
  PiorCaso()
      : enmo_abs(0), zcr_abs(0), mag_din_rel(0), p_frac_amostras(0),
        g_componente(0), g_angulo(0), quant_enmo_media(0),
        quant_enmo_desvio(0), quant_enmo_max(0), quant_mag_din(0),
        quant_g_angulo(0) {}
};

static void maximizar(double *alvo, double candidato) {
  if (candidato > *alvo) *alvo = candidato;
}

static double angulo_entre_graus(const double a[3], const double b[3]) {
  double c = a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
  // O `clip` nao e decoracao: o produto interno de dois unitarios passa de 1
  // por 1 ulp com facilidade, e `acos` de 1,0000000000000002 e NaN. O NaN
  // atravessaria o teste como "divergencia nao maior que a tolerancia"
  // (porque toda comparacao com NaN e falsa) -- ou seja, um erro viraria um
  // sucesso. Mesma armadilha que `test_angulo_entre_vetores_paralelos_nao_e_nan`
  // registra do lado do Python.
  if (c > 1.0) c = 1.0;
  if (c < -1.0) c = -1.0;
  return acos(c) * 180.0 / 3.141592653589793;
}

// ── O caso do dourado, em memoria ─────────────────────────────────────
//
// Uma epoca de 960 amostras x 3 eixos em double: 23 KB na pilha seria
// arriscado, entao e estatico. Isto e codigo de teste de host; na placa nada
// disto existe.
static const uint32_t MAX_AMOSTRAS = 4096;
static double entrada_[MAX_AMOSTRAS][3];

struct Esperado {
  double f[8];
  double g[3];
  bool tem_g;
  Esperado() : tem_g(false) {
    for (int i = 0; i < 8; i++) f[i] = 0.0;
    g[0] = g[1] = g[2] = 0.0;
  }
};

// Le o bloco "esperado" de um caso. Aceita as chaves em qualquer ordem --
// um leitor que exigisse ordem quebraria no dia em que o Python mudasse de
// versao de `json.dumps`, e isso nao e uma mudanca de definicao.
static bool ler_esperado(LeitorJson *l, Esperado *e) {
  if (!l->entrar_objeto()) return false;
  char chave[64];
  while (l->proxima_chave(chave, sizeof(chave))) {
    bool casou = false;
    for (int i = 0; i < 8; i++) {
      if (strcmp(chave, ORDEM_CANONICA[i]) == 0) {
        if (!l->ler_numero(&e->f[i])) return false;
        casou = true;
        break;
      }
    }
    if (casou) continue;
    if (strcmp(chave, "g") == 0) {
      if (!l->ler_array_de_numeros(e->g, 3)) return false;
      e->tem_g = true;
      continue;
    }
    // Chave nova no bloco esperado: pular em silencio seria o
    // comportamento errado -- o dourado ganhou um campo e este teste nao
    // sabe o que fazer com ele. Melhor falhar e obrigar a decidir.
    l->falhar("chave desconhecida no bloco 'esperado' do dourado");
    return false;
  }
  return !l->erro();
}

static void conferir_um_caso(int seed, double fs, uint32_t n,
                             const Esperado &esp, const Tolerancias &tol,
                             PiorCaso *pior) {
  // ── O calculo, pelo caminho de producao ──
  //
  // De proposito atraves do `AcumuladorDeFeatures`, e nao chamando as contas
  // soltas: o que precisa ter paridade e o caminho que o firmware vai
  // executar, incluindo o arquivamento amostra a amostra e o fechamento.
  static AcumuladorDeFeatures acc;
  acc.iniciar();
  for (uint32_t i = 0; i < n; i++) {
    acc.amostrar(static_cast<float>(entrada_[i][0]),
                 static_cast<float>(entrada_[i][1]),
                 static_cast<float>(entrada_[i][2]));
  }
  VERIFICAR(acc.arquivadas() == n, "seed %d: arquivou %u de %u amostras", seed,
            acc.arquivadas(), n);
  VERIFICAR(acc.descartadas() == 0, "seed %d: %u amostras descartadas", seed,
            acc.descartadas());

  FeaturesDeEpoca f;
  const bool fechou = acc.fechar(static_cast<float>(fs), &f);
  VERIFICAR(fechou, "seed %d: fechar() recusou uma epoca COMPLETA de %u amostras",
            seed, n);
  if (!fechou) return;

  // ── ENMO: tolerancia ABSOLUTA, em g ──
  //
  // Nao passa pelo filtro. A regua e 1 ULP de float32 em 1 g, onde o ENMO faz
  // a subtracao que cancela -- nao e "exato", e o limite do float do alvo.
  const char *nomes_enmo[3] = {"enmo_media", "enmo_desvio", "enmo_max"};
  const double meus_enmo[3] = {f.enmo_media, f.enmo_desvio, f.enmo_max};
  for (int k = 0; k < 3; k++) {
    const double d = fabs(meus_enmo[k] - esp.f[k]);
    maximizar(&pior->enmo_abs, d);
    VERIFICAR(d <= tol.enmo_abs_g,
              "seed %d: %s divergiu %.3e g, acima de %.1e g. NAO depende do "
              "filtro -- e bug, nao borda. C++ %.17g vs Python %.17g",
              seed, nomes_enmo[k], d, tol.enmo_abs_g, meus_enmo[k], esp.f[k]);
  }

  // ── zcr: CONTAGEM, sem tolerancia ──
  const double d_zcr = fabs(f.zcr - esp.f[4]);
  maximizar(&pior->zcr_abs, d_zcr);
  VERIFICAR(d_zcr <= tol.zcr_abs,
            "seed %d: zcr divergiu %.3e -- e uma CONTAGEM de trocas de sinal, "
            "nao tem tolerancia possivel. C++ %.17g (%u cruzamentos em %u "
            "amostras) vs Python %.17g",
            seed, d_zcr, f.zcr, f.cruzamentos, f.amostras, esp.f[4]);

  // ── mag_din_media: tolerancia RELATIVA; aqui o filtro diverge de verdade ──
  const double ref_mag = esp.f[3];
  const double d_mag = fabs(f.mag_din_media - ref_mag);
  const double rel_mag = ref_mag != 0.0 ? d_mag / fabs(ref_mag) : d_mag;
  maximizar(&pior->mag_din_rel, rel_mag);
  VERIFICAR(rel_mag <= tol.mag_din_rel,
            "seed %d: mag_din_media divergiu %.3f%% (tolerancia %.1f%%). "
            "Confira se o biquad ainda e butter(2, %.2f Hz) nos DOIS sentidos "
            "com estado em regime permanente. C++ %.17g vs Python %.17g",
            seed, rel_mag * 100.0, tol.mag_din_rel * 100.0,
            static_cast<double>(CORTE_GRAVIDADE_HZ), f.mag_din_media, ref_mag);

  // ── p_frac: tolerancia ABSOLUTA em NUMERO DE AMOSTRAS ──
  //
  // Nao e quantidade continua: e fracao de amostras acima de um limiar
  // RIGIDO. O residuo de borda pode empurrar uma amostra que caiu em cima do
  // limiar para o outro lado, o que muda a contagem em +-1, nao o valor. Regua
  // percentual falharia justamente quando `p_frac` e pequeno -- noite parada,
  // que e o caso normal.
  const double d_pfrac_amostras = fabs(f.p_frac - esp.f[5]) * static_cast<double>(n);
  maximizar(&pior->p_frac_amostras, d_pfrac_amostras);
  VERIFICAR(d_pfrac_amostras <= tol.p_frac_abs_amostras,
            "seed %d: p_frac divergiu %.2f amostras de %u (tolerancia %.1f). "
            "C++ %.17g (%u acima) vs Python %.17g",
            seed, d_pfrac_amostras, n, tol.p_frac_abs_amostras, f.p_frac,
            f.amostras_acima, esp.f[5]);

  // ── `g`: por componente E por angulo ──
  VERIFICAR(esp.tem_g, "seed %d: o caso do dourado nao traz `g`", seed);
  if (esp.tem_g) {
    const double meu_g[3] = {f.gx, f.gy, f.gz};
    const double norma = sqrt(f.gx * f.gx + f.gy * f.gy + f.gz * f.gz);
    // Coerencia de UM lado, nao orcamento de paridade -- a distincao esta
    // registrada no contrato secao 2.6 e custou uma nota de rodape la.
    VERIFICAR(fabs(norma - 1.0) <= 1e-3,
              "seed %d: `g` do firmware nao e unitario (||g|| = %.17g). O "
              "contrato secao 2.6 exige 1 +- 1e-3 e o ponto fixo satura fora "
              "disso",
              seed, norma);
    for (int k = 0; k < 3; k++) {
      const double d = fabs(meu_g[k] - esp.g[k]);
      maximizar(&pior->g_componente, d);
      VERIFICAR(d <= tol.g_componente_abs,
                "seed %d: g[%d] divergiu %.3e, acima de %.1e (= sen da "
                "tolerancia angular). C++ %.17g vs Python %.17g",
                seed, k, d, tol.g_componente_abs, meu_g[k], esp.g[k]);
    }
    const double ang = angulo_entre_graus(meu_g, esp.g);
    maximizar(&pior->g_angulo, ang);
    VERIFICAR(ang <= tol.g_angulo_graus,
              "seed %d: `g` divergiu %.4f grau, acima de %.2f. O piso medido "
              "do residuo de borda e 0,082 grau no pior caso, entao isto nao "
              "e borda: e o filtro fora de sincronia",
              seed, ang, tol.g_angulo_graus);
  }

  // ── As duas angulares TEM de vir (praticamente) zero ──
  //
  // ⚠️ A regua e 1e-5 GRAU, e nao igualdade a zero. A primeira versao deste
  // teste exigia `== 0.0` e REPROVOU no seed 4, que traz
  // `inclinacao_rel = 8,53774e-07`.
  //
  // Nao e defeito do dourado: e o piso de condicionamento do `arccos`, que o
  // lado do Python ja tinha medido e registrado. Com uma epoca so, `g_ref` e
  // o proprio `g` da epoca, entao o produto interno e 1 -- e e justamente ali
  // que `arccos` e MAL CONDICIONADO: dtheta/dc = -1/sqrt(1-c^2) explode, e
  // 1 ulp em `c` (2,2e-16) vira ~6e-7 grau no angulo. O Python mede o mesmo
  // 8,5e-7 grau para dois vetores BIT A BIT IGUAIS
  // (`test_angulo_entre_vetores_paralelos_nao_e_nan`), e usa `atol=1e-5` pelo
  // mesmo motivo.
  //
  // Entao 1e-5 grau aqui nao e folga inventada: e a MESMA regua do outro
  // lado, e continua 100 000x abaixo da fronteira de decisao de 1 grau do
  // estudo do buffer. O que o teste ainda pega e o que ele existe para pegar:
  // se um dia estes campos vierem com valor DE VERDADE, o dourado do
  // dispositivo mudou de natureza.
  VERIFICAR(fabs(esp.f[6]) <= 1e-5 && fabs(esp.f[7]) <= 1e-5,
            "seed %d: o dourado do DISPOSITIVO trouxe inclinacao_rel=%g e "
            "d_angulo=%g acima do piso do arccos (1e-5 grau). Este alvo as "
            "ignora de proposito (sao derivadas no servidor); se elas passaram "
            "a ter valor aqui, o arquivo mudou de natureza e este teste "
            "precisa ser revisto",
            seed, esp.f[6], esp.f[7]);

  // ── O que a QUANTIZACAO custa, medido no mesmo caso ──
  //
  // Separado da paridade de proposito. Sao dois orcamentos de erro
  // diferentes, e confundi-los levaria a reprovar firmware correto: o passo do
  // u16 em `enmo_media` e 1,526e-5 g, contra uma tolerancia de paridade de
  // 1e-7 g. A regua da quantizacao nao e a tolerancia -- e o piso de ruido do
  // sensor (0,64 mg), conferido no fim do programa.
  const VetorDeFeatures q = quantizar(f);
  const FeaturesDeEpoca dq = desquantizar(q, f.amostras);
  maximizar(&pior->quant_enmo_media, fabs(dq.enmo_media - f.enmo_media));
  maximizar(&pior->quant_enmo_desvio, fabs(dq.enmo_desvio - f.enmo_desvio));
  maximizar(&pior->quant_enmo_max, fabs(dq.enmo_max - f.enmo_max));
  maximizar(&pior->quant_mag_din, fabs(dq.mag_din_media - f.mag_din_media));
  const double g_antes[3] = {f.gx, f.gy, f.gz};
  double g_depois[3] = {dq.gx, dq.gy, dq.gz};
  const double n_dep = sqrt(g_depois[0] * g_depois[0] + g_depois[1] * g_depois[1] +
                            g_depois[2] * g_depois[2]);
  if (n_dep > 1e-12) {
    g_depois[0] /= n_dep;
    g_depois[1] /= n_dep;
    g_depois[2] /= n_dep;
  }
  maximizar(&pior->quant_g_angulo, angulo_entre_graus(g_antes, g_depois));

  // As contagens atravessam o ponto fixo SEM PERDA -- e o que o contrato quer
  // dizer com "o firmware as guarda como a contagem inteira: em uint16 e
  // representacao exata, nao quantizacao".
  VERIFICAR(dq.zcr == f.zcr && dq.p_frac == f.p_frac,
            "seed %d: zcr/p_frac mudaram ao passar pelo ponto fixo -- deviam "
            "ser contagens exatas em uint16",
            seed);
}

// ── O percurso do arquivo ─────────────────────────────────────────────

static int rodar_dourado(const char *caminho) {
  uint32_t tamanho = 0;
  char *conteudo = dormio::testes::ler_arquivo_inteiro(caminho, &tamanho);
  if (conteudo == 0) {
    printf("  FALHOU  nao consegui abrir %s\n", caminho);
    printf("          O dourado e gravado pelo pytest do ml/. Rode:\n");
    printf("            cd ml && python -m pytest testes/test_vetor_dourado.py\n");
    falhas++;
    total++;
    return 1;
  }
  printf("  arquivo: %s (%u bytes)\n", caminho, tamanho);

  LeitorJson l(conteudo);
  Tolerancias tol;
  PiorCaso pior;
  uint32_t casos_vistos = 0;
  double limiar_do_arquivo = -1.0;
  double corte_do_arquivo = -1.0;
  double n_minimo_do_arquivo = -1.0;

  if (!l.entrar_objeto()) l.falhar("o dourado nao comeca com um objeto");

  char chave[64];
  while (l.proxima_chave(chave, sizeof(chave))) {
    if (strcmp(chave, "limiar_p_frac_g") == 0) {
      l.ler_numero(&limiar_do_arquivo);
    } else if (strcmp(chave, "corte_gravidade_hz") == 0) {
      l.ler_numero(&corte_do_arquivo);
    } else if (strcmp(chave, "n_amostras_minimo_paridade") == 0) {
      l.ler_numero(&n_minimo_do_arquivo);
    } else if (strcmp(chave, "ordem_features") == 0) {
      // A ordem canonica, conferida nome por nome.
      int i = 0;
      if (l.entrar_array()) {
        while (l.proximo_elemento()) {
          char nome[64];
          if (!l.ler_string(nome, sizeof(nome))) break;
          if (i < 8) {
            VERIFICAR(strcmp(nome, ORDEM_CANONICA[i]) == 0,
                      "ordem_features[%d] e \"%s\", esperado \"%s\" -- trocar a "
                      "ordem e mudanca MAJOR do contrato",
                      i, nome, ORDEM_CANONICA[i]);
          }
          i++;
        }
      }
      VERIFICAR(i == 8, "ordem_features tem %d nomes, esperados 8", i);
    } else if (strcmp(chave, "features_do_dispositivo") == 0) {
      int i = 0;
      if (l.entrar_array()) {
        while (l.proximo_elemento()) {
          char nome[64];
          if (!l.ler_string(nome, sizeof(nome))) break;
          if (i < 6) {
            VERIFICAR(strcmp(nome, ORDEM_CANONICA[i]) == 0,
                      "features_do_dispositivo[%d] e \"%s\", esperado \"%s\"", i,
                      nome, ORDEM_CANONICA[i]);
          }
          i++;
        }
      }
      // SEIS, nao oito. E a decisao do contrato v2.5.0: as duas angulares
      // saem do servidor, a partir do `g` bruto.
      VERIFICAR(i == 6,
                "features_do_dispositivo tem %d nomes, esperados 6. Se virou "
                "8, alguem reintroduziu calculo angular no dispositivo -- o "
                "que a secao 2.6 do contrato proibe, porque `g_ref` depende da "
                "noite inteira",
                i);
    } else if (strcmp(chave, "tolerancias") == 0) {
      if (l.entrar_objeto()) {
        char tk[64];
        while (l.proxima_chave(tk, sizeof(tk))) {
          if (strcmp(tk, "enmo_abs_g") == 0) {
            l.ler_numero(&tol.enmo_abs_g);
          } else if (strcmp(tk, "zcr_abs") == 0) {
            l.ler_numero(&tol.zcr_abs);
          } else if (strcmp(tk, "mag_din_rel") == 0) {
            l.ler_numero(&tol.mag_din_rel);
          } else if (strcmp(tk, "p_frac_abs_amostras") == 0) {
            l.ler_numero(&tol.p_frac_abs_amostras);
          } else if (strcmp(tk, "g_componente_abs") == 0) {
            l.ler_numero(&tol.g_componente_abs);
          } else if (strcmp(tk, "g_angulo_graus") == 0) {
            l.ler_numero(&tol.g_angulo_graus);
          } else {
            l.pular_valor();
          }
        }
        tol.completas = tol.enmo_abs_g > 0 && tol.mag_din_rel > 0 &&
                        tol.p_frac_abs_amostras > 0 && tol.g_componente_abs > 0 &&
                        tol.g_angulo_graus > 0;
      }
    } else if (strcmp(chave, "casos") == 0) {
      if (!tol.completas) {
        // Ordem de chaves no JSON do Python poe `tolerancias` antes de
        // `casos`, mas depender disso seria frágil. Se um dia inverter, isto
        // falha alto em vez de conferir contra tolerancia zero -- que
        // reprovaria tudo e faria parecer que o firmware esta errado.
        l.falhar("`casos` apareceu antes de `tolerancias` completas no dourado");
      }
      if (l.entrar_array()) {
        while (l.proximo_elemento()) {
          double seed = -1, fs = -1, n_amostras = -1;
          Esperado esp;
          bool tem_entrada = false;
          uint32_t n_lidas = 0;

          if (!l.entrar_objeto()) break;
          char ck[64];
          while (l.proxima_chave(ck, sizeof(ck))) {
            if (strcmp(ck, "seed") == 0) {
              l.ler_numero(&seed);
            } else if (strcmp(ck, "fs_hz") == 0) {
              l.ler_numero(&fs);
            } else if (strcmp(ck, "n_amostras") == 0) {
              l.ler_numero(&n_amostras);
            } else if (strcmp(ck, "entrada_g") == 0) {
              if (l.entrar_array()) {
                while (l.proximo_elemento()) {
                  if (n_lidas < MAX_AMOSTRAS) {
                    if (!l.ler_array_de_numeros(entrada_[n_lidas], 3)) break;
                  } else {
                    l.falhar("entrada_g maior que MAX_AMOSTRAS do teste");
                    break;
                  }
                  n_lidas++;
                }
              }
              tem_entrada = true;
            } else if (strcmp(ck, "esperado") == 0) {
              ler_esperado(&l, &esp);
            } else {
              l.pular_valor();
            }
          }
          if (l.erro()) break;

          VERIFICAR(tem_entrada, "caso sem `entrada_g`");
          VERIFICAR(n_amostras > 0, "caso sem `n_amostras`");
          // A assercao de quantidade que faz o resto valer: se o leitor
          // tivesse lido menos amostras, a paridade passaria sobre dado pela
          // metade.
          VERIFICAR(static_cast<double>(n_lidas) == n_amostras,
                    "seed %d: li %u amostras, o arquivo declara %g", (int)seed,
                    n_lidas, n_amostras);

          if (!l.erro() && static_cast<double>(n_lidas) == n_amostras) {
            conferir_um_caso(static_cast<int>(seed), fs, n_lidas, esp, tol, &pior);
            casos_vistos++;
          }
        }
      }
    } else {
      l.pular_valor();
    }
  }

  if (l.erro()) {
    printf("  FALHOU  erro de leitura do dourado: %s (posicao %u)\n", l.mensagem(),
           l.posicao());
    falhas++;
    total++;
  }

  // ── As constantes do arquivo TEM de bater com as compiladas ──
  secao("as constantes do dourado batem com as do firmware");
  VERIFICAR(limiar_do_arquivo > 0, "o dourado nao trouxe `limiar_p_frac_g`");
  const double limiar_cpp = static_cast<double>(LIMIAR_P_FRAC_G);
  // Folga de 1e-7 relativo: o firmware guarda o limiar em `float` (e a
  // comparacao de `p_frac` acontece em float promovido), o Python em float64.
  // Nao e tolerancia de paridade -- e a largura do tipo.
  VERIFICAR(fabs(limiar_cpp - limiar_do_arquivo) <= 1e-7 * limiar_do_arquivo,
            "o limiar de p_frac do dourado (%.17g) nao bate com o do firmware "
            "(%.17g). `p_frac` e contagem contra limiar RIGIDO: limiares "
            "diferentes nao divergem um pouco, divergem por amostra",
            limiar_do_arquivo, limiar_cpp);
  VERIFICAR(fabs(static_cast<double>(CORTE_GRAVIDADE_HZ) - corte_do_arquivo) <= 1e-9,
            "o corte do filtro do dourado (%.17g Hz) nao bate com o do "
            "firmware (%.17g Hz). Cortes diferentes nao aparecem como erro "
            "obvio -- aparecem como residuo de borda maior, indistinguivel de "
            "'a borda e assim'",
            corte_do_arquivo, static_cast<double>(CORTE_GRAVIDADE_HZ));
  VERIFICAR(n_minimo_do_arquivo == static_cast<double>(AMOSTRAS_MINIMAS_PARA_PARIDADE),
            "o minimo de amostras para paridade do dourado (%g) nao bate com o "
            "do firmware (%u)",
            n_minimo_do_arquivo,
            static_cast<unsigned>(AMOSTRAS_MINIMAS_PARA_PARIDADE));

  VERIFICAR(casos_vistos == 5,
            "conferi %u casos, o dourado tem 5. Se o arquivo cresceu, otimo -- "
            "atualize este numero de proposito",
            casos_vistos);

  // ── O relatorio dos piores casos ──
  //
  // Mais util que "passou": diz quanta folga sobrou em cada regua, e e o que
  // permite ver uma tolerancia encostando ANTES de ela estourar.
  secao("folga medida em cada regua (pior caso dos 5)");
  printf("  %-22s %12s %12s %8s\n", "regua", "pior medido", "tolerancia", "uso");
  printf("  %-22s %12.3e %12.1e %7.1f%%\n", "enmo (abs, g)", pior.enmo_abs,
         tol.enmo_abs_g, 100.0 * pior.enmo_abs / tol.enmo_abs_g);
  printf("  %-22s %12.3e %12.1e %8s\n", "zcr (abs)", pior.zcr_abs, tol.zcr_abs,
         pior.zcr_abs == 0.0 ? "exato" : "ESTOUROU");
  printf("  %-22s %11.3f%% %11.1f%% %7.1f%%\n", "mag_din_media (rel)",
         pior.mag_din_rel * 100.0, tol.mag_din_rel * 100.0,
         100.0 * pior.mag_din_rel / tol.mag_din_rel);
  printf("  %-22s %12.2f %12.1f %7.1f%%\n", "p_frac (amostras)",
         pior.p_frac_amostras, tol.p_frac_abs_amostras,
         100.0 * pior.p_frac_amostras / tol.p_frac_abs_amostras);
  printf("  %-22s %12.3e %12.1e %7.1f%%\n", "g (componente)", pior.g_componente,
         tol.g_componente_abs, 100.0 * pior.g_componente / tol.g_componente_abs);
  printf("  %-22s %12.4f %12.2f %7.1f%%\n", "g (angulo, grau)", pior.g_angulo,
         tol.g_angulo_graus, 100.0 * pior.g_angulo / tol.g_angulo_graus);

  secao("o que a QUANTIZACAO de 16 bits custa (orcamento SEPARADO)");
  printf("  Nao se compara com as tolerancias acima: aquelas medem se as duas\n");
  printf("  implementacoes calculam a mesma formula; esta mede o preco da\n");
  printf("  representacao. A regua aqui e o piso de ruido do ENMO no MPU6050,\n");
  printf("  0,64 mg = 6,40e-04 g (ML-DATASETS secao 2.2).\n\n");
  const double piso_ruido_enmo_g = 0.00064;
  printf("  %-22s %12s %12s\n", "campo", "perda (g)", "x piso ruido");
  printf("  %-22s %12.3e %11.3fx\n", "enmo_media", pior.quant_enmo_media,
         pior.quant_enmo_media / piso_ruido_enmo_g);
  printf("  %-22s %12.3e %11.3fx\n", "enmo_desvio", pior.quant_enmo_desvio,
         pior.quant_enmo_desvio / piso_ruido_enmo_g);
  printf("  %-22s %12.3e %11.3fx\n", "enmo_max", pior.quant_enmo_max,
         pior.quant_enmo_max / piso_ruido_enmo_g);
  printf("  %-22s %12.3e %11.3fx\n", "mag_din_media", pior.quant_mag_din,
         pior.quant_mag_din / piso_ruido_enmo_g);
  printf("  %-22s %12.4f %12s\n", "g (angulo, grau)", pior.quant_g_angulo,
         "ver abaixo");

  // A quantizacao tem de ficar ABAIXO do piso de ruido do sensor: se ela
  // passasse disso, a representacao de 16 bits estaria descartando sinal que o
  // sensor consegue medir -- e a decisao do estudo do buffer (Delta-kappa
  // ~1e-4) teria de ser refeita.
  VERIFICAR(pior.quant_enmo_media < piso_ruido_enmo_g,
            "a quantizacao de enmo_media (%.3e g) passou do piso de ruido do "
            "MPU6050 (%.2e g)",
            pior.quant_enmo_media, piso_ruido_enmo_g);
  VERIFICAR(pior.quant_enmo_max < piso_ruido_enmo_g,
            "a quantizacao de enmo_max (%.3e g) passou do piso de ruido do "
            "MPU6050 (%.2e g). O fundo de escala de 16 g e o mais grosso dos "
            "quatro -- se mudar, este e o numero a revisar",
            pior.quant_enmo_max, piso_ruido_enmo_g);
  // `g` quantizado move os angulos do servidor em ate 2,0e-3 grau (medido no
  // DATA-07c). A fronteira de decisao do estudo do buffer e 1 grau.
  VERIFICAR(pior.quant_g_angulo < 0.01,
            "a quantizacao de `g` moveu a direcao em %.5f grau, acima dos 0,01 "
            "grau que o dourado da fronteira B declara",
            pior.quant_g_angulo);

  dormio::testes::liberar_arquivo(conteudo);
  return 0;
}

// ── Testes do filtro e das bordas, independentes do dourado ───────────

static void testar_coeficientes_do_filtro() {
  secao("coeficientes do Butterworth");

  // Valores de referencia de `scipy.signal.butter(2, 0.25/(32/2), "low")`,
  // conferidos com o scipy de verdade (ver o comentario no fim do arquivo).
  // Estao escritos aqui porque um filtro com coeficiente errado NAO falha de
  // forma obvia: ele vira outro filtro, com outra banda, e as features saem
  // plausiveis e erradas.
  const CoeficientesBiquad c = coeficientes_butterworth2(32.0f, 0.25f);
  VERIFICAR(fabs(c.b0 - 0.00058207613423604820) < 1e-15, "b0 = %.17g", c.b0);
  VERIFICAR(c.b1 == 2.0 * c.b0, "b1 e exatamente 2*b0");
  VERIFICAR(c.b2 == c.b0, "b2 e exatamente b0 (simetria do FIR do biquad)");
  VERIFICAR(fabs(c.a1 - (-1.9306064272196681)) < 1e-14, "a1 = %.17g", c.a1);
  VERIFICAR(fabs(c.a2 - 0.93293473175661220) < 1e-14, "a2 = %.17g", c.a2);

  // ── Ganho unitario em DC ──
  //
  // H(1) = (b0+b1+b2)/(1+a1+a2) tem de dar 1, e esta e a propriedade de que
  // depende a inicializacao em regime permanente: se o ganho DC nao fosse 1,
  // comecar com `y = v[0]` seria errado e a gravidade estimada sairia
  // ESCALADA -- um vies, nao um ruido.
  //
  // ⚠️ A regua e 1e-12, e nao 1e-15, por causa do CONDICIONAMENTO da propria
  // expressao: `1 + a1 + a2` = 0,0023283, uma soma que perde quase tres
  // ordens de grandeza. Mesmo com os coeficientes exatos em double, o
  // resultado herda ~1e-16/0,0023 = 4e-14 de erro relativo. 1e-12 e tres
  // ordens de folga sobre esse piso.
  //
  // 📌 Esta tolerancia ja esteve em 1e-5 e REPROVOU -- com os coeficientes em
  // float32 o ganho dava 1,0000120. A correcao foi passar os coeficientes
  // para double (ver `CoeficientesBiquad`), nao afrouxar o numero. Fica
  // registrado porque a tentacao de mexer na constante era imediata e errada:
  // o teste estava certo, o estimador estava enviesado.
  const double dc = (c.b0 + c.b1 + c.b2) / (1.0 + c.a1 + c.a2);
  VERIFICAR(fabs(dc - 1.0) < 1e-12, "ganho DC = %.17g, deveria ser 1", dc);

  VERIFICAR(!filtro_aplicavel(32.0f, 16.0f), "recusa corte EM Nyquist");
  VERIFICAR(!filtro_aplicavel(32.0f, 20.0f), "recusa corte acima de Nyquist");
  VERIFICAR(filtro_aplicavel(32.0f, 0.25f), "aceita o corte de projeto");
}

static void testar_regime_permanente() {
  secao("inicializacao em regime permanente");

  // Sinal CONSTANTE em 1 g. Um filtro passa-baixa de ganho unitario em DC tem
  // de devolver 1 g em TODA amostra, inclusive na primeira. Se o estado
  // comecasse em zero, a primeira amostra sairia perto de 0 e so subiria
  // depois -- um transiente de ~meio segundo exatamente onde a epoca comeca,
  // com a gravidade valendo ~1 g. Erro de 1 g, nao de 1 %.
  const uint32_t n = 960;
  static float v[960];
  for (uint32_t i = 0; i < n; i++) v[i] = 1.0f;
  VERIFICAR(filtrar_ida_e_volta(v, n, 32.0f, 0.25f), "filtra o constante");

  double pior = 0.0;
  for (uint32_t i = 0; i < n; i++) {
    const double d = fabs(static_cast<double>(v[i]) - 1.0);
    if (d > pior) pior = d;
  }
  VERIFICAR(pior < 1e-6,
            "o constante de 1 g saiu alterado em %.3e no pior ponto -- o estado "
            "nao esta em regime permanente",
            pior);
  printf("     sinal constante: desvio maximo %.3e g\n", pior);

  // Degrau: o filtro NAO pode antecipar nem atrasar a borda de forma
  // assimetrica -- e o que a fase zero garante. Aqui so se confere que o
  // resultado e finito e monotono nao-decrescente num degrau de subida, que e
  // o sintoma barato de estado corrompido.
  for (uint32_t i = 0; i < n; i++) v[i] = (i < n / 2) ? 0.0f : 1.0f;
  VERIFICAR(filtrar_ida_e_volta(v, n, 32.0f, 0.25f), "filtra o degrau");
  bool finito = true;
  for (uint32_t i = 0; i < n; i++) {
    if (!(v[i] == v[i]) || v[i] < -0.5f || v[i] > 1.5f) finito = false;
  }
  VERIFICAR(finito, "o degrau produziu valor nao finito ou fora de faixa");

  VERIFICAR(!filtrar_ida_e_volta(v, 1, 32.0f, 0.25f), "recusa n = 1");
  VERIFICAR(!filtrar_ida_e_volta(0, n, 32.0f, 0.25f), "recusa ponteiro nulo");
}

static void testar_recusa_de_epoca_incompleta() {
  secao("epoca incompleta e RECUSADA, nao aproximada");

  // E a implementacao da decisao do contrato secao 2.6: "o dispositivo nao
  // pode emitir `f` de uma epoca truncada". A medicao que justifica esta em
  // `test_epoca_incompleta_nao_tem_paridade`: 8 amostras divergem 54 %, 64
  // divergem 3 %, e so a epoca completa cai para 0,26 %.
  //
  // O ponto e que o firmware nao DEVOLVE um vetor nesses casos. Emitir seis
  // numeros dentro de todas as faixas do contrato e errados em 54 % e pior
  // que nao emitir nada: o servidor nao tem como saber.
  static AcumuladorDeFeatures acc;
  const uint32_t curtas[5] = {0, 1, 8, 64, 300};
  for (int k = 0; k < 5; k++) {
    acc.iniciar();
    for (uint32_t i = 0; i < curtas[k]; i++) {
      acc.amostrar(0.1f, 0.2f, 0.97f);
    }
    FeaturesDeEpoca f;
    VERIFICAR(!acc.fechar(32.0f, &f),
              "epoca de %u amostras NAO foi recusada -- o contrato exige que o "
              "dispositivo nao emita `f` de epoca truncada",
              curtas[k]);
  }

  // E a completa, essa sim, fecha.
  acc.iniciar();
  for (uint32_t i = 0; i < AMOSTRAS_POR_EPOCA_NOMINAL; i++) {
    acc.amostrar(0.1f, 0.2f, 0.97f);
  }
  FeaturesDeEpoca f;
  VERIFICAR(acc.fechar(32.0f, &f), "epoca completa fecha");

  // Transbordo CONTADO, nao silencioso.
  acc.iniciar();
  for (uint32_t i = 0; i < AMOSTRAS_POR_EPOCA_NOMINAL + 17u; i++) {
    acc.amostrar(0.1f, 0.2f, 0.97f);
  }
  VERIFICAR(acc.arquivadas() == AMOSTRAS_POR_EPOCA_NOMINAL,
            "a janela aceitou mais que o maximo");
  VERIFICAR(acc.descartadas() == 17u,
            "o transbordo nao foi contado: %u descartadas, esperadas 17",
            acc.descartadas());

  // `fs` invalido tambem recusa, em vez de produzir um filtro degenerado.
  acc.iniciar();
  for (uint32_t i = 0; i < AMOSTRAS_POR_EPOCA_NOMINAL; i++) {
    acc.amostrar(0.1f, 0.2f, 0.97f);
  }
  VERIFICAR(!acc.fechar(0.4f, &f),
            "fs = 0,4 Hz (Nyquist 0,2 < corte 0,25) nao foi recusado");
}

static void testar_invariancia_a_rotacao() {
  secao("as 6 features sao invariantes a rotacao do referencial");

  // A propriedade que justifica a escolha das features: num travesseiro a
  // orientacao e arbitraria E muda durante a noite, entao uma feature que
  // mede a orientacao de montagem nao transfere. Do lado do Python isto e
  // `test_features_invariantes_a_rotacao`, e ele JA REPROVOU uma feature de
  // verdade (a SMA em norma L1, que variava ~6 %).
  //
  // Aqui a rotacao e fixa e escrita: 30 graus em torno de z composto com 40
  // em torno de x. Nao precisa ser aleatoria -- precisa ser ortogonal, e uma
  // composicao de duas rotacoes elementares e, por construcao.
  const double a1 = 30.0 * 3.141592653589793 / 180.0;
  const double a2 = 40.0 * 3.141592653589793 / 180.0;
  const double cz = cos(a1), sz = sin(a1);
  const double cx = cos(a2), sx = sin(a2);
  // R = Rx(a2) * Rz(a1)
  const double R[3][3] = {
      {cz, -sz, 0.0},
      {cx * sz, cx * cz, -sx},
      {sx * sz, sx * cz, cx}};

  static AcumuladorDeFeatures a_normal;
  static AcumuladorDeFeatures a_girado;
  a_normal.iniciar();
  a_girado.iniciar();

  // Um sinal com movimento de verdade: gravidade mais uma oscilacao, senao a
  // invariancia seria testada sobre um constante, onde tudo e invariante.
  for (uint32_t i = 0; i < AMOSTRAS_POR_EPOCA_NOMINAL; i++) {
    const double t = static_cast<double>(i) / 32.0;
    const double v[3] = {0.30 + 0.05 * sin(2.0 * 3.14159 * 1.3 * t),
                         0.20 + 0.04 * sin(2.0 * 3.14159 * 2.1 * t + 0.7),
                         0.93 + 0.03 * sin(2.0 * 3.14159 * 0.8 * t + 1.9)};
    a_normal.amostrar(static_cast<float>(v[0]), static_cast<float>(v[1]),
                      static_cast<float>(v[2]));
    double w[3];
    for (int r = 0; r < 3; r++) {
      w[r] = R[r][0] * v[0] + R[r][1] * v[1] + R[r][2] * v[2];
    }
    a_girado.amostrar(static_cast<float>(w[0]), static_cast<float>(w[1]),
                      static_cast<float>(w[2]));
  }

  FeaturesDeEpoca f0, f1;
  VERIFICAR(a_normal.fechar(32.0f, &f0) && a_girado.fechar(32.0f, &f1),
            "as duas epocas fecham");

  // 1e-6 relativo: as amostras passam por `float` na janela, e a rotacao em
  // double seguida de conversao para float introduz ~6e-8 relativo por
  // componente. Nao e a invariancia que e aproximada -- e o armazenamento.
  struct Par { const char *nome; double a, b; };
  const Par pares[6] = {
      {"enmo_media", f0.enmo_media, f1.enmo_media},
      {"enmo_desvio", f0.enmo_desvio, f1.enmo_desvio},
      {"enmo_max", f0.enmo_max, f1.enmo_max},
      {"mag_din_media", f0.mag_din_media, f1.mag_din_media},
      {"zcr", f0.zcr, f1.zcr},
      {"p_frac", f0.p_frac, f1.p_frac}};
  for (int k = 0; k < 6; k++) {
    const double escala = fabs(pares[k].a) > 1e-12 ? fabs(pares[k].a) : 1.0;
    const double rel = fabs(pares[k].a - pares[k].b) / escala;
    VERIFICAR(rel < 1e-5,
              "%s MUDOU sob rotacao do referencial em %.3e relativo -- nao e "
              "invariante a orientacao e nao pode ser usada (DECISAO TECNICA 1 "
              "de ml/src/features.py)",
              pares[k].nome, rel);
  }

  // `g` nao e invariante: ele GIRA com o referencial, que e o esperado. O que
  // tem de ser invariante e o ANGULO entre `g` e qualquer outra direcao --
  // e e disso que vive a invariancia de `inclinacao_rel` no servidor.
  const double g0[3] = {f0.gx, f0.gy, f0.gz};
  const double g1[3] = {f1.gx, f1.gy, f1.gz};
  double g0_girado[3];
  for (int r = 0; r < 3; r++) {
    g0_girado[r] = R[r][0] * g0[0] + R[r][1] * g0[1] + R[r][2] * g0[2];
  }
  const double ang = angulo_entre_graus(g0_girado, g1);
  VERIFICAR(ang < 1e-3,
            "R*g da epoca normal e o `g` da epoca girada diferem %.3e grau -- "
            "`g` deveria ser EQUIVARIANTE a rotacao",
            ang);
  printf("     R*g vs g(girada): %.3e grau\n", ang);
}

// ── main ──────────────────────────────────────────────────────────────

int main(int argc, char **argv) {
  printf("Paridade do nucleo contra o vetor dourado -- DATA-07b\n");
  printf("=====================================================\n");
  printf("sizeof(VetorDeFeatures) = %u bytes\n",
         static_cast<unsigned>(sizeof(VetorDeFeatures)));
  printf("sizeof(Epoca)           = %u bytes\n",
         static_cast<unsigned>(sizeof(Epoca)));
  printf("janela do acumulador    = %u bytes (%.1f KiB)\n",
         static_cast<unsigned>(sizeof(AcumuladorDeFeatures)),
         static_cast<double>(sizeof(AcumuladorDeFeatures)) / 1024.0);

  secao("autoteste do leitor de JSON");
  const int falhas_leitor = dormio::testes::autotestar_leitor_json();
  total++;
  if (falhas_leitor != 0) {
    falhas++;
    printf("  FALHOU  o leitor de JSON tem %d defeitos -- NAO confie no resto "
           "deste programa: a regua esta torta\n",
           falhas_leitor);
  } else {
    printf("  ok -- o leitor passa inclusive nos casos que deve RECUSAR\n");
  }

  testar_coeficientes_do_filtro();
  testar_regime_permanente();
  testar_recusa_de_epoca_incompleta();
  testar_invariancia_a_rotacao();

  secao("FRONTEIRA A -- paridade das 6 features e de `g`");
  const char *caminho = (argc > 1) ? argv[1] : "../../ml/testes/vetor_dourado.json";
  rodar_dourado(caminho);

  printf("\n-----------------------------------------\n");
  printf("%d verificacoes, %d falhas\n", total, falhas);
  return falhas == 0 ? 0 : 1;
}

// Os coeficientes de referencia do `testar_coeficientes_do_filtro` saem de:
//
//     python -c "from scipy.signal import butter;
//                b,a = butter(2, 0.25/(32/2), 'low'); print(repr(b), repr(a))"
//
// Conferido em 2026-10-17 com scipy 1.15.3: a forma fechada deste modulo e o
// `butter` do scipy concordam em 2,2e-19 nos cinco coeficientes.
//
// Estao escritos no teste e nao calculados por ele de proposito: se a formula
// fechada deste modulo e a do scipy divergirem algum dia, o teste tem de
// falhar -- e um teste que recalculasse os dois lados com a mesma formula
// nunca falharia.
