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
#include "caracteristicas.h"
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
  // ✏️ 30/10: esta escolha era "128 epocas no RTC, porque o buffer precisa
  // sobreviver ao Deep Sleep". O ARQ-01 decidiu a C2, em sono leve, que
  // preserva a RAM -- e o texto impresso seguiu dizendo o contrario.
  printf("ESCOLHA PARA O sketch.ino (FW-07, arquitetura C2 do ARQ-01):\n");
  printf("  heap, como no envio-continuo: em SONO LEVE a RAM sobrevive. O registro\n");
  printf("  duravel vai para a flash (FW-08). As linhas do RTC acima ficam como\n");
  printf("  medida -- eram a escolha do desenho antigo, em Deep Sleep.\n\n");

  // ══════════════════════════════════════════════════════════════════
  // RECALCULO DA AUTONOMIA DEPOIS DO DATA-07b
  // ══════════════════════════════════════════════════════════════════
  //
  // O estudo do buffer (`docs/DECISAO-BUFFER-E-FEATURES.md`) dimensionou um
  // registro de 40 B carregando as features. A implementacao do `DATA-07b`
  // NAO chegou a 40 B, e a diferenca esta medida abaixo em vez de escondida.
  printf("AUTONOMIA COM AS FEATURES (recalculo do DATA-07b)\n");
  printf("------------------------------------------------\n");
  const uint32_t b_epoca = static_cast<uint32_t>(sizeof(Epoca));
  const uint32_t b_feat = static_cast<uint32_t>(sizeof(VetorDeFeatures));
  const uint32_t b_par = b_epoca + b_feat;
  printf("  sizeof(Epoca) ............. %2u B   (inalterado -- o static_assert\n", b_epoca);
  printf("                                     de epoca.cpp continua travado)\n");
  printf("  sizeof(VetorDeFeatures) ... %2u B   6 x u16 + 3 x i16\n", b_feat);
  printf("  pareamento implementado ... %2u B\n", b_par);
  printf("  layout D do estudo ........ 40 B   (picos tambem quantizados)\n");
  printf("  diferenca ................. %2u B   = os 5 floats de pico que o\n",
         b_par - 40u);
  printf("                                     layout D converte em 2+6+2 B\n\n");

  printf("  Em memoria o pareamento alinha em %u B (o compilador alinha o par\n",
         static_cast<unsigned>(((b_par + 3u) / 4u) * 4u));
  printf("  em 4 B, como `Epoca`), que e o numero que dimensiona o buffer.\n\n");

  struct Variante {
    const char *nome;
    uint32_t bytes;
  };
  const Variante variantes[3] = {
      {"A. hoje, sem features", b_epoca},
      {"D. estudo (picos quantizados)", 40u},
      {"IMPLEMENTADO (Epoca + features)", ((b_par + 3u) / 4u) * 4u}};

  linha();
  printf("| %-25s | %6s | %6s | %9s | %9s |\n", "registro", "bytes", "epocas",
         "32 KiB", "1,5 MiB");
  linha();
  for (unsigned i = 0; i < 3; i++) {
    const uint32_t n32 = 32768u / variantes[i].bytes;
    const double h32 = (n32 * 30.0) / 3600.0;
    const uint32_t nflash = (1536u * 1024u) / variantes[i].bytes;
    const double hflash = (nflash * 30.0) / 3600.0;
    printf("| %-25s | %6u | %6u | %7.2f h | %7.1f h |\n", variantes[i].nome,
           variantes[i].bytes, n32, h32, hflash);
  }
  linha();
  printf("\n  CUSTO DA DECISAO: o pareamento implementado custa %.2f h de heap\n",
         (32768.0 / 40.0 - 32768.0 / (((b_par + 3u) / 4u) * 4u)) * 30.0 / 3600.0);
  printf("  (32 KiB) contra o layout D -- %.0f%% menos autonomia em resolucao\n",
         100.0 * (1.0 - (32768.0 / (((b_par + 3u) / 4u) * 4u)) / (32768.0 / 40.0)));
  printf("  cheia. Em flash a diferenca e de %.0f h.\n\n",
         (1536.0 * 1024.0 / 40.0 - 1536.0 * 1024.0 / (((b_par + 3u) / 4u) * 4u)) *
             30.0 / 3600.0);
  // ⚠️ A CONSEQUENCIA QUE NAO E SO "MENOS MARGEM". Vale escrever com
  // cuidado, porque a primeira versao deste texto dizia "isso continua
  // cobrindo a noite" -- e 5,25 h nao cobrem 8 h. Cobre com DEGRADACAO, e a
  // degradacao tem um preco novo que o layout A nao tinha.
  const double h_cheia = (32768.0 / (((b_par + 3u) / 4u) * 4u)) * 30.0 / 3600.0;
  printf("  ⚠️ A CONSEQUENCIA NAO E SO MARGEM. Com 32 B o buffer de 32 KiB\n");
  printf("  cobria 8,53 h -- uma noite de 8 h cabia INTEIRA em resolucao\n");
  printf("  cheia, sem degradar uma vez. Com %u B cobre %.2f h, entao numa\n",
         (((b_par + 3u) / 4u) * 4u), h_cheia);
  printf("  noite de 8 h sem rede a degradacao PASSA A SER ACIONADA -- cerca\n");
  printf("  de %.2f h de dado precisam ser fundidos.\n\n", 8.0 - h_cheia);
  printf("  E epoca degradada NAO TEM FEATURES: `mag_din_media`, `zcr` e `g`\n");
  printf("  nao fundem (a janela do filtro muda, o `zcr` e relativo a media da\n");
  printf("  propria janela, e `g` guardado e so a direcao unitaria). Ver a nota\n");
  printf("  longa no topo de caracteristicas.h. Ou seja: numa noite inteira sem\n");
  printf("  rede, o inicio da noite chega ao servidor SEM vetor de\n");
  printf("  caracteristicas -- com `total`/`status`, como hoje, mas sem `f`.\n\n");
  printf("  Isso nao e perda de dado silenciosa (a epoca viaja marcada\n");
  printf("  EPOCA_DEGRADADA e o contrato ja diz que `f` e opcional), mas E uma\n");
  printf("  perda de COBERTURA DE FEATURES que o layout D de 40 B reduziria e o\n");
  printf("  layout A de 32 B nem teria. E o argumento mais forte a favor de\n");
  printf("  quantizar os picos, e esta registrado como tal.\n\n");
  printf("  Por que nao foi feito junto, ainda assim: quantizar os picos mexe\n");
  printf("  na precisao TRANSMITIDA (ax/ay/az/total do payload) e na checagem\n");
  printf("  de coerencia da secao 5.1 do contrato. Juntar as duas mudancas\n");
  printf("  tornaria impossivel dizer qual delas quebrou o que -- e a suite de\n");
  printf("  payload que hoje passa e o que garante que a primeira nao quebrou\n");
  printf("  nada.\n\n");

  // ── O custo que o estudo do buffer NAO tinha como prever ──
  printf("CUSTO DE RAM DO ACUMULADOR (achado novo do DATA-07b)\n");
  printf("---------------------------------------------------\n");
  printf("  sizeof(AcumuladorDeFeatures) = %u B (%.1f KiB)\n",
         static_cast<unsigned>(sizeof(AcumuladorDeFeatures)),
         static_cast<double>(sizeof(AcumuladorDeFeatures)) / 1024.0);
  printf("\n  O estudo do buffer dimensionou o ARMAZENAMENTO das features e nao\n");
  printf("  tinha como orcar o CALCULO delas -- nao havia implementacao para\n");
  printf("  medir. Este numero e o achado:\n\n");
  printf("  O filtro de gravidade e de FASE ZERO, aplicado ida e volta. A\n");
  printf("  passagem de volta le a janela do fim para o comeco, entao a\n");
  printf("  gravidade na amostra 0 depende da amostra 959. NAO EXISTE forma\n");
  printf("  O(1) de calcular isto em streaming: um acumulador incremental\n");
  printf("  seria um filtro CAUSAL, ou seja outro estimador, com divergencia\n");
  printf("  nao declarada. A janela inteira em RAM e imposta pela matematica,\n");
  printf("  nao por conveniencia.\n\n");
  printf("  %.1f KiB sao %.0f%% do orcamento de heap \"conservador\" (32 KiB) que\n",
         static_cast<double>(sizeof(AcumuladorDeFeatures)) / 1024.0,
         100.0 * static_cast<double>(sizeof(AcumuladorDeFeatures)) / 32768.0);
  printf("  este estudo usou para o buffer. Os dois NAO competem pelo mesmo\n");
  printf("  orcamento -- o ESP32 tem ~300 KB livres e o acumulador e um bloco\n");
  printf("  estatico, nao heap fragmentavel --, mas o total de RAM do sketch\n");
  printf("  sobe ~%.0f KB e isso precisa estar escrito antes de alguem medir\n",
         static_cast<double>(sizeof(AcumuladorDeFeatures)) / 1024.0);
  printf("  na placa e se surpreender.\n\n");

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
  printf("  (b) o endpoint de lote, POST /api/data/lote (API-03, fechado em 30/10),\n");
  printf("      ate 60 leituras por requisicao; o cliente dele e o lote.h (FW-07).\n\n");

  return 0;
}
