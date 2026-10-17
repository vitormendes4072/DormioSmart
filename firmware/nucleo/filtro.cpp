#include "filtro.h"

#include <math.h>

namespace dormio {

// Q = 1/sqrt(2) e o que define Butterworth entre os filtros de 2a ordem. Aqui
// ele aparece como `q = sqrt(2)` porque entra multiplicando `k` no
// denominador -- e a mesma constante escrita do outro lado da fracao. Esta
// linha e `q = math.sqrt(2.0)` em `_biquad_butter2`; sao a mesma constante e
// e por isso que os coeficientes batem.
static const double RAIZ_DE_DOIS = 1.4142135623730951;

// `M_PI` e POSIX, nao ISO, e o Makefile compila com `-std=c++11` (e nao
// `gnu++11`): em modo estrito a `math.h` da glibc NAO define M_PI. Ja foi
// motivo de build quebrado em toolchain mais arisca, entao a constante vem
// escrita. Os digitos sao os de `double` -- o mesmo valor que `math.pi` do
// Python, que e o que a referencia usa.
static const double PI = 3.141592653589793;

bool filtro_aplicavel(float fs, float corte_hz) {
  if (!(fs > 0.0f) || !(corte_hz > 0.0f)) return false;
  // Estritamente abaixo de Nyquist: em fs/2 o prewarp `tan(pi/2)` estoura.
  return corte_hz < fs * 0.5f;
}

CoeficientesBiquad coeficientes_butterworth2(float fs, float corte_hz) {
  // Em DOUBLE de ponta a ponta -- ver a nota longa em `CoeficientesBiquad`.
  //
  // Sao cinco numeros calculados UMA VEZ por epoca (ou, na pratica, uma vez
  // por execucao, porque `fs` nao muda no meio de uma noite), contra 960
  // amostras x 3 eixos x 2 passagens que depois usam esses cinco numeros. O
  // custo de calcula-los em double e irrelevante no orcamento de 30 s, e o
  // beneficio e direto: `tan` perto de zero e a divisao por
  // (1 + q*k + k*k) sao onde um erro de coeficiente entraria, e um erro NO
  // COEFICIENTE nao se cancela -- ele se aplica identicamente a todas as
  // amostras, virando um vies no estimador de gravidade, que e exatamente o
  // tipo de divergencia que nao aparece como ruido e sim como fórmula
  // diferente.
  //
  // A referencia em Python calcula em float64. Calcular aqui em float32
  // introduziria uma diferenca de coeficiente de ~1e-7 relativo que seria
  // indistinguivel de "o firmware usa outro corte". Em double ela desaparece,
  // e o que sobra na comparacao e so o que se quer medir: o residuo de borda.
  const double k = tan(PI * static_cast<double>(corte_hz) / static_cast<double>(fs));
  const double kk = k * k;
  const double norma = 1.0 / (1.0 + RAIZ_DE_DOIS * k + kk);

  CoeficientesBiquad c;
  const double b0 = kk * norma;
  c.b0 = b0;
  c.b1 = 2.0 * b0;
  c.b2 = b0;
  c.a1 = 2.0 * (kk - 1.0) * norma;
  c.a2 = (1.0 - RAIZ_DE_DOIS * k + kk) * norma;
  return c;
}

// Uma passagem causal do biquad sobre `v`, no lugar, com o estado
// inicializado em regime permanente da PRIMEIRA amostra percorrida.
//
// `passo` vale +1 para ler na ordem e -1 para ler ao contrario: e assim que a
// passagem de volta acontece sem ninguem precisar inverter o vetor na memoria.
//
// ⚠️ O acumulador e `double` e os coeficientes sao `float`. A conta e a mesma
// que o Python faz, mas sem o erro de arredondamento se acumulando pelos 960
// passos da recursao -- e numa recursao de 2a ordem o erro NAO e independente
// amostra a amostra: `y[n]` realimenta `y[n-1]` e `y[n-2]`, entao o erro
// circula pelo proprio filtro. Em float32 ele e pequeno mas correlacionado, o
// que e a pior forma para um estimador de media (ele nao se cancela no
// somatorio de `g`). O double custa nada aqui: num ESP32 sem FPU de dupla
// precisao sao 960 operacoes em software por eixo por passagem, dentro de um
// orcamento de 30 segundos.
static void passagem(float *v, uint32_t n, const CoeficientesBiquad &c,
                     int32_t passo) {
  const uint32_t primeiro = (passo > 0) ? 0u : (n - 1u);

  // Regime permanente: entrada constante `v[0]` com ganho unitario em DC
  // produz saida `v[0]`. Esta e a unica diferenca de estimador em relacao ao
  // `filtfilt` do scipy, e esta documentada no topo de filtro.h.
  const double v0 = static_cast<double>(v[primeiro]);
  double x1 = v0, x2 = v0, y1 = v0, y2 = v0;

  const double b0 = c.b0, b1 = c.b1, b2 = c.b2, a1 = c.a1, a2 = c.a2;

  uint32_t i = primeiro;
  for (uint32_t contados = 0; contados < n; contados++) {
    // Le ANTES de escrever. E o que torna a passagem segura no lugar.
    const double amostra = static_cast<double>(v[i]);
    const double y = b0 * amostra + b1 * x1 + b2 * x2 - a1 * y1 - a2 * y2;
    x2 = x1;
    x1 = amostra;
    y2 = y1;
    y1 = y;
    v[i] = static_cast<float>(y);
    i = static_cast<uint32_t>(static_cast<int64_t>(i) + passo);
  }
}

bool filtrar_ida_e_volta(float *v, uint32_t n, float fs, float corte_hz) {
  if (v == 0) return false;
  if (n < 2) return false;
  if (!filtro_aplicavel(fs, corte_hz)) return false;

  const CoeficientesBiquad c = coeficientes_butterworth2(fs, corte_hz);

  // Ida: ordem natural.
  passagem(v, n, c, +1);
  // Volta: ordem inversa.
  //
  // A inversao dupla do Python (`_passagem(ida[::-1])` e depois `[::-1]`)
  // equivale a percorrer de tras para frente escrevendo no mesmo indice --
  // que e o que `passo = -1` faz. Nenhuma copia, nenhum vetor invertido na
  // memoria, e o resultado e indice a indice o mesmo.
  passagem(v, n, c, -1);
  return true;
}

}  // namespace dormio
