// epoca.h -- a unidade de dado do buffer: uma epoca agregada, nao uma amostra.
//
// ── POR QUE EPOCA, E NAO AMOSTRA INSTANTANEA ───────────────────────────
//
// Esta e a decisao de projeto que sustenta todo o resto, e ela antecipa o
// `FW-05` de proposito.
//
// Com amostras instantaneas no buffer, "buffer cheio" so tem saidas ruins:
// descartar o mais antigo perde o adormecer (a transicao que mais interessa
// numa actigrafia), descartar o mais novo perde o despertar. As duas sao
// perdas BINARIAS -- o dado some inteiro.
//
// Com epocas, existe uma terceira saida: agregar o que ja esta guardado em
// epocas mais longas e continuar medindo. Perde-se RESOLUCAO, nao COBERTURA.
// A noite inteira continua registrada, so que parte dela em janelas de 60 s
// ou 120 s em vez de 30 s. Degradacao gradual em vez de penhasco.
//
// ── POR QUE A DEGRADACAO E EXATA, E NAO UMA APROXIMACAO ────────────────
//
// O contrato (`docs/DATA-CONTRACT.md` secao 2.5) define o unico metodo de
// agregacao aceito como `pico-da-magnitude`: `total` e o MAIOR |a| da janela,
// e `ax/ay/az` sao os da amostra de pico.
//
// Maximo e associativo. O pico de duas epocas de 30 s adjacentes E o pico da
// epoca de 60 s que as cobre -- nao uma estimativa dele, o valor exato. Entao
// degradar resolucao nao introduz erro nenhum de agregacao: o numero que sai
// e identico ao que sairia se a epoca de 60 s tivesse sido medida assim desde
// o inicio. O que se perde e so a informacao de EM QUAL METADE o pico caiu.
//
// Se o metodo fosse media, isso nao valeria (media de medias so e a media
// quando os pesos batem) e a degradacao teria de carregar contagens. O `total`
// tambem deixaria de ser comparavel com o limiar de 1,2 m/s^2 sem caso
// especial. O pico nao tem esse problema -- e essa e mais uma razao para ele.
//
// ── POR QUE O GIROSCOPIO NAO ENTRA AQUI ────────────────────────────────
//
// Seriam 12 bytes por epoca, 37,5% do registro. O contrato (secao 2.0) diz
// que `gx/gy/gz` sao opcionais desde a v2.0.0 e que "o giroscopio NAO entra
// em nenhum criterio: o movimento e decidido so pela magnitude da
// aceleracao". Gastar mais de um terco do buffer com um campo que nenhuma
// decisao le custaria mais de um terco das horas de autonomia offline.
//
// A temperatura FICA, apesar de tambem ser opcional: 4 bytes que pagam o
// delator de sensor mudo (36,5 C exatos = registrador zerado), e um sensor
// mudo a noite inteira e o modo de falha mais caro que este projeto ja teve.

#ifndef DORMIO_NUCLEO_EPOCA_H
#define DORMIO_NUCLEO_EPOCA_H

#include <stdint.h>

namespace dormio {

// Duracao da epoca base. 30 s nao e um numero escolhido aqui: e a resolucao
// dos rotulos de PSG de todos os datasets do projeto e a epoca do pipeline de
// ML (`DATA-02`). O firmware tem de falar a mesma unidade, senao o dado
// captado nao entra no mesmo lugar que o dado dos datasets.
const uint16_t DURACAO_EPOCA_BASE_S = 30;

// Teto da degradacao, imposto pelo BACKEND e nao por gosto.
// `web-app/validacao.py` rejeita `epoca_s` fora de [1, 3600]. Com base de
// 30 s, o nivel n produz 30 * 2^n segundos:
//
//     n=0: 30 s   n=1: 60 s   n=2: 120 s   n=3: 240 s
//     n=4: 480 s  n=5: 960 s  n=6: 1920 s  n=7: 3840 s  <- 400 Bad Request
//
// Degradar alem do nivel 6 produziria epocas que o firmware nao consegue
// entregar: o dado sobreviveria ao buffer e morreria na validacao. Uma epoca
// guardada que nao pode ser enviada e pior que uma epoca descartada, porque
// ocupa espaco fingindo que o dado esta salvo.
const uint8_t NIVEL_MAXIMO = 6;
const uint16_t DURACAO_MAXIMA_S = 1920;  // 30 * 2^6

// Bits de `flags`.
enum FlagsDeEpoca {
  // A epoca fechou com menos amostras do que a cadencia prometia. O dado
  // continua valendo; o que muda e a confianca no pico (com menos amostras,
  // mais chance de o pico real ter caido num intervalo nao amostrado).
  EPOCA_INCOMPLETA = 1 << 0,

  // Nenhuma amostra caiu nesta janela. E uma LACUNA declarada, nao um
  // silencio: existe para a base de tempo continuar intacta quando a
  // amostragem falha. Ver `buffer.h`, "por que lacuna vira registro".
  EPOCA_VAZIA = 1 << 1,

  // A epoca e resultado de fusao por degradacao de resolucao, nao foi medida
  // nesta duracao. Viaja com o dado para a analise posterior saber.
  EPOCA_DEGRADADA = 1 << 2,

  // Alguma amostra desta janela foi recusada por magnitude fisicamente
  // impossivel (sensor respondendo no I2C mas nao medindo).
  EPOCA_COM_AMOSTRA_INVALIDA = 1 << 3,
};

// Registro de uma epoca. POD, com tipos de largura fixa e um `static_assert`
// de tamanho no .cpp.
//
// POR QUE A LARGURA FIXA IMPORTA AQUI: a medicao de capacidade roda no host
// (x86-64) e o resultado precisa valer para o alvo (xtensa 32 bits). Com
// `int`/`long` e padding implicito, `sizeof` no host seria um numero sobre o
// host, nao sobre a placa -- exatamente o tipo de "medida" que parece medida
// e e chute. Com larguras fixas e a ordem abaixo (4/4/4/4/4/4/2/2/2/1/1), o
// layout e o mesmo nos dois e a medicao transfere.
struct Epoca {
  // Indice da epoca na GRADE absoluta de 30 s desde o inicio da coleta, nao
  // um instante em ms. Guardar o indice e o que impede a deriva: o instante e
  // sempre recalculado como `t0 + indice * 30 s`, nunca acumulado a partir do
  // fechamento anterior. 2^32 indices sao 4085 anos.
  uint32_t indice;

  float pico_total;  // maior |a| da janela, m/s^2
  float pico_ax;     // ax/ay/az DA AMOSTRA DE PICO -- assim a checagem de
  float pico_ay;     // coerencia do backend (secao 5.1 do contrato) continua
  float pico_az;     // valendo sem caso especial
  float temp_pico;   // C, do mesmo instante do pico

  uint16_t amostras;   // quantas amostras entraram de fato
  uint16_t esperadas;  // quantas a cadencia prometia para esta janela
  uint16_t duracao_s;  // 30 na epoca base; 60, 120... depois de degradar

  uint8_t nivel;  // 0 = base. n = fundiu 2^n epocas base.
  uint8_t flags;  // ver FlagsDeEpoca

  Epoca()
      : indice(0), pico_total(0), pico_ax(0), pico_ay(0), pico_az(0),
        temp_pico(0), amostras(0), esperadas(0),
        duracao_s(DURACAO_EPOCA_BASE_S), nivel(0), flags(0) {}

  bool vazia() const { return (flags & EPOCA_VAZIA) != 0; }
  bool incompleta() const { return (flags & EPOCA_INCOMPLETA) != 0; }
  bool degradada() const { return (flags & EPOCA_DEGRADADA) != 0; }

  // Quantas epocas base esta epoca cobre.
  uint32_t largura_em_slots() const { return 1u << nivel; }

  // Primeiro slot da grade coberto por esta epoca.
  uint32_t primeiro_slot() const { return indice * largura_em_slots(); }
};

// Tamanho do registro, fixado por `static_assert` em epoca.cpp.
const uint32_t TAMANHO_DA_EPOCA_BYTES = 32;

// Funde `b` (posterior) em `a` (anterior), produzindo a epoca de nivel n+1.
// Pre-condicao: mesmo nivel e adjacencia na grade (a->indice par, b == a+1).
// O chamador (`BufferDeEpocas::degradar`) e quem garante isso.
void fundir(Epoca *a, const Epoca &b);

// ── Acumulador ─────────────────────────────────────────────────────────
//
// Recebe amostras e fecha epocas na grade. Nao conhece buffer, nem rede, nem
// Arduino: so recebe (mono_ms, ax, ay, az, temp) e avisa quando uma epoca
// fechou.
class AcumuladorDeEpoca {
 public:
  // O callback recebe cada epoca fechada. `contexto` e repassado sem
  // interpretacao, para esta camada nao precisar conhecer o tipo do buffer.
  typedef void (*AoFechar)(const Epoca &, void *contexto);

  AcumuladorDeEpoca();

  // Zera, ancora a grade em `mono_ms` (o slot 0 comeca aqui) e registra para
  // quem entregar as epocas fechadas.
  //
  // POR QUE O CALLBACK FICA AQUI, E NAO SO NO `fechar_ate`: na primeira
  // versao o fechamento era preguicoso e `amostrar` recusava amostra de um
  // slot futuro, porque nao tinha como fechar o anterior. O efeito era que
  // toda amostra que caisse exatamente na virada de epoca -- uma em cada
  // tres, na cadencia de 10 s -- sumia, e a epoca saia marcada incompleta sem
  // que nada estivesse errado com a medicao. Com o callback guardado,
  // `amostrar` fecha o que tiver de fechar antes de arquivar a amostra, e a
  // ordem das chamadas no laco deixa de importar.
  void iniciar(uint64_t mono_ms, uint16_t amostras_esperadas_por_epoca,
               AoFechar callback, void *contexto);

  // Indice do slot de grade a que um instante pertence.
  uint32_t slot_de(uint64_t mono_ms) const;

  // Instante monotonico em que um slot comeca.
  uint64_t inicio_do_slot(uint32_t slot) const;

  // Registra uma amostra valida. `total` e a magnitude ja calculada.
  void amostrar(uint64_t mono_ms, float ax, float ay, float az, float total, float temp);

  // Registra que uma amostra foi TENTADA e saiu fisicamente impossivel.
  // Conta como amostra perdida e marca a epoca. Nao contamina o pico.
  void amostrar_invalida(uint64_t mono_ms);

  // Fecha todas as epocas ja terminadas em `mono_ms`, INCLUSIVE as que nao
  // receberam amostra nenhuma (marcadas EPOCA_VAZIA). E aqui que a perda de
  // cadencia vira registro em vez de virar silencio.
  //
  // O laco chama isto a cada volta, mesmo sem ter amostrado: e o que garante
  // que uma noite com o sensor solto produza lacunas declaradas em vez de
  // nada.
  void fechar_ate(uint64_t mono_ms);

  bool iniciado() const { return iniciado_; }
  uint32_t slot_corrente() const { return slot_corrente_; }
  uint64_t ancora_ms() const { return ancora_ms_; }
  uint64_t inicio_da_epoca_corrente() const { return inicio_do_slot(slot_corrente_); }

 private:
  void zerar_corrente(uint32_t slot);

  bool iniciado_;
  uint64_t ancora_ms_;
  uint16_t esperadas_;
  uint32_t slot_corrente_;
  Epoca corrente_;
  bool corrente_tem_amostra_;
  AoFechar callback_;
  void *contexto_;
};

}  // namespace dormio

#endif  // DORMIO_NUCLEO_EPOCA_H
