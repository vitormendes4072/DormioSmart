// filtro.h -- passa-baixa Butterworth de 2a ordem aplicado IDA E VOLTA.
//
// Separa a gravidade da aceleracao dinamica. E o estimador de que dependem
// `mag_din_media`, `p_frac` e o proprio vetor `g` transmitido -- ou seja, tres
// dos sete numeros que o dispositivo emite por epoca, e os dois que o servidor
// deriva depois. Se este arquivo divergir do Python, divergem todos.
//
// ── POR QUE NAO E O MESMO FILTRO DO SCIPY, E POR QUE ISSO ESTA CERTO ───
//
// A referencia em Python e `scipy.signal.filtfilt(butter(2, 0.25/(fs/2)), a)`.
// O `filtfilt` do scipy NAO e so "rodar o biquad nos dois sentidos": antes de
// filtrar ele ESTENDE o sinal nas duas bordas por REFLEXAO IMPAR
// (`padtype="odd"`, `padlen = 3*max(len(a), len(b)) = 9` amostras por
// padrao), filtra o sinal estendido e descarta as extensoes. A reflexao impar
// de um sinal `x` em torno da borda `x[0]` e `2*x[0] - x[k]`: ela continua o
// sinal de um jeito que preserva a inclinacao na borda em vez de criar um
// degrau.
//
// Este modulo NAO faz isso. Ele roda um biquad causal de 2a ordem na ida,
// inverte, roda o mesmo biquad na volta, e inverte de novo. Nas bordas, em vez
// de extensao, ele INICIALIZA O ESTADO EM REGIME PERMANENTE: para uma entrada
// constante `v[0]`, a saida de um passa-baixa de ganho unitario em DC tambem e
// `v[0]`, entao comecar com `x1 = x2 = y1 = y2 = v[0]` e equivalente a dizer
// "antes da primeira amostra, o sinal estava parado neste valor". Sem isso o
// filtro "liga" do zero e produz um transiente de ~meio segundo exatamente
// onde a epoca comeca -- e com a gravidade valendo ~1 g, um transiente que sai
// de 0 e um erro de 1 g na primeira decima de segundo da janela.
//
// As duas estrategias concordam no meio da janela e discordam nas bordas. A
// discordancia NAO e arredondamento: sao dois estimadores diferentes, e a
// diferenca foi MEDIDA em vez de estimada (DATA-07c, 200 sementes):
//
//     mag_din_media ....... p95 0,99 %   maximo 1,43 %   (tolerancia 4 %)
//     direcao de `g` ...... p50 0,017    p95 0,054       maximo 0,082 grau
//                                                        (tolerancia 0,25)
//
// E o residuo de borda que domina o piso de tolerancia do item inteiro -- nao
// o float32, que contribui com 1,2e-4 grau. Quem apertar essas tolerancias
// esta apertando contra ESTA escolha, e a saida seria implementar a reflexao
// impar aqui, nao mexer na constante.
//
// ── POR QUE NAO IMPLEMENTAR A REFLEXAO IMPAR, ENTAO ───────────────────
//
// Ela custaria 9 amostras de extensao em cada ponta -- barato. O que pesa e
// que ela NAO ELIMINA a divergencia, so a reduz: o `filtfilt` do scipy usa
// `lfilter_zi` para inicializar o estado em regime permanente DO SINAL
// ESTENDIDO, e reproduzir `lfilter_zi` exige resolver o sistema linear
// (I - A) zi = B no estado do biquad. Da para fazer em forma fechada para
// ordem 2, mas ai o firmware passa a carregar uma reimplementacao de um
// detalhe interno do scipy, que muda de versao sem avisar -- e a divergencia
// volta, agora silenciosa, porque ninguem estaria mais olhando.
//
// A escolha registrada e a oposta: manter o estimador do firmware SIMPLES e
// EXPLICADO, e declarar a divergencia com numero medido. Uma tolerancia de
// 4 % derivada entre piso e teto e verificavel; uma igualdade bit a bit que
// depende da versao do scipy nao e.
//
// ── A FORMA FECHADA DOS COEFICIENTES ──────────────────────────────────
//
// Os coeficientes sao EXATAMENTE os de `butter(2, corte/(fs/2), "low")`:
// prewarp por tangente (`k = tan(pi*fc/fs)`) seguido de transformada
// bilinear, com Q = 1/sqrt(2) (que e o que faz o filtro ser Butterworth e nao
// outro de 2a ordem). Escrever a forma fechada aqui e de proposito: o ESP32
// nao ganha uma dependencia de biblioteca de DSP, e o mesmo texto de doze
// linhas pode ser comparado com `_biquad_butter2` do vetor dourado lado a
// lado.
//
// ⚠️ A ordem efetiva e 4, nao 2. Duas passagens de um biquad de 2a ordem dao,
// em MAGNITUDE, |H(w)|^2 -- o mesmo que o `filtfilt` faz com `butter(2, ...)`,
// que tambem dobra a ordem efetiva. A referencia em Python e o firmware
// concordam nisso; o que diverge e so a borda.

#ifndef DORMIO_NUCLEO_FILTRO_H
#define DORMIO_NUCLEO_FILTRO_H

#include <stdint.h>

namespace dormio {

// Corte do passa-baixa que separa gravidade de aceleracao dinamica, em Hz.
//
// 0,25 Hz NAO e escolhido aqui: e o valor de `CORTE_GRAVIDADE_HZ` em
// `ml/src/features.py`, e os dois lados TEM de usar o mesmo numero ou a
// paridade nao significa nada. A justificativa (a gravidade e quase-DC; o
// movimento humano tem energia predominante em 0,3-3,5 Hz) esta la.
const float CORTE_GRAVIDADE_HZ = 0.25f;

// Coeficientes de um biquad passa-baixa de 2a ordem, forma direta I.
//
//   y[n] = b0*x[n] + b1*x[n-1] + b2*x[n-2] - a1*y[n-1] - a2*y[n-2]
//
// `a0` nao aparece porque os cinco ja saem normalizados por ele.
//
// ⚠️ SAO `double`, E ISSO FOI MEDIDO, NAO ESCOLHIDO POR GOSTO.
//
// A primeira versao guardava os cinco em `float`, com o argumento de que o
// ESP32 nao tem FPU de dupla precisao. O teste de ganho DC reprovou: o ganho
// em corrente continua de um passa-baixa tem de ser exatamente 1, e saiu
// **1,0000120**.
//
// A causa e cancelamento catastrofico na propria expressao do ganho:
//
//     H(1) = (b0+b1+b2) / (1 + a1 + a2)
//     1 + a1 + a2 = 1 - 1,93060643 + 0,93293473 = 0,00232830
//
// O denominador perde quase tres ordens de grandeza na soma. Em float32 cada
// coeficiente carrega ~1e-7 de erro relativo, e 1e-7 sobre 0,0023 e 4,3e-5 --
// que e a ordem exata do desvio observado.
//
// Por que isso importa, em termos fisicos: um ganho DC de 1,000012 escala a
// GRAVIDADE ESTIMADA por 1,000012. Sobre ~1 g isso e um erro de 1,2e-5 g que
// entra em `||a - g||`, cujos valores tipicos sao ~24 mg -- ou seja ~0,05 %
// de `mag_din_media`, de forma SISTEMATICA e nao aleatoria. Nao reprovaria a
// tolerancia de 4 %, mas e vies de estimador, nao ruido: ele nao se cancela
// no somatorio e nao apareceria como divergencia obvia.
//
// E o custo de corrigir e ZERO. O laco interno de `passagem` ja acumula em
// `double` (pelo motivo documentado la), entao os coeficientes em `float`
// eram promovidos a `double` em toda multiplicacao de qualquer maneira. Eram
// float truncado promovido a double -- o pior dos dois mundos. Com `double`
// desde a origem, o ganho DC fecha em ~1e-16 e o sinal constante atravessa o
// filtro inalterado.
struct CoeficientesBiquad {
  double b0, b1, b2, a1, a2;
};

// Calcula os coeficientes de Butterworth para `corte_hz` em `fs` Hz.
//
// Pre-condicao: 0 < corte_hz < fs/2. Fora disso o prewarp por tangente
// estoura (em fs/2 a tangente vai a infinito) e o resultado nao e um filtro.
// O chamador confere -- aqui nao ha excecao para lancar, e devolver um filtro
// invalido em silencio seria pior que um estouro.
CoeficientesBiquad coeficientes_butterworth2(float fs, float corte_hz);

// Verdadeiro se o par (fs, corte) produz um filtro valido.
bool filtro_aplicavel(float fs, float corte_hz);

// Aplica o filtro IDA E VOLTA sobre `n` amostras, NO LUGAR e SEM RASCUNHO.
//
// `v` e entrada e saida, e nao ha segundo vetor. Isso nao e um truque: na
// forma direta I as duas entradas passadas (`x[n-1]`, `x[n-2]`) ficam em
// variaveis LOCAIS, nao sao relidas do vetor. Cada passo le `v[i]` para uma
// local antes de escrever `v[i]`, entao sobrescrever a propria posicao e
// seguro, e a recursao continua vendo exatamente o historico que veria com
// dois vetores separados.
//
// A referencia em Python escreve numa lista nova (`saida = [0.0]*len(v)`), mas
// a conta e a mesma pelo mesmo motivo -- `x1`/`x2` sao locais la tambem. A
// unica coisa que a versao no lugar economiza e memoria: 3,8 KB de rascunho
// por epoca de 960 amostras, numa camada que tem de caber ao lado de um
// buffer de 32 KiB.
//
// Devolve false (e nao toca em `v`) se `n < 2` ou se o filtro nao e aplicavel.
// n = 1 nao e erro de programacao, e epoca de uma amostra: filtrar nao
// significa nada ali, e o chamador ja vai recusar a epoca por tamanho.
bool filtrar_ida_e_volta(float *v, uint32_t n, float fs, float corte_hz);

}  // namespace dormio

#endif  // DORMIO_NUCLEO_FILTRO_H
