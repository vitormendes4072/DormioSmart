#include "reamostragem.h"

#include <math.h>

namespace dormio {

static const double PI_DUPLO = 3.141592653589793;

CoeficientesBiquad coeficientes_secao(float fs, float corte_hz, double q) {
  // Mesma forma fechada de `coeficientes_butterworth2`, com `k / q` no lugar
  // de `sqrt(2) * k`. Copia linha por linha `_secao` em dourado_cadeia_c2.py.
  const double k = tan(PI_DUPLO * static_cast<double>(corte_hz) / static_cast<double>(fs));
  const double kk = k * k;
  const double norma = 1.0 / (1.0 + k / q + kk);
  CoeficientesBiquad c;
  c.b0 = kk * norma;
  c.b1 = 2.0 * c.b0;
  c.b2 = c.b0;
  c.a1 = 2.0 * (kk - 1.0) * norma;
  c.a2 = (1.0 - k / q + kk) * norma;
  return c;
}

bool filtrar_antialiasing(float *v, uint32_t n, float fs) {
  if (v == 0 || n < 2) return false;
  if (!filtro_aplicavel(fs, CORTE_ANTIALIASING_HZ)) return false;
  const CoeficientesBiquad s1 = coeficientes_secao(fs, CORTE_ANTIALIASING_HZ, Q_SECAO_1);
  const CoeficientesBiquad s2 = coeficientes_secao(fs, CORTE_ANTIALIASING_HZ, Q_SECAO_2);
  // Ida: secao 1, secao 2. Volta: secao 1, secao 2, percorrendo ao contrario.
  // E a ordem de `filtrar_antialiasing` no Python; trocar a ordem das secoes
  // na volta nao muda a resposta em magnitude, mas muda o arredondamento e o
  // transiente de borda -- e a paridade e contra aquela ordem.
  passagem_biquad(v, n, s1, false);
  passagem_biquad(v, n, s2, false);
  passagem_biquad(v, n, s1, true);
  passagem_biquad(v, n, s2, true);
  return true;
}

void interpolar_linear(const float *v, uint32_t n, double x0, double dx, float *saida,
                       uint32_t m) {
  if (v == 0 || saida == 0 || n == 0) return;
  for (uint32_t j = 0; j < m; j++) {
    const double x = x0 + static_cast<double>(j) * dx;
    if (n == 1 || x <= 0.0) {
      saida[j] = v[0];
      continue;
    }
    if (x >= static_cast<double>(n - 1)) {
      saida[j] = v[n - 1];
      continue;
    }
    const double piso = floor(x);
    const uint32_t i = static_cast<uint32_t>(piso);
    const double fr = x - piso;
    const double a = static_cast<double>(v[i]);
    const double b = static_cast<double>(v[i + 1]);
    saida[j] = static_cast<float>(a + (b - a) * fr);
  }
}

}  // namespace dormio
