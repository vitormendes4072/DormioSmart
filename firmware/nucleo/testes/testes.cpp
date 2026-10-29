// testes.cpp -- suite do nucleo, rodando no HOST com g++.
//
// Nao ha arduino-cli nem platformio neste ambiente, e mesmo que houvesse o
// teste util aqui nao e "compila para o ESP32": e "a cadencia sobrevive a uma
// queda de rede de tres horas", e isso se verifica em segundos no host e em
// tres horas de espera na placa. Por isso o nucleo nao tem uma linha de
// WiFi.h ou Arduino.h -- nao e purismo, e o que torna esta suite possivel.

#include <math.h>
#include <stdio.h>
#include <string.h>

#include "../buffer.h"
#include "../cadencia.h"
#include "../epoca.h"
#include "../payload.h"
#include "../reconexao.h"
#include "../relogio.h"

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

// ── Relogio ────────────────────────────────────────────────────────────

static void testar_relogio() {
  secao("relogio monotonico");

  RelogioMonotonico r;
  VERIFICAR(r.atualizar(1000) == 1000, "primeira leitura passa direto");
  VERIFICAR(r.atualizar(2000) == 2000, "avanco normal");

  // O wrap de millis() aos 49,7 dias: sem tratamento, `agora - antes` viraria
  // um numero gigante e a cadencia colapsaria sem erro nenhum aparecer.
  RelogioMonotonico w;
  w.atualizar(0xFFFFFF00u);
  uint64_t depois = w.atualizar(0x00000100u);
  VERIFICAR(w.voltas() == 1, "detectou a volta do contador");
  VERIFICAR(depois == (1ull << 32) + 0x100u, "tempo estendido segue crescendo");
  VERIFICAR(depois > 0xFFFFFF00u, "nao andou para tras no wrap");

  // O intervalo real atravessando o wrap tem de dar 512 ms, nao 4,29 bilhoes.
  uint64_t antes = (0ull << 32) | 0xFFFFFF00u;
  VERIFICAR(depois - antes == 512, "intervalo correto atravessando o wrap");
}

static void testar_resolucao_de_parede() {
  secao("resolucao para hora de parede");

  ResolucaoDeParede p;
  VERIFICAR(!p.valida, "nasce invalida: sem NTP nao ha hora");

  // Cenario real: a placa mediu as 23h, ficou offline a noite toda e so
  // sincronizou as 5h. O dado de 23h tem de sair carimbado com 23h.
  const int64_t cinco_da_manha = 1758000000000LL;
  p.sincronizar(6ull * 3600 * 1000, cinco_da_manha);
  int64_t seis_horas_antes = p.resolver(0);
  VERIFICAR(p.valida, "sincronizou");
  VERIFICAR(seis_horas_antes == cinco_da_manha - 6ll * 3600 * 1000,
            "dado de seis horas atras resolve seis horas para tras");
  VERIFICAR(seis_horas_antes < cinco_da_manha,
            "sempre para tras -- o backend so recusa futuro");
}

// ── ISO 8601 ───────────────────────────────────────────────────────────

static void testar_iso8601() {
  secao("formatacao ISO 8601");

  char buf[32];
  VERIFICAR(formatar_iso8601_utc(0, buf, sizeof(buf)) > 0, "epoch zero formata");
  VERIFICAR(strcmp(buf, "1970-01-01T00:00:00.000Z") == 0, "epoch zero correto");

  // 2026-09-22T12:34:56.789Z
  formatar_iso8601_utc(1790080496789LL, buf, sizeof(buf));
  VERIFICAR(strcmp(buf, "2026-09-22T12:34:56.789Z") == 0, "data de hoje correta");

  // 29 de fevereiro de 2024 -- bissexto
  formatar_iso8601_utc(1709164800000LL, buf, sizeof(buf));
  VERIFICAR(strcmp(buf, "2024-02-29T00:00:00.000Z") == 0, "ano bissexto");

  // 2000 e bissexto (divisivel por 400), 1900 nao era
  formatar_iso8601_utc(951782400000LL, buf, sizeof(buf));
  VERIFICAR(strcmp(buf, "2000-02-29T00:00:00.000Z") == 0, "regra dos 400 anos");

  VERIFICAR(formatar_iso8601_utc(0, buf, 10) == 0, "recusa buffer pequeno");
}

// ── Cadencia ───────────────────────────────────────────────────────────

static void testar_cadencia_regular() {
  secao("cadencia -- ritmo normal");

  ControleDeCadencia c;
  c.iniciar(0, 1000);

  int amostras = 0;
  for (uint64_t t = 0; t <= 10000; t += 100) {
    if (c.deve_amostrar(t)) amostras++;
  }
  VERIFICAR(amostras == 11, "11 ticks em 10 s a 1 Hz (inclui t=0)");
  VERIFICAR(c.ticks_perdidos() == 0, "nenhum tick perdido no ritmo normal");
}

static void testar_cadencia_sem_deriva() {
  secao("cadencia -- a grade e absoluta");

  // O laco chega SEMPRE 300 ms atrasado. Com agendamento relativo
  // (`ultimo + periodo`), esse atraso entraria na base de tempo e nunca mais
  // sairia: ao fim de 100 ticks a serie estaria 30 s deslocada, e nada no
  // dado diria isso. Com grade absoluta, o atraso e absorvido tick a tick.
  ControleDeCadencia c;
  c.iniciar(0, 1000);

  uint64_t ultimo_servido = 0;
  int servidos = 0;
  for (int k = 0; k < 100; k++) {
    uint64_t t = static_cast<uint64_t>(k) * 1000 + 300;
    if (c.deve_amostrar(t)) {
      servidos++;
      ultimo_servido = t;
    }
  }
  VERIFICAR(servidos == 100, "todo tick foi servido, apesar do atraso fixo");
  VERIFICAR(c.ticks_perdidos() == 0, "atraso menor que o periodo nao perde tick");
  // O centesimo tick e devido em 99000; com 300 ms de atraso, 99300. Se
  // houvesse deriva, seria 99000 + 100*300 = 129000.
  VERIFICAR(ultimo_servido == 99300, "sem acumulo de deriva ao fim de 100 ticks");
  VERIFICAR(c.maior_atraso_ms() == 300, "o atraso e medido, nao escondido");
}

static void testar_cadencia_sob_bloqueio() {
  secao("cadencia -- bloqueio longo nao vira compensacao");

  // Exatamente o que `conectarWiFi()` faz hoje dentro do laco: 20 s presos.
  ControleDeCadencia c;
  c.iniciar(0, 1000);
  c.deve_amostrar(0);

  bool serviu = c.deve_amostrar(20500);
  VERIFICAR(serviu, "serve o tick corrente ao voltar");
  VERIFICAR(c.ticks_perdidos() == 19,
            "contou os 19 ticks que passaram em branco (o 20o e o que acabou de ser servido)");

  // O proximo tick tem de cair na grade (21000), e nao 1000 ms depois do
  // retorno (21500) -- senao o bloqueio teria deslocado a grade para sempre.
  VERIFICAR(!c.deve_amostrar(20900), "nao dispara antes do proximo tick da grade");
  VERIFICAR(c.deve_amostrar(21000), "o proximo tick esta na grade");

  // E nao dispara 20 vezes seguidas para "recuperar" -- isso poria 20 medidas
  // no instante errado, que e pior que nao ter as 20.
  int rajada = 0;
  for (int i = 0; i < 50; i++) {
    if (c.deve_amostrar(21000)) rajada++;
  }
  VERIFICAR(rajada == 0, "nao compensa disparando em rajada");
}

// ── Acumulador de epoca ────────────────────────────────────────────────

struct Coletor {
  Epoca itens[512];
  uint32_t n;
  Coletor() : n(0) {}
};

static void coletar(const Epoca &e, void *ctx) {
  Coletor *c = static_cast<Coletor *>(ctx);
  if (c->n < 512) c->itens[c->n++] = e;
}

static void testar_acumulador_pico() {
  secao("acumulador -- pico da magnitude");

  AcumuladorDeEpoca a;
  Coletor c;
  a.iniciar(0, 3, coletar, &c);  // 3 amostras por epoca (cadencia de 10 s)

  a.amostrar(0, 0, 0, 9.81f, 9.81f, 25.0f);
  a.amostrar(10000, 1, 0, 12.0f, 12.04f, 25.1f);  // pico
  a.amostrar(20000, 0, 0, 9.70f, 9.70f, 25.0f);
  a.fechar_ate(30000);

  VERIFICAR(c.n == 1, "fechou uma epoca");
  VERIFICAR_PROX(c.itens[0].pico_total, 12.04f, 0.001f, "guardou o pico, nao a media");
  VERIFICAR_PROX(c.itens[0].pico_az, 12.0f, 0.001f, "ax/ay/az sao os DA amostra de pico");
  VERIFICAR(c.itens[0].amostras == 3, "contou as tres amostras");
  VERIFICAR(!c.itens[0].incompleta(), "completa: bateu com o esperado");
  VERIFICAR(c.itens[0].duracao_s == 30, "epoca base de 30 s");

  // A coerencia que o backend cobra (secao 5.1): |a| tem de bater com
  // sqrt(ax^2+ay^2+az^2) da MESMA amostra, com folga de 0,5.
  const Epoca &e = c.itens[0];
  float mag = sqrtf(e.pico_ax * e.pico_ax + e.pico_ay * e.pico_ay + e.pico_az * e.pico_az);
  VERIFICAR_PROX(mag, e.pico_total, 0.5f, "payload internamente coerente");
}

static void testar_acumulador_lacuna() {
  secao("acumulador -- lacuna vira registro, nao silencio");

  AcumuladorDeEpoca a;
  Coletor c;
  a.iniciar(0, 3, coletar, &c);

  a.amostrar(0, 0, 0, 9.81f, 9.81f, 25.0f);
  a.amostrar(10000, 0, 0, 9.81f, 9.81f, 25.0f);
  a.amostrar(20000, 0, 0, 9.81f, 9.81f, 25.0f);
  // Tres epocas inteiras sem amostra nenhuma (placa presa, sensor solto).
  a.amostrar(120000, 0, 0, 9.81f, 9.81f, 25.0f);
  a.fechar_ate(150000);

  VERIFICAR(c.n == 5, "cinco epocas fechadas -- as tres vazias INCLUSIVE");
  VERIFICAR(!c.itens[0].vazia(), "epoca 0 tem dado");
  VERIFICAR(c.itens[1].vazia() && c.itens[2].vazia() && c.itens[3].vazia(),
            "epocas 1..3 declaradas vazias");
  VERIFICAR(!c.itens[4].vazia(), "epoca 4 tem dado");

  // O ponto: os indices continuam sendo 0,1,2,3,4. A epoca 4 nao "encostou"
  // na 0. Sem os registros vazios, a analise veria duas epocas consecutivas
  // e concluiria que a noite foi medida sem falha.
  for (uint32_t i = 0; i < c.n; i++) {
    VERIFICAR(c.itens[i].indice == i, "indice da grade preservado na lacuna");
  }
}

static void testar_acumulador_incompleta() {
  secao("acumulador -- perda de cadencia fica no dado");

  AcumuladorDeEpoca a;
  Coletor c;
  a.iniciar(0, 3, coletar, &c);

  a.amostrar(0, 0, 0, 9.81f, 9.81f, 25.0f);  // so 1 das 3
  a.fechar_ate(30000);

  VERIFICAR(c.n == 1, "fechou");
  VERIFICAR(c.itens[0].amostras == 1 && c.itens[0].esperadas == 3,
            "a diferenca entre medido e prometido esta gravada");
  VERIFICAR(c.itens[0].incompleta(),
            "marcada incompleta -- dado distorcido que parece valido e o que evitamos");
}

static void testar_acumulador_amostra_atrasada() {
  secao("acumulador -- amostra atrasada nao e realocada no tempo");

  AcumuladorDeEpoca a;
  Coletor c;
  a.iniciar(0, 3, coletar, &c);
  a.fechar_ate(60000);  // avanca para a epoca 2

  // Uma amostra carimbada com um instante da epoca 0, chegando agora. Atribui-la
  // a epoca corrente moveria um evento no tempo -- a distorcao que este modulo
  // existe para impedir.
  a.amostrar(1000, 0, 0, 50.0f, 50.0f, 25.0f);
  a.fechar_ate(90000);

  VERIFICAR(c.n == 3, "fechou as epocas 0, 1 e 2");
  VERIFICAR(c.itens[2].indice == 2, "a terceira e mesmo a epoca 2");
  VERIFICAR(c.itens[2].vazia(),
            "a amostra atrasada NAO foi parar na epoca corrente");
  // O pico absurdo de 50 m/s2 nao aparece em epoca nenhuma: a epoca 0 ja
  // tinha fechado vazia, e a 2 nao e dela. Perder a amostra e a resposta
  // certa -- move-la no tempo seria inventar um evento onde nao houve.
  for (uint32_t i = 0; i < c.n; i++) {
    VERIFICAR(c.itens[i].pico_total < 40.0f, "o evento nao foi realocado no tempo");
  }
}

static void testar_amostra_na_virada() {
  secao("acumulador -- REGRESSAO: a amostra da virada nao pode sumir");

  // Este teste existe por causa de um bug que a primeira versao tinha e que
  // so a suite pegou. O fechamento era preguicoso (`fechar_ate` chamado pelo
  // laco DEPOIS de `amostrar`), e `amostrar` recusava amostra de um slot
  // futuro porque nao tinha como fechar o anterior sozinho.
  //
  // O efeito: na cadencia de 10 s com epoca de 30 s, as amostras dos
  // instantes 30 000, 60 000, 90 000... -- UMA EM CADA TRES -- eram
  // silenciosamente descartadas, e toda epoca saia com 2 de 3 amostras e a
  // flag INCOMPLETA. A medicao estaria perfeita e o dado diria que nao.
  //
  // Na placa isso apareceria como "o firmware perde um terco das amostras",
  // depois de uma noite de coleta. Aqui aparece em 3 ms.

  AcumuladorDeEpoca a;
  Coletor c;
  a.iniciar(0, 3, coletar, &c);

  for (uint64_t t = 0; t < 300000; t += 10000) {
    a.amostrar(t, 0.1f, 0.2f, 9.8f, 9.81f, 25.0f);
  }
  a.fechar_ate(300000);

  VERIFICAR(c.n == 10, "dez epocas de 30 s em 300 s");
  for (uint32_t i = 0; i < c.n; i++) {
    VERIFICAR(c.itens[i].amostras == 3, "toda epoca com as 3 amostras que a cadencia deu");
    VERIFICAR(!c.itens[i].incompleta(), "nenhuma epoca marcada incompleta sem motivo");
  }
}

// ── Degradacao ─────────────────────────────────────────────────────────

static Epoca fabricar(uint32_t indice, float pico, uint16_t amostras = 3) {
  Epoca e;
  e.indice = indice;
  e.pico_total = pico;
  e.pico_ax = 0;
  e.pico_ay = 0;
  e.pico_az = pico;
  e.temp_pico = 25.0f;
  e.amostras = amostras;
  e.esperadas = 3;
  e.duracao_s = DURACAO_EPOCA_BASE_S;
  e.nivel = 0;
  e.flags = 0;
  return e;
}

static void testar_fusao_exata() {
  secao("degradacao -- a fusao e exata, nao aproximada");

  // Maximo e associativo: o pico de duas epocas de 30 s E o pico da epoca de
  // 60 s que as cobre. Nao uma estimativa -- o mesmo numero.
  Epoca a = fabricar(0, 9.9f);
  Epoca b = fabricar(1, 14.2f);
  b.pico_az = 14.2f;
  fundir(&a, b);

  VERIFICAR_PROX(a.pico_total, 14.2f, 0.001f, "pico das duas = pico da janela dobrada");
  VERIFICAR_PROX(a.pico_az, 14.2f, 0.001f, "ax/ay/az acompanham o pico vencedor");
  VERIFICAR(a.duracao_s == 60, "duracao dobrou");
  VERIFICAR(a.nivel == 1, "subiu um nivel");
  VERIFICAR(a.indice == 0, "indice passa para a grade do novo nivel");
  VERIFICAR(a.amostras == 6, "contagens somam");
  VERIFICAR(a.degradada(), "marcada como degradada -- a analise precisa saber");
}

static void testar_fusao_com_vazia() {
  secao("degradacao -- fusao com lacuna nao apaga a lacuna");

  Epoca a = fabricar(0, 9.9f);
  Epoca b = fabricar(1, 0.0f, 0);
  b.flags = EPOCA_VAZIA;

  fundir(&a, b);
  VERIFICAR(!a.vazia(), "metade com dado: o todo nao e vazio");
  VERIFICAR(a.incompleta(), "mas fica incompleto -- metade da janela nao foi medida");
  VERIFICAR_PROX(a.pico_total, 9.9f, 0.001f, "a lacuna nao derruba o pico para zero");

  // Duas lacunas continuam sendo lacuna.
  Epoca v1 = fabricar(0, 0.0f, 0); v1.flags = EPOCA_VAZIA;
  Epoca v2 = fabricar(1, 0.0f, 0); v2.flags = EPOCA_VAZIA;
  fundir(&v1, v2);
  VERIFICAR(v1.vazia(), "duas lacunas viram uma lacuna maior");
}

static void testar_buffer_degrada_em_vez_de_descartar() {
  secao("buffer -- degrada resolucao em vez de perder a noite");

  BufferDeEpocas<64> b;
  b.definir_limiar(75);

  for (uint32_t i = 0; i < 200; i++) {
    Epoca e = fabricar(i, 9.8f + (i % 7) * 0.1f);
    VERIFICAR(b.guardar(e), "nenhuma epoca foi descartada");
  }

  VERIFICAR(b.estatisticas().descartes == 0, "zero descartes em 200 epocas num buffer de 64");
  VERIFICAR(b.estatisticas().degradacoes > 0, "degradou");
  VERIFICAR(b.estatisticas().nivel_maximo >= 1, "produziu epocas mais longas");

  // O que importa: a COBERTURA temporal sobreviveu. 200 epocas de 30 s sao
  // 100 minutos; o buffer de 64 posicoes guarda essa hora e quarenta inteira,
  // parte dela em resolucao mais grossa.
  double horas = b.horas_cobertas();
  VERIFICAR(horas > 1.6, "cobertura preservada (>1,6 h)");
  printf("     cobertura mantida: %.2f h em %u posicoes (nivel max %u)\n", horas,
         b.tamanho(), b.estatisticas().nivel_maximo);
}

static void testar_teto_do_contrato() {
  secao("degradacao -- respeita o teto de 3600 s do backend");

  BufferDeEpocas<8> b;
  b.definir_limiar(75);
  for (uint32_t i = 0; i < 5000; i++) {
    b.guardar(fabricar(i, 9.9f));
  }
  for (uint32_t i = 0; i < b.tamanho(); i++) {
    VERIFICAR(b.em(i).nivel <= NIVEL_MAXIMO, "nunca passa do nivel 6");
    VERIFICAR(b.em(i).duracao_s <= 3600, "epoca_s dentro do que o backend aceita");
  }
  printf("     apos 5000 epocas num buffer de 8: nivel max %u, duracao max %u s\n",
         b.estatisticas().nivel_maximo, b.em(0).duracao_s);
}

static void testar_buffer_fifo_e_confirmacao() {
  secao("buffer -- o dado so sai depois do 201");

  BufferDeEpocas<16> b;
  b.guardar(fabricar(0, 9.8f));
  b.guardar(fabricar(1, 9.9f));

  Epoca primeira;
  VERIFICAR(b.primeira(&primeira), "leu a mais antiga");
  VERIFICAR(primeira.indice == 0, "FIFO: a mais antiga sai primeiro");
  VERIFICAR(b.tamanho() == 2, "ler NAO remove -- se o POST falhar, o dado fica");

  b.confirmar_entrega();
  VERIFICAR(b.tamanho() == 1, "confirmada, sai da fila");
  b.primeira(&primeira);
  VERIFICAR(primeira.indice == 1, "a proxima e a seguinte");
}

// ── Backoff ────────────────────────────────────────────────────────────

static void testar_backoff() {
  secao("reconexao -- backoff exponencial com teto");

  PoliticaDeReconexao p(0xABCD);
  ParametrosDeBackoff par;
  par.base_ms = 2000;
  par.teto_ms = 120000;
  par.jitter_ms = 0;  // sem jitter para o teste ser deterministico
  p.definir_parametros(par);

  p.iniciar(0);
  VERIFICAR(p.deve_tentar(0), "a primeira tentativa e imediata");

  uint64_t t = 0;
  uint32_t esperas[8];
  for (int i = 0; i < 8; i++) {
    p.registrar_falha(t);
    esperas[i] = p.espera_atual();
    t = p.proxima_tentativa_em();
  }
  VERIFICAR(esperas[0] == 2000, "1a falha: 2 s");
  VERIFICAR(esperas[1] == 4000, "2a falha: 4 s");
  VERIFICAR(esperas[2] == 8000, "3a: 8 s");
  VERIFICAR(esperas[3] == 16000, "4a: 16 s");
  VERIFICAR(esperas[7] == 120000, "satura no teto, nao cresce sem limite");

  // O teto e o que faz o aparelho perceber que a rede voltou. Sem ele, apos
  // uma noite de falhas a proxima tentativa seria daqui a dias.
  VERIFICAR(p.espera_atual() <= par.teto_ms, "nunca acima do teto");

  p.registrar_sucesso(t);
  VERIFICAR(p.conectado(), "conectou");
  VERIFICAR(p.tentativas_seguidas() == 0, "sucesso zera o expoente");
  VERIFICAR(!p.deve_tentar(t + 999999), "conectado nao tenta de novo");

  p.registrar_queda(t);
  VERIFICAR(p.deve_tentar(t), "queda depois de conectado: tentativa imediata");
}

static void testar_backoff_jitter() {
  secao("reconexao -- jitter descorrelaciona aparelhos");

  ParametrosDeBackoff par;
  par.jitter_ms = 1500;
  PoliticaDeReconexao a(1), bb(2);
  a.definir_parametros(par);
  bb.definir_parametros(par);
  a.iniciar(0);
  bb.iniciar(0);
  a.registrar_falha(0);
  bb.registrar_falha(0);
  VERIFICAR(a.espera_atual() != bb.espera_atual(),
            "dois aparelhos que cairam juntos nao voltam juntos");
  VERIFICAR(a.espera_atual() >= par.base_ms &&
                a.espera_atual() < par.base_ms + par.jitter_ms,
            "jitter dentro da amplitude declarada");
}

// ── Payload ────────────────────────────────────────────────────────────

static void testar_payload() {
  secao("payload -- contrato v2.0.0");

  char buf[256];
  uint32_t n = 0;
  ResolucaoDeParede parede;

  Epoca e = fabricar(0, 9.85f);
  e.pico_ax = 0.1f; e.pico_ay = 0.2f; e.pico_az = 9.85f;

  VERIFICAR(montar_payload(e, parede, 0, buf, sizeof(buf), &n) == PAYLOAD_OK,
            "monta sem hora de parede");
  VERIFICAR(strstr(buf, "\"ts\"") == 0,
            "sem NTP, o campo ts NAO vai -- backend cai no created_at, que e honesto");
  VERIFICAR(strstr(buf, "\"epoca_s\":30") != 0, "declara a epoca");
  VERIFICAR(strstr(buf, "\"metodo\":\"pico-da-magnitude\"") != 0,
            "declara o metodo -- obrigatorio quando ha epoca_s");
  VERIFICAR(strstr(buf, "\"status\":\"Repouso\"") != 0, "classificou no dispositivo");
  VERIFICAR(strstr(buf, "\"gx\"") == 0, "sem giroscopio: opcional desde a v2.0.0");

  parede.sincronizar(3600000, 1790080496789LL);
  VERIFICAR(montar_payload(e, parede, 0, buf, sizeof(buf), &n) == PAYLOAD_OK, "monta com ts");
  VERIFICAR(strstr(buf, "\"ts\":\"2026-09-22T11:34:56.789Z\"") != 0,
            "ts resolvido uma hora para tras");

  Epoca mov = fabricar(1, 12.5f);
  mov.pico_az = 12.5f;
  montar_payload(mov, parede, 0, buf, sizeof(buf), &n);
  VERIFICAR(strstr(buf, "\"status\":\"Movimento\"") != 0, "|12,5-9,81| > 1,2");

  Epoca vazia = fabricar(2, 0.0f, 0);
  vazia.flags = EPOCA_VAZIA;
  VERIFICAR(montar_payload(vazia, parede, 0, buf, sizeof(buf), &n) == PAYLOAD_EPOCA_VAZIA,
            "epoca vazia nao produz payload -- nao se inventa medida");

  Epoca mudo = fabricar(3, 0.0f);
  VERIFICAR(montar_payload(mudo, parede, 0, buf, sizeof(buf), &n) ==
                PAYLOAD_MAGNITUDE_IMPLAUSIVEL,
            "|a| = 0 e sensor mudo, nao repouso -- nao envia");
}

// ── Cenario de noite inteira ───────────────────────────────────────────

static void testar_noite_com_queda_de_rede() {
  secao("cenario -- 8 h de coleta com 3 h de rede fora");

  // O caso que motivou tudo. Antes: `conectarWiFi()` dentro do laco, 20 s de
  // bloqueio por ciclo de 10 s. A cadencia colapsaria e a leitura seria
  // descartada. Aqui a rede cai e a medida nem percebe.

  RelogioMonotonico relogio;
  ControleDeCadencia cadencia;
  AcumuladorDeEpoca acumulador;
  BufferDeEpocas<1024> buffer;
  PoliticaDeReconexao rede(0x1234);

  const uint32_t PERIODO_MS = 10000;   // amostra a cada 10 s
  const uint64_t OITO_HORAS = 8ull * 3600 * 1000;
  const uint64_t QUEDA_INICIO = 1ull * 3600 * 1000;
  const uint64_t QUEDA_FIM = 4ull * 3600 * 1000;

  struct Ponte {
    BufferDeEpocas<1024> *b;
    uint32_t guardadas;
  };
  Ponte ponte = {&buffer, 0};

  struct Aux {
    static void guardar(const Epoca &e, void *ctx) {
      Ponte *p = static_cast<Ponte *>(ctx);
      p->b->guardar(e);
      p->guardadas++;
    }
  };

  uint64_t t0 = relogio.atualizar(0);
  cadencia.iniciar(t0, PERIODO_MS);
  acumulador.iniciar(t0, cadencia.amostras_por_epoca(DURACAO_EPOCA_BASE_S),
                     Aux::guardar, &ponte);
  rede.iniciar(t0);

  uint32_t amostras = 0;
  uint32_t entregues = 0;

  // Passo de 1 s: 28 800 iteracoes de uma noite inteira, em milissegundos de
  // CPU. Na placa seriam oito horas.
  for (uint64_t t = 0; t <= OITO_HORAS; t += 1000) {
    uint64_t agora = relogio.atualizar(static_cast<uint32_t>(t));

    // 1. MEDIR. Nunca espera por rede, por serial, nem por nada.
    if (cadencia.deve_amostrar(agora)) {
      acumulador.amostrar(agora, 0.1f, 0.2f, 9.8f, 9.81f, 25.0f);
      amostras++;
    }
    acumulador.fechar_ate(agora);

    // 2. REDE, em outra linha de raciocinio. Falha aqui nao toca no de cima.
    bool ha_rede = !(t >= QUEDA_INICIO && t < QUEDA_FIM);
    if (!rede.conectado() && rede.deve_tentar(agora)) {
      if (ha_rede) {
        rede.registrar_sucesso(agora);
      } else {
        rede.registrar_falha(agora);
      }
    }
    if (rede.conectado() && !ha_rede) {
      rede.registrar_queda(agora);
    }

    // 3. DRENAR, por rajada limitada.
    if (rede.conectado()) {
      for (int i = 0; i < 4 && !buffer.vazio(); i++) {
        Epoca e;
        buffer.primeira(&e);
        if (e.vazia()) {
          buffer.confirmar_entrega();  // lacuna nao se envia; sai da fila
          continue;
        }
        buffer.confirmar_entrega();
        entregues++;
      }
    }
  }

  // 8 h a 10 s = 2880 amostras. 8 h / 30 s = 960 epocas.
  VERIFICAR(amostras == 2881, "a cadencia NAO foi afetada pela queda de rede");
  VERIFICAR(ponte.guardadas == 960, "960 epocas de 30 s numa noite de 8 h");
  VERIFICAR(buffer.estatisticas().descartes == 0, "nenhuma epoca perdida");
  VERIFICAR(entregues >= 950, "praticamente tudo entregue ao fim");
  VERIFICAR(cadencia.ticks_perdidos() == 0, "nenhum tick perdido");

  printf("     amostras %u | epocas %u | entregues %u | degradacoes %u | descartes %u\n",
         amostras, ponte.guardadas, entregues, buffer.estatisticas().degradacoes,
         buffer.estatisticas().descartes);
}

static void testar_noite_sem_rede_nenhuma() {
  secao("cenario -- 8 h SEM rede nenhuma, buffer de 128 epocas");

  // O teste que mostra o valor da degradacao. 8 h sao 960 epocas de 30 s e o
  // buffer tem 128 posicoes. Com descarte, sobrariam 64 min de noite. Com
  // degradacao, sobra a noite inteira, em resolucao mais grossa.

  AcumuladorDeEpoca acumulador;
  BufferDeEpocas<128> buffer;
  struct Ponte { BufferDeEpocas<128> *b; uint32_t n; };
  Ponte ponte = {&buffer, 0};
  struct Aux {
    static void guardar(const Epoca &e, void *ctx) {
      Ponte *p = static_cast<Ponte *>(ctx);
      p->b->guardar(e);
      p->n++;
    }
  };

  acumulador.iniciar(0, 3, Aux::guardar, &ponte);
  for (uint64_t t = 0; t <= 8ull * 3600 * 1000; t += 10000) {
    acumulador.amostrar(t, 0.1f, 0.2f, 9.8f, 9.81f + (t % 70000) * 0.00001f, 25.0f);
    acumulador.fechar_ate(t);
  }

  VERIFICAR(ponte.n >= 959, "as 960 epocas da noite foram produzidas");
  VERIFICAR(buffer.estatisticas().descartes == 0, "nada foi descartado");
  double horas = buffer.horas_cobertas();
  VERIFICAR(horas > 7.9, "a noite INTEIRA continua no buffer");
  printf("     buffer de 128 posicoes guardou %.2f h (nivel max %u, %u fusoes)\n",
         horas, buffer.estatisticas().nivel_maximo, buffer.estatisticas().fusoes);
}

// ── main ───────────────────────────────────────────────────────────────

int main() {
  printf("Nucleo do firmware Dormio -- suite no host\n");
  printf("sizeof(Epoca) = %u bytes\n", static_cast<unsigned>(sizeof(Epoca)));

  testar_relogio();
  testar_resolucao_de_parede();
  testar_iso8601();
  testar_cadencia_regular();
  testar_cadencia_sem_deriva();
  testar_cadencia_sob_bloqueio();
  testar_acumulador_pico();
  testar_acumulador_lacuna();
  testar_acumulador_incompleta();
  testar_acumulador_amostra_atrasada();
  testar_amostra_na_virada();
  testar_fusao_exata();
  testar_fusao_com_vazia();
  testar_buffer_degrada_em_vez_de_descartar();
  testar_teto_do_contrato();
  testar_buffer_fifo_e_confirmacao();
  testar_backoff();
  testar_backoff_jitter();
  testar_payload();
  testar_noite_com_queda_de_rede();
  testar_noite_sem_rede_nenhuma();

  printf("\n-----------------------------------------\n");
  printf("%d verificacoes, %d falhas\n", total, falhas);
  return falhas == 0 ? 0 : 1;
}
