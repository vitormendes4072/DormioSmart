// capacidade.cpp -- MEDE a capacidade do buffer, em vez de estimar.
//
// A diferenca importa. "Uns 32 bytes por epoca, uns 4 KB de RTC, deve dar
// umas duas horas" e o tipo de conta que se defende mal e que erra por um
// fator de dois sem ninguem notar. Aqui o numero sai de `sizeof` do registro
// real e de uma SIMULACAO da degradacao -- o buffer de verdade, enchendo de
// verdade, ate o teto do contrato.
//
// Por que `sizeof` no host vale para o ESP32: os campos de `Epoca` tem largura
// fixa (`uint32_t`, `float`, `uint16_t`, `uint8_t`) e estao em ordem
// decrescente de alinhamento, entao nao ha padding em nenhum dos dois ABIs. O
// `static_assert` em `epoca.cpp` trava o tamanho: se alguem acrescentar um
// campo, o build quebra antes de esta medicao passar a mentir.

#include <stdio.h>

#include "buffer.h"
#include "epoca.h"

using namespace dormio;

struct Orcamento {
  const char *nome;
  uint32_t bytes;
  const char *nota;
};

static void linha() {
  printf("+---------------------------+--------+--------+-----------+-----------+\n");
}

// Simula encher um buffer de `capacidade` posicoes com epocas de 30 s ate
// nao caber mais, e devolve as horas cobertas.
template <uint32_t N>
static double horas_ate_saturar(uint32_t *nivel_max, uint32_t *epocas_aceitas) {
  BufferDeEpocas<N> b;
  b.definir_limiar(75);
  uint32_t i = 0;
  for (; i < 2000000u; i++) {
    Epoca e;
    e.indice = i;
    e.pico_total = 9.85f;
    e.pico_az = 9.85f;
    e.temp_pico = 25.0f;
    e.amostras = 3;
    e.esperadas = 3;
    if (!b.guardar(e)) break;
  }
  *nivel_max = b.estatisticas().nivel_maximo;
  *epocas_aceitas = i;
  return b.horas_cobertas();
}

int main() {
  printf("\nCAPACIDADE DO BUFFER DE EPOCAS -- medida, nao estimada\n");
  printf("=====================================================\n\n");

  printf("Registro de epoca: %u bytes\n", static_cast<unsigned>(sizeof(Epoca)));
  printf("  indice      %2u B   grade absoluta de 30 s\n",
         static_cast<unsigned>(sizeof(uint32_t)));
  printf("  pico        %2u B   total + ax/ay/az + temperatura\n",
         static_cast<unsigned>(5 * sizeof(float)));
  printf("  contagens   %2u B   amostras, esperadas, duracao\n",
         static_cast<unsigned>(3 * sizeof(uint16_t)));
  printf("  nivel+flags %2u B\n\n", static_cast<unsigned>(2 * sizeof(uint8_t)));

  printf("Sem o giroscopio (12 B, opcional desde o contrato v2.0.0 e usado por\n");
  printf("nenhum criterio), o registro ficaria em 44 B: 37%% a mais por epoca,\n");
  printf("37%% menos horas de autonomia offline.\n\n");

  const Orcamento orcamentos[] = {
      {"RTC slow (deep sleep)", 4096, "sobrevive ao Deep Sleep; ~8 KB no total, metade reservada"},
      {"RTC slow, folgado", 6144, "teto pratico depois do bootloader"},
      {"heap, conservador", 32768, "envio-continuo nao dorme: pode usar heap"},
      {"heap, generoso", 131072, "ESP32 tem ~300 KB livres"},
  };

  printf("EPOCAS DE 30 s, SEM DEGRADACAO (resolucao cheia)\n");
  linha();
  printf("| %-25s | %6s | %6s | %9s | %9s |\n", "orcamento", "bytes", "epocas",
         "horas", "");
  linha();
  for (unsigned i = 0; i < sizeof(orcamentos) / sizeof(orcamentos[0]); i++) {
    uint32_t n = orcamentos[i].bytes / sizeof(Epoca);
    double horas = (n * 30.0) / 3600.0;
    printf("| %-25s | %6u | %6u | %7.2f h | %9s |\n", orcamentos[i].nome,
           orcamentos[i].bytes, n, horas, "");
  }
  linha();

  printf("\nCOM DEGRADACAO ATE O TETO DO CONTRATO (epoca_s <= 3600 s -> nivel 6)\n");
  linha();
  printf("| %-25s | %6s | %6s | %9s | %9s |\n", "orcamento", "bytes", "epocas",
         "horas", "nivel max");
  linha();

  uint32_t nivel, aceitas;
  double h;

  h = horas_ate_saturar<128>(&nivel, &aceitas);  // 4096 / 32
  printf("| %-25s | %6u | %6u | %7.2f h | %9u |\n", "RTC slow (deep sleep)", 4096u,
         128u, h, nivel);

  h = horas_ate_saturar<192>(&nivel, &aceitas);  // 6144 / 32
  printf("| %-25s | %6u | %6u | %7.2f h | %9u |\n", "RTC slow, folgado", 6144u, 192u,
         h, nivel);

  h = horas_ate_saturar<1024>(&nivel, &aceitas);  // 32768 / 32
  printf("| %-25s | %6u | %6u | %7.2f h | %9u |\n", "heap, conservador", 32768u,
         1024u, h, nivel);

  h = horas_ate_saturar<4096>(&nivel, &aceitas);  // 131072 / 32
  printf("| %-25s | %6u | %6u | %7.2f h | %9u |\n", "heap, generoso", 131072u, 4096u,
         h, nivel);
  linha();

  printf("\nLEITURA\n");
  printf("-------\n");
  printf("A coluna \"horas\" da segunda tabela e o tempo que o aparelho aguenta SEM\n");
  printf("REDE NENHUMA antes de comecar a perder dado de verdade. A primeira tabela\n");
  printf("e o tempo que ele aguenta sem perder RESOLUCAO.\n\n");
  printf("Entre as duas ha uma faixa larga em que o dado continua inteiro e so a\n");
  printf("granularidade piora -- que e o ponto do buffer ser de epocas e nao de\n");
  printf("amostras. Com amostras instantaneas essa faixa nao existe: passou do\n");
  printf("limite, perde-se dado.\n\n");

  printf("ESCOLHA PARA O envio-continuo: 1024 epocas (32 KB de heap).\n");
  printf("  Cobre uma noite de 8 h em resolucao CHEIA de 30 s, sem degradar uma vez\n");
  printf("  sequer, e ainda sobra margem. A placa nao dorme nesse sketch, entao nao\n");
  printf("  ha razao para espremer no RTC.\n\n");
  printf("ESCOLHA PARA O sketch.ino (quando ele for reescrito -- item FW-07):\n");
  printf("  128 epocas no RTC, porque ali o buffer precisa SOBREVIVER ao Deep Sleep\n");
  printf("  e o heap nao sobrevive. Uma hora em resolucao cheia, a noite inteira\n");
  printf("  em resolucao degradada.\n\n");

  printf("CUSTO DE DRENAR (dimensiona o backoff)\n");
  printf("--------------------------------------\n");
  double epocas_8h = (8.0 * 3600.0) / 30.0;
  printf("  8 h de buffer = %.0f epocas = %.0f POSTs, um handshake TLS cada.\n",
         epocas_8h, epocas_8h);
  printf("  A 10 s de cadencia seriam %.0f POSTs se o buffer fosse de AMOSTRAS --\n",
         (8.0 * 3600.0) / 10.0);
  printf("  agregar por epoca ja divide por 3. Quando o FW-05 subir a amostragem\n");
  printf("  para >= 42 Hz, seriam 1,2 milhao de amostras e continuariam sendo %.0f\n",
         epocas_8h);
  printf("  epocas: e a agregacao, nao o buffer, que torna a drenagem possivel.\n\n");
  printf("  Mesmo assim %.0f POSTs sequenciais sao caros. Dai duas decisoes:\n", epocas_8h);
  printf("  (a) drenagem em RAJADA LIMITADA, devolvendo o controle ao laco entre\n");
  printf("      pedacos, para a cadencia nao ser comida pela drenagem;\n");
  printf("  (b) o item API-03 no backlog: endpoint de lote no backend.\n\n");

  return 0;
}
