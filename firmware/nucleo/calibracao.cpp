// calibracao.cpp -- ver calibracao.h. A referencia e `ml/src/calibracao.py`.

#include "calibracao.h"

#include <math.h>

namespace dormio {

Calibracao::Calibracao() { identidade(); }

void Calibracao::identidade() {
  aceita = false;
  for (int k = 0; k < 3; k++) {
    desvio[k] = 0.0;
    escala[k] = 1.0;
    coef_temp[k] = 0.0;
    modos[k] = EIXO_FIXO;
  }
  temp_ref_c = 0.0;
  usou_temperatura = false;
  n = 0;
  erro_antes_g = 0.0;
  erro_depois_g = 0.0;
  iteracoes = 0;
}

void aplicar_calibracao(const Calibracao &c, double temp_c, const double entrada[3],
                        double saida[3]) {
  const double dt = temp_c - c.temp_ref_c;
  for (int k = 0; k < 3; k++) {
    saida[k] = c.aceita ? c.desvio[k] + c.escala[k] * entrada[k] + c.coef_temp[k] * dt
                        : entrada[k];
  }
}

void desfazer_calibracao(const Calibracao &c, double temp_c, const double entrada[3],
                         double saida[3]) {
  const double dt = temp_c - c.temp_ref_c;
  for (int k = 0; k < 3; k++) {
    saida[k] = c.aceita ? (entrada[k] - c.desvio[k] - c.coef_temp[k] * dt) / c.escala[k]
                        : entrada[k];
  }
}

static double norma(const double v[3]) { return sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2]); }

// Erro RMS da norma: o quanto os pontos estao fora da esfera de 1 g.
static double erro_rms(const Calibracao &c, const double (*p)[3], const double *t, uint32_t n) {
  double soma = 0.0;
  for (uint32_t i = 0; i < n; i++) {
    double cal[3];
    aplicar_calibracao(c, t[i], p[i], cal);
    const double e = norma(cal) - 1.0;
    soma += e * e;
  }
  return sqrt(soma / static_cast<double>(n));
}

// Resolve o sistema `m` x `m` (m <= 3) por eliminacao de Gauss com pivo
// parcial. Devolve false se for singular (nao acontece com as colunas que o
// estimador escolhe: o eixo so entra quando passou de 0,3 g, e a temperatura
// so com 2 graus de faixa).
static bool resolver(double a[3][3], double b[3], int m, double x[3]) {
  for (int col = 0; col < m; col++) {
    int pivo = col;
    for (int lin = col + 1; lin < m; lin++) {
      if (fabs(a[lin][col]) > fabs(a[pivo][col])) pivo = lin;
    }
    if (fabs(a[pivo][col]) < 1e-300) return false;
    if (pivo != col) {
      for (int j = 0; j < m; j++) {
        const double tmp = a[col][j];
        a[col][j] = a[pivo][j];
        a[pivo][j] = tmp;
      }
      const double tb = b[col];
      b[col] = b[pivo];
      b[pivo] = tb;
    }
    for (int lin = col + 1; lin < m; lin++) {
      const double f = a[lin][col] / a[col][col];
      for (int j = col; j < m; j++) a[lin][j] -= f * a[col][j];
      b[lin] -= f * b[col];
    }
  }
  for (int lin = m - 1; lin >= 0; lin--) {
    double s = b[lin];
    for (int j = lin + 1; j < m; j++) s -= a[lin][j] * x[j];
    x[lin] = s / a[lin][lin];
  }
  return true;
}

static Calibracao recusar(const Calibracao &c) {
  Calibracao r;
  r.temp_ref_c = c.temp_ref_c;
  for (int k = 0; k < 3; k++) r.modos[k] = c.modos[k];
  r.usou_temperatura = c.usou_temperatura;
  r.n = c.n;
  r.erro_antes_g = c.erro_antes_g;
  r.erro_depois_g = c.erro_depois_g;
  r.iteracoes = c.iteracoes;
  return r;
}

Calibracao estimar_calibracao(const double (*p)[3], const double *t, uint32_t n) {
  Calibracao c;
  c.n = n;
  if (p == 0 || t == 0 || n < PONTOS_MINIMOS_CALIBRACAO) return c;

  c.erro_antes_g = erro_rms(c, p, t, n);

  double t_min = t[0], t_max = t[0], t_soma = 0.0;
  for (uint32_t i = 0; i < n; i++) {
    if (t[i] < t_min) t_min = t[i];
    if (t[i] > t_max) t_max = t[i];
    t_soma += t[i];
  }
  c.temp_ref_c = t_soma / static_cast<double>(n);
  c.usou_temperatura = (t_max - t_min) >= FAIXA_MINIMA_TEMPERATURA_C;

  bool algum = false;
  for (int k = 0; k < 3; k++) {
    bool acima = false, abaixo = false;
    for (uint32_t i = 0; i < n; i++) {
      if (p[i][k] > LADO_MINIMO_G) acima = true;
      if (p[i][k] < -LADO_MINIMO_G) abaixo = true;
    }
    c.modos[k] = (acima && abaixo) ? EIXO_COMPLETO : (acima || abaixo) ? EIXO_DESVIO : EIXO_FIXO;
    if (c.modos[k] != EIXO_FIXO) algum = true;
  }
  if (!algum) {
    c.erro_depois_g = c.erro_antes_g;
    return c;
  }

  // A iteracao roda com `aceita` ligado para `aplicar` calibrar; a decisao
  // de aceitar vem no fim.
  c.aceita = true;
  double erro = c.erro_antes_g;
  for (uint32_t it = 1; it <= ITERACOES_MAXIMAS_CALIBRACAO; it++) {
    // Os alvos sao calculados com a calibracao do INICIO da iteracao, para os
    // tres eixos -- como na referencia, que projeta todos antes de ajustar.
    const Calibracao antes = c;
    for (int k = 0; k < 3; k++) {
      if (c.modos[k] == EIXO_FIXO) continue;
      const bool completo = c.modos[k] == EIXO_COMPLETO;
      // Colunas: 1, [bruto se completo], [dT se temperatura].
      const int m = 1 + (completo ? 1 : 0) + (c.usou_temperatura ? 1 : 0);
      double ata[3][3] = {{0, 0, 0}, {0, 0, 0}, {0, 0, 0}};
      double aty[3] = {0, 0, 0};
      for (uint32_t i = 0; i < n; i++) {
        double cal[3];
        aplicar_calibracao(antes, t[i], p[i], cal);
        const double nc = norma(cal);
        const double alvo = cal[k] / nc;
        const double y = completo ? alvo : alvo - p[i][k];
        double linha[3];
        int j = 0;
        linha[j++] = 1.0;
        if (completo) linha[j++] = p[i][k];
        if (c.usou_temperatura) linha[j++] = t[i] - c.temp_ref_c;
        for (int a = 0; a < m; a++) {
          aty[a] += linha[a] * y;
          for (int b = 0; b < m; b++) ata[a][b] += linha[a] * linha[b];
        }
      }
      double x[3] = {0, 0, 0};
      if (!resolver(ata, aty, m, x)) return recusar(c);
      c.desvio[k] = x[0];
      if (completo) c.escala[k] = x[1];
      if (c.usou_temperatura) c.coef_temp[k] = x[m - 1];
    }
    const double novo = erro_rms(c, p, t, n);
    c.iteracoes = it;
    const double melhora = erro - novo;
    erro = novo;
    if (fabs(melhora) < TOLERANCIA_CALIBRACAO) break;
  }

  c.erro_depois_g = erro;
  if (!(c.erro_depois_g < c.erro_antes_g)) return recusar(c);
  if (c.erro_depois_g > ERRO_MAXIMO_ACEITO_G) return recusar(c);
  return c;
}

}  // namespace dormio
