// testes_c2.cpp -- as pecas da arquitetura C2 (FW-07), uma a uma.
//
// A paridade da cadeia inteira contra o `ml/` mora em `testes_cadeia_c2.cpp`,
// que precisa do dourado. Aqui ficam as propriedades que nao dependem dele:
// o que os bytes da FIFO significam, o que o filtro deixa passar, quando a
// cadeia recusa uma epoca, e como a resposta do lote vira epocas fora da fila.

#include <math.h>
#include <stdio.h>
#include <string.h>

#include "../buffer.h"
#include "../cadeia_c2.h"
#include "../epoca.h"
#include "../fifo_mpu.h"
#include "../filtro.h"
#include "../lote.h"
#include "../payload.h"
#include "../reamostragem.h"

using namespace dormio;

static int falhas = 0;
static int total = 0;

#define VERIFICAR(cond, msg)                                              \
  do {                                                                    \
    total++;                                                              \
    if (!(cond)) {                                                        \
      falhas++;                                                           \
      printf("  FALHOU  %s\n          (%s:%d)  %s\n", msg, __FILE__,      \
             __LINE__, #cond);                                            \
    }                                                                     \
  } while (0)

#define VERIFICAR_PROX(a, b, tol, msg) VERIFICAR(fabs((a) - (b)) <= (tol), msg)

static void secao(const char *nome) { printf("\n== %s\n", nome); }

// ── FIFO ──────────────────────────────────────────────────────────────

static void testar_registradores_da_c2() {
  secao("fifo -- os valores que o sketch escreve");
  VERIFICAR(taxa_nominal_hz(C2_SMPLRT_DIV) == 50.0f, "1 kHz / (1 + 19) = 50 Hz");
  VERIFICAR(TAXA_NOMINAL_C2_HZ == taxa_nominal_hz(C2_SMPLRT_DIV),
            "a cadeia assume a taxa que o divisor produz");
  VERIFICAR(FIFO_CAPACIDADE_AMOSTRAS == 170, "1024 B / 6 B = 170 amostras inteiras");
  VERIFICAR(C2_ACCEL_CONFIG == 0x10, "AFS_SEL = 2 (+-8 g) nos bits 4:3");
  VERIFICAR(C2_FIFO_EN == 0x08, "so ACCEL_FIFO_EN");
  VERIFICAR(C2_DLPF_CFG == 4, "DLPF de 21 Hz, o do FW-06");
  // O intervalo de drenagem tem de deixar folga na FIFO no pior caso: oscilador
  // a +10 % e o intervalo no maximo da variacao, mais a latencia de despertar.
  const double pior_s = (INTERVALO_DE_DRENAGEM_US + VARIACAO_DA_DRENAGEM_US) / 1e6 + 0.003;
  VERIFICAR(pior_s * 50.0 * 1.10 < FIFO_CAPACIDADE_AMOSTRAS,
            "drenar a cada ~1,7 s nao transborda nem com o oscilador a +10 %");
}

static void testar_avaliar_fifo() {
  secao("fifo -- quando a leitura nao merece confianca");
  VERIFICAR(avaliar_fifo(510, 0) == LEITURA_OK, "85 amostras inteiras");
  VERIFICAR(avaliar_fifo(0, 0) == LEITURA_OK, "vazia e leitura valida (nada a ler)");
  VERIFICAR(avaliar_fifo(510, MPU_INT_STATUS_FIFO_OFLOW) == LEITURA_TRANSBORDOU,
            "o bit de transbordo manda, mesmo com contagem plausivel");
  VERIFICAR(avaliar_fifo(1024, 0) == LEITURA_TRANSBORDOU,
            "contagem no teto e transbordo mesmo sem o bit");
  VERIFICAR(avaliar_fifo(511, 0) == LEITURA_DESALINHADA, "nao multiplo de 6");
  VERIFICAR(bytes_para_ler(515, 1024) == 510, "arredonda para baixo em amostras");
  VERIFICAR(bytes_para_ler(600, 256) == 252, "respeita o buffer de quem chama");
}

static void testar_decodificar_fifo() {
  secao("fifo -- os bytes sao int16 big-endian, X Y Z");
  const uint8_t bytes[13] = {0x10, 0x00, 0xF0, 0x00, 0x7F, 0xFF,
                             0x80, 0x00, 0x00, 0x01, 0xFF, 0xFF, 0xAA};
  AmostraBruta a[4];
  VERIFICAR(decodificar_fifo(bytes, 13, a, 4) == 2, "13 bytes = 2 amostras; o 13o sobra");
  VERIFICAR(a[0].x == 4096 && a[0].y == -4096 && a[0].z == 32767, "primeira amostra");
  VERIFICAR(a[1].x == -32768 && a[1].y == 1 && a[1].z == -1, "extremos e sinal");
  VERIFICAR(lsb_para_g(4096) == 1.0f, "4096 LSB = 1 g em +-8 g");
  VERIFICAR(lsb_para_g(-32768) == -8.0f, "fundo de escala = -8 g");
  VERIFICAR(decodificar_fifo(bytes, 12, a, 1) == 1, "nao escreve alem da capacidade");
  VERIFICAR(decodificar_fifo(0, 12, a, 4) == 0, "ponteiro nulo nao e amostra");
}

// ── Reamostragem ──────────────────────────────────────────────────────

static void testar_secao_reproduz_o_butterworth2() {
  secao("anti-aliasing -- a secao generica com Q = 1/sqrt(2) e o filtro de sempre");
  const CoeficientesBiquad a = coeficientes_secao(50.0f, 12.8f, 0.70710678118654752);
  const CoeficientesBiquad b = coeficientes_butterworth2(50.0f, 12.8f);
  VERIFICAR(fabs(a.b0 - b.b0) < 1e-15 && fabs(a.a1 - b.a1) < 1e-15 &&
                fabs(a.a2 - b.a2) < 1e-15,
            "mesmos coeficientes -- uma forma fechada so");
  VERIFICAR_PROX(CORTE_ANTIALIASING_HZ, 12.8f, 1e-6, "0,8 x Nyquist de 32 Hz");
  VERIFICAR_PROX(Q_SECAO_1, 1.0 / (2.0 * cos(3.141592653589793 / 8.0)), 1e-15, "Q da secao 1");
  VERIFICAR_PROX(Q_SECAO_2, 1.0 / (2.0 * cos(3.0 * 3.141592653589793 / 8.0)), 1e-15,
                 "Q da secao 2");
}

static double amplitude_central(float fs, double f_hz) {
  // Senoide de amplitude 1, filtrada; mede a amplitude no meio (longe das
  // bordas) pelo RMS x sqrt(2), sobre 500 amostras = 10 s a 50 Hz, que e um
  // numero inteiro de ciclos de 3 e de 20 Hz.
  //
  // ⚠️ A primeira versao media o MAIOR valor amostrado, e reprovou o filtro
  // com 0,998 em 3 Hz. Nao era o filtro: a 50 Hz as amostras de uma senoide
  // de 3 Hz nao caem no pico (o mais perto fica a 0,03 ciclo dele). O defeito
  // era da regua.
  static float v[1500];
  const uint32_t n = 1500;
  for (uint32_t i = 0; i < n; i++) {
    v[i] = static_cast<float>(sin(2.0 * 3.141592653589793 * f_hz * i / fs));
  }
  filtrar_antialiasing(v, n, fs);
  double soma2 = 0.0;
  for (uint32_t i = 500; i < 1000; i++) soma2 += static_cast<double>(v[i]) * v[i];
  return sqrt(2.0 * soma2 / 500.0);
}

static void testar_o_que_o_antialiasing_deixa_passar() {
  secao("anti-aliasing -- passa a banda do sono, corta o que dobraria");
  float dc[200];
  for (int i = 0; i < 200; i++) dc[i] = 0.987f;
  filtrar_antialiasing(dc, 200, 50.0f);
  double pior = 0.0;
  for (int i = 0; i < 200; i++) pior = fmax(pior, fabs(dc[i] - 0.987f));
  VERIFICAR(pior < 1e-6, "gravidade constante sai intacta, inclusive nas bordas");

  const double a3 = amplitude_central(50.0f, 3.0);
  const double a20 = amplitude_central(50.0f, 20.0);
  printf("     a 50 Hz: 3 Hz passa com %.4f; 20 Hz sai com %.4f\n", a3, a20);
  VERIFICAR(a3 > 0.999, "3 Hz (movimento de sono) passa inteiro");
  // Butterworth de 4a ordem ida e volta: |H|^2 em 20 Hz ~ 0,03. Sem o filtro,
  // 20 Hz a 50 Hz dobraria para 12 Hz na grade de 32 Hz.
  VERIFICAR(a20 < 0.05, "20 Hz cai abaixo de 5 %");
  VERIFICAR(!filtrar_antialiasing(dc, 200, 20.0f), "12,8 Hz acima do Nyquist de 20 Hz: recusa");
}

static void testar_interpolacao() {
  secao("interpolacao -- linear, e saturada na borda");
  const float rampa[5] = {0.0f, 1.0f, 2.0f, 3.0f, 4.0f};
  float s[4];
  interpolar_linear(rampa, 5, 0.5, 1.25, s, 4);
  VERIFICAR(s[0] == 0.5f && s[1] == 1.75f && s[2] == 3.0f && s[3] == 4.0f,
            "rampa reproduzida e o ultimo ponto em cima da borda");
  interpolar_linear(rampa, 5, -2.0, 10.0, s, 2);
  VERIFICAR(s[0] == 0.0f && s[1] == 4.0f, "fora da janela satura, nao le memoria alheia");
}

// ── Cadeia ────────────────────────────────────────────────────────────

static void testar_intervalo_variado() {
  secao("cadeia -- o despertar variado");
  uint32_t estado = 12345;
  uint32_t menor = 0xFFFFFFFFu, maior = 0;
  for (int i = 0; i < 1000; i++) {
    const uint32_t v = intervalo_de_drenagem_us(&estado);
    if (v < menor) menor = v;
    if (v > maior) maior = v;
  }
  VERIFICAR(menor >= INTERVALO_DE_DRENAGEM_US, "nunca antes de 1,7 s");
  VERIFICAR(maior < INTERVALO_DE_DRENAGEM_US + VARIACAO_DA_DRENAGEM_US, "nunca alem de 1,72 s");
  VERIFICAR(maior - menor > VARIACAO_DA_DRENAGEM_US / 2, "varia de fato");
  uint32_t e1 = 7, e2 = 7;
  VERIFICAR(intervalo_de_drenagem_us(&e1) == intervalo_de_drenagem_us(&e2),
            "deterministico: a mesma semente da a mesma sequencia");
  uint32_t zero = 0;
  intervalo_de_drenagem_us(&zero);
  VERIFICAR(zero != 0, "semente zero nao trava o xorshift em zero");
}

static void testar_ajuste_da_linha_do_tempo() {
  secao("cadeia -- a regressao recupera taxa e fase");
  // Drenagens perfeitas: a amostra k esta em 0,3 + k/47, e a drenagem que deixa
  // a contagem em C acontece meio passo depois da amostra C-1.
  double t[20], x[20];
  for (int i = 0; i < 20; i++) {
    x[i] = 80.0 * (i + 1);
    t[i] = 0.3 + (x[i] - 1.0) / 47.0 + 0.5 / 47.0;
  }
  LinhaDoTempo l;
  VERIFICAR(ajustar_linha_do_tempo(t, x, 20, &l), "ajusta com 20 pontos");
  VERIFICAR_PROX(1.0 / l.b_s, 47.0, 1e-9, "taxa medida = 47 Hz");
  VERIFICAR_PROX(l.a_s + l.b_s * 0.5, 0.3, 1e-9, "t_0 = a + b * 0,5 = 0,3 s");
  VERIFICAR(!ajustar_linha_do_tempo(t, x, MINIMO_DE_DRENAGENS - 1, &l),
            "menos que o minimo de drenagens: recusa");
  for (int i = 0; i < 20; i++) x[i] = 100.0;
  VERIFICAR(!ajustar_linha_do_tempo(t, x, 20, &l), "contagem parada: nao ha reta");
}

// Simula a FIFO de uma taxa `fs`, gravidade em Z e uma senoide lenta em X,
// drenando com o intervalo variado. `pular_drenagens_entre` simula falha de
// despertar; `transbordo_em_s` injeta uma leitura descartada.
struct Simulacao {
  CadeiaC2 cadeia;
  uint64_t origem;
  double fs;
  uint64_t enviadas;
  double proxima_s;
  uint32_t estado;

  void iniciar(double taxa) {
    origem = 50000000ull;
    fs = taxa;
    enviadas = 0;
    proxima_s = -2.0 + 0.9;
    estado = 99;
    cadeia.iniciar(origem);
  }
  // Avanca ate `ate_s`, drenando. Devolve o numero de drenagens feitas.
  int avancar(double ate_s, double transbordo_em_s = 1e9, double surdo_de = 1e9,
              double surdo_ate = -1e9) {
    int feitas = 0;
    while (proxima_s <= ate_s) {
      const double agora = proxima_s;
      proxima_s += intervalo_de_drenagem_us(&estado) / 1e6;
      const uint64_t t_us = origem + static_cast<uint64_t>(llround((agora + 10.0) * 1e6)) -
                            10000000ull;
      // amostras com instante -2 + k/fs <= agora
      const uint64_t devidas = static_cast<uint64_t>(floor((agora + 2.0) * fs)) + 1;
      if (agora >= surdo_de && agora < surdo_ate) continue;  // despertar perdido
      if (fabs(agora - transbordo_em_s) < 0.9) {
        enviadas = devidas;  // o que estava na FIFO se perdeu
        cadeia.registrar_drenagem(t_us, 0, 0, true);
        feitas++;
        continue;
      }
      static AmostraBruta lote[512];
      uint16_t n = 0;
      while (enviadas < devidas && n < 512) {
        const double tk = -2.0 + static_cast<double>(enviadas) / fs;
        lote[n].x = static_cast<int16_t>(lround(400.0 * sin(2.0 * 3.141592653589793 * 0.5 * tk)));
        lote[n].y = 0;
        lote[n].z = 4096;
        enviadas++;
        n++;
      }
      cadeia.registrar_drenagem(t_us, lote, n, false);
      feitas++;
    }
    return feitas;
  }
};

static float gx_[AMOSTRAS_NA_GRADE], gy_[AMOSTRAS_NA_GRADE], gz_[AMOSTRAS_NA_GRADE];

static void testar_cadeia_fecha_epoca() {
  secao("cadeia -- fecha a epoca no tempo certo, na taxa medida");
  static Simulacao s;
  s.iniciar(47.0);
  EpocaReamostrada info;
  s.avancar(32.0);
  VERIFICAR(s.cadeia.proxima_epoca(&info, gx_, gy_, gz_) == EPOCA_AINDA_NAO,
            "antes de fim + margem + folga (32,5 s), espera");
  s.avancar(34.5);
  VERIFICAR(s.cadeia.proxima_epoca(&info, gx_, gy_, gz_) == EPOCA_PRONTA, "depois, fecha");
  VERIFICAR(info.indice == 0, "a primeira epoca");
  VERIFICAR_PROX(1.0 / info.linha.b_s, 47.0, 0.05, "mediu 47 Hz, nao assumiu 50");
  double pior_z = 0.0, pior_x = 0.0;
  for (uint32_t j = 0; j < AMOSTRAS_NA_GRADE; j++) {
    pior_z = fmax(pior_z, fabs(gz_[j] - 1.0));
    const double tj = j / 32.0;
    pior_x = fmax(pior_x, fabs(gx_[j] - (400.0 / 4096.0) * sin(2.0 * 3.141592653589793 * 0.5 * tj)));
  }
  printf("     grade: |gz - 1| max %.2e g; |gx - senoide| max %.2e g\n", pior_z, pior_x);
  VERIFICAR(pior_z < 1e-5, "gravidade constante atravessa a cadeia");
  VERIFICAR(pior_x < 2e-3, "a senoide de 0,5 Hz cai no instante certo da grade");
  VERIFICAR(s.cadeia.proxima_epoca(&info, gx_, gy_, gz_) == EPOCA_AINDA_NAO,
            "a epoca seguinte ainda nao tem folga");
  s.avancar(64.5);
  VERIFICAR(s.cadeia.proxima_epoca(&info, gx_, gy_, gz_) == EPOCA_PRONTA && info.indice == 1,
            "e fecha quando tiver");
}

static void testar_cadeia_recusa() {
  secao("cadeia -- recusa em vez de reamostrar errado");
  EpocaReamostrada info;
  static Simulacao s;

  s.iniciar(50.0);
  s.avancar(34.0);
  VERIFICAR(s.cadeia.proxima_epoca(&info, gx_, gy_, gz_) == EPOCA_PRONTA,
            "epoca 0, antes do transbordo, sai");
  s.avancar(70.0, 45.0);  // transbordo aos 45 s: dentro do ajuste da epoca 1
  VERIFICAR(s.cadeia.proxima_epoca(&info, gx_, gy_, gz_) == EPOCA_RECUSADA_TRANSBORDO,
            "epoca 1 tem o transbordo no ajuste: recusada, nao emendada");
  s.avancar(100.0);
  VERIFICAR(s.cadeia.proxima_epoca(&info, gx_, gy_, gz_) == EPOCA_PRONTA,
            "epoca 2, depois do transbordo, volta a sair -- a contagem nova e coerente");

  s.iniciar(35.0);
  s.avancar(40.0);
  VERIFICAR(s.cadeia.proxima_epoca(&info, gx_, gy_, gz_) == EPOCA_RECUSADA_TAXA,
            "35 Hz (-30 %) nao e o oscilador: recusa");

  // Na placa, 27 s sem despertar transbordariam a FIFO (3,4 s) e o transbordo
  // recusaria a epoca antes. Aqui a simulacao nao transborda, para isolar a
  // regra do minimo de drenagens.
  s.iniciar(50.0);
  s.avancar(40.0, 1e9, 3.0, 30.0);  // 27 s sem despertar: sobram ~5 drenagens
  VERIFICAR(s.cadeia.proxima_epoca(&info, gx_, gy_, gz_) == EPOCA_RECUSADA_POUCAS_DRENAGENS,
            "despertares perdidos demais: a regressao nao tem apoio");

  s.iniciar(50.0);
  s.avancar(130.0);  // processa tarde: o anel (46 s a 50 Hz) ja passou da epoca 0
  VERIFICAR(s.cadeia.proxima_epoca(&info, gx_, gy_, gz_) == EPOCA_RECUSADA_SEM_AMOSTRAS,
            "a janela saiu do anel: recusa em vez de ler amostra sobrescrita");
  VERIFICAR(s.cadeia.epoca_seguinte() == 1, "a recusa consome a epoca");
}

// ── Lote ──────────────────────────────────────────────────────────────

static void testar_montador() {
  secao("lote -- o envelope");
  char buf[64];
  MontadorDeLote m(buf, sizeof(buf));
  VERIFICAR(m.fechar() == 0, "lote vazio nao e enviado");
  VERIFICAR(m.adicionar("{\"a\":1}", 7), "primeira leitura");
  VERIFICAR(m.adicionar("{\"b\":2}", 7), "segunda");
  const uint32_t n = m.fechar();
  VERIFICAR(strcmp(buf, "{\"leituras\":[{\"a\":1},{\"b\":2}]}") == 0, "envelope exato");
  VERIFICAR(n == strlen(buf), "tamanho devolvido");

  char pequeno[24];
  MontadorDeLote p(pequeno, sizeof(pequeno));
  VERIFICAR(p.adicionar("{\"a\":1}", 7), "cabe uma");
  VERIFICAR(!p.adicionar("{\"b\":2}", 7), "a segunda nao cabe com o fechamento: recusada");
  p.fechar();
  VERIFICAR(strcmp(pequeno, "{\"leituras\":[{\"a\":1}]}") == 0, "o recusado nao deixou rastro");

  static char grande[4096];
  MontadorDeLote g(grande, sizeof(grande));
  uint32_t aceitas = 0;
  for (int i = 0; i < 70; i++) aceitas += g.adicionar("{}", 2) ? 1u : 0u;
  VERIFICAR(aceitas == MAX_LEITURAS_POR_LOTE, "teto de 60, o do servidor");
}

static DecisaoDoLote ler(int status, const char *corpo, uint32_t enviadas) {
  return interpretar_resposta_do_lote(status, corpo, corpo ? static_cast<uint32_t>(strlen(corpo)) : 0,
                                      enviadas);
}

static void testar_resposta_do_lote() {
  secao("lote -- a resposta vira epocas fora da fila");
  // O Flask devolve as chaves em ordem alfabetica (sort_keys do jsonify).
  DecisaoDoLote d = ler(200, "{\"aceitas\":[0,1,2],\"pendentes\":[],\"rejeitadas\":[]}", 3);
  VERIFICAR(d.acao == LOTE_CONFIRMAR && d.confirmar == 3 && !d.recuar_depois, "tudo aceito");

  d = ler(200,
          "{\"aceitas\": [0, 2], \"pendentes\": [3, 4], "
          "\"rejeitadas\": [{\"erro\": \"campo \\\"ax\\\" ]} fora\", \"indice\": 1}]}",
          5);
  VERIFICAR(d.acao == LOTE_CONFIRMAR && d.confirmar == 3, "prefixo antes do primeiro pendente");
  VERIFICAR(d.aceitas == 2 && d.rejeitadas == 1 && d.pendentes == 2, "contagens para o log");
  VERIFICAR(d.recuar_depois, "pendentes: o banco caiu ou o tempo acabou -- esperar");

  d = ler(503, "{\"aceitas\":[],\"pendentes\":[0,1],\"rejeitadas\":[]}", 2);
  VERIFICAR(d.acao == LOTE_RECUAR && d.confirmar == 0, "503: nada gravado, nada sai");
  d = ler(503, "{\"aceitas\":[],\"pendentes\":[1],\"rejeitadas\":[{\"indice\":0,\"erro\":\"x\"}]}", 2);
  VERIFICAR(d.acao == LOTE_CONFIRMAR && d.confirmar == 1 && d.recuar_depois,
            "503 com uma rejeitada antes: ela sai (reenviar nao adianta), o resto espera");
  d = ler(503, 0, 2);
  VERIFICAR(d.acao == LOTE_RECUAR && !d.resposta_ilegivel, "503 do gateway, sem corpo: recuar");

  VERIFICAR(ler(413, "", 60).acao == LOTE_DIVIDIR, "413: dividir");
  VERIFICAR(ler(401, "{\"erro\":\"token\"}", 3).acao == LOTE_RECUAR, "401: recuar sem apagar");
  VERIFICAR(ler(400, "{}", 3).confirmar == 0, "400: nada sai");
  VERIFICAR(ler(-1, 0, 3).acao == LOTE_RECUAR, "erro de transporte: recuar");

  d = ler(200, "{\"aceitas\":[0,1,2],\"pendentes\":[],\"rejeitadas\":[],"
               "\"extra\":{\"a\":[1,{\"b\":null}],\"c\":true}}", 3);
  VERIFICAR(d.acao == LOTE_CONFIRMAR && d.confirmar == 3, "chave a mais e pulada");
}

static void testar_resposta_incoerente_nao_apaga_nada() {
  secao("lote -- resposta incoerente: nada sai da fila");
  const char *ruins[] = {
      "{\"aceitas\":[0,0,1],\"pendentes\":[],\"rejeitadas\":[]}",       // repetido
      "{\"aceitas\":[0,1],\"pendentes\":[],\"rejeitadas\":[]}",         // falta o 2
      "{\"aceitas\":[0,1,2,3],\"pendentes\":[],\"rejeitadas\":[]}",     // fora do lote
      "{\"aceitas\":[0,2],\"pendentes\":[1],\"rejeitadas\":[]}",        // pendente no meio
      "{\"aceitas\":[0,1],\"pendentes\":[2]}",                          // lista faltando
      "{\"aceitas\":[0,-1,2],\"pendentes\":[],\"rejeitadas\":[]}",      // negativo
      "{\"aceitas\":[0,1.0,2],\"pendentes\":[],\"rejeitadas\":[]}",     // fracao
      "{\"aceitas\":[0,1],\"pendentes\":[],\"rejeitadas\":[{\"erro\":\"x\"}]}",  // sem indice
      "{\"aceitas\":[0,1,2],\"pendentes\":[],\"rejeit",                  // truncada
      "{}",
      "[0,1,2]",
  };
  for (unsigned i = 0; i < sizeof(ruins) / sizeof(ruins[0]); i++) {
    DecisaoDoLote d = ler(200, ruins[i], 3);
    char msg[96];
    snprintf(msg, sizeof(msg), "resposta ruim %u: ilegivel, nada confirmado", i);
    VERIFICAR(d.resposta_ilegivel && d.confirmar == 0 && d.acao == LOTE_RECUAR, msg);
  }
}

static Epoca fabricar(uint32_t indice) {
  Epoca e;
  e.indice = indice;
  e.pico_total = 9.85f;
  e.pico_ax = 0;
  e.pico_ay = 0;
  e.pico_az = 9.85f;
  e.temp_pico = 25.0f;
  e.amostras = 3;
  e.esperadas = 3;
  e.duracao_s = DURACAO_EPOCA_BASE_S;
  e.nivel = 0;
  e.flags = 0;
  return e;
}

static void testar_buffer_confirma_o_prefixo() {
  secao("lote + buffer -- confirma o prefixo, e so se a fila nao mudou");
  BufferDeEpocas<16> b;
  b.definir_limiar(100);
  for (uint32_t i = 0; i < 5; i++) b.guardar(fabricar(i));

  // Monta o lote com as 5, do jeito que o sketch vai fazer.
  static char envelope[2048];
  MontadorDeLote m(envelope, sizeof(envelope));
  ResolucaoDeParede parede;
  for (uint32_t i = 0; i < b.tamanho(); i++) {
    char leitura[256];
    uint32_t n = 0;
    VERIFICAR(montar_payload(b.em(i), parede, 0, leitura, sizeof(leitura), &n) == PAYLOAD_OK,
              "payload de cada epoca");
    VERIFICAR(m.adicionar(leitura, n), "entra no lote");
  }
  VERIFICAR(m.fechar() > 0 && m.quantidade() == 5, "lote de 5");
  const uint32_t geracao = b.geracao();

  DecisaoDoLote d = ler(200, "{\"aceitas\":[0,1,2],\"pendentes\":[3,4],\"rejeitadas\":[]}", 5);
  VERIFICAR(b.confirmar_entregas(d.confirmar, geracao) == 3, "saem 3");
  VERIFICAR(b.tamanho() == 2 && b.em(0).indice == 3, "os pendentes ficam, na ordem");

  // Agora a fila degrada com um lote no ar.
  BufferDeEpocas<8> c;
  c.definir_limiar(100);
  for (uint32_t i = 0; i < 8; i++) c.guardar(fabricar(i));
  const uint32_t g0 = c.geracao();
  c.degradar();
  VERIFICAR(c.geracao() != g0, "a degradacao muda a geracao");
  VERIFICAR(c.confirmar_entregas(4, g0) == 0,
            "lote montado antes da fusao: nada sai (as 4 primeiras de agora sao outras)");
  VERIFICAR(c.tamanho() == 4, "a fila continua inteira");
  VERIFICAR(c.confirmar_entregas(99, c.geracao()) == 4, "k acima do tamanho satura");
}

int main() {
  printf("Nucleo do firmware Dormio -- pecas da arquitetura C2 (FW-07)\n");

  testar_registradores_da_c2();
  testar_avaliar_fifo();
  testar_decodificar_fifo();
  testar_secao_reproduz_o_butterworth2();
  testar_o_que_o_antialiasing_deixa_passar();
  testar_interpolacao();
  testar_intervalo_variado();
  testar_ajuste_da_linha_do_tempo();
  testar_cadeia_fecha_epoca();
  testar_cadeia_recusa();
  testar_montador();
  testar_resposta_do_lote();
  testar_resposta_incoerente_nao_apaga_nada();
  testar_buffer_confirma_o_prefixo();

  printf("\n-----------------------------------------\n");
  printf("%d verificacoes, %d falhas\n", total, falhas);
  return falhas == 0 ? 0 : 1;
}
