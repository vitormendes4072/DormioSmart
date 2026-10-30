// lote.h -- o lado do dispositivo do `POST /api/data/lote` (API-03).
//
// Na arquitetura C2 o radio e 63 % da corrente media com uma entrega por
// epoca; uma entrega por hora a reduz de 5,31 para 2,03 mA
// (`docs/DECISAO-ARQ-01-CADENCIA.md` §4.2). Este modulo monta o envelope e
// decide, a partir da resposta, quantas epocas saem da fila.
//
// ── A REGRA QUE TORNA ISTO SIMPLES ────────────────────────────────────
//
// O servidor processa as leituras EM ORDEM e para na primeira falha do banco
// ou no fim do orcamento de tempo (contrato v2.6.0 §5.2). Entao `pendentes`
// e sempre um SUFIXO do lote: tudo antes do primeiro pendente foi gravado ou
// rejeitado de vez, e tudo a partir dele volta. O dispositivo confirma um
// PREFIXO da fila -- que e a unica operacao que a fila de epocas sabe fazer
// sem furar a serie.
//
// Se a resposta nao respeitar isso (indice repetido, faltando, fora do lote,
// pendentes que nao formam um sufixo), ela e tratada como ilegivel: nada
// sai da fila e o lote volta inteiro. O custo e duplicata no servidor; o
// custo do contrario seria apagar do dispositivo um dado que talvez nao
// tenha sido gravado. Duplicata se limpa depois; perda, nao.
//
// ⚠️ A duplicata NAO esta resolvida (contrato §5.2): se a resposta se perder
// depois da gravacao, o dispositivo reenvia o que ja foi gravado. O lote so
// concentra um risco que o `/api/data` sempre teve.

#ifndef DORMIO_NUCLEO_LOTE_H
#define DORMIO_NUCLEO_LOTE_H

#include <stdint.h>

namespace dormio {

// O teto do servidor (`web-app/lote.py`, MAX_LEITURAS_POR_LOTE). Mais que isso
// e `413` e nada e gravado.
const uint32_t MAX_LEITURAS_POR_LOTE = 60;

// Monta `{"leituras":[<l0>,<l1>,...]}` num buffer de tamanho fixo, uma leitura
// por vez. Cada leitura e o JSON que `montar_payload` ja produz -- o mesmo
// corpo do `POST /api/data`, validado pelas mesmas regras no servidor.
class MontadorDeLote {
 public:
  MontadorDeLote(char *destino, uint32_t capacidade);

  // Acrescenta uma leitura. Devolve false -- e nao muda nada -- se ela nao
  // cabe junto com o fechamento, ou se o lote ja tem `MAX_LEITURAS_POR_LOTE`.
  // Quem chama envia o que ja tem e deixa esta para o proximo lote.
  bool adicionar(const char *leitura_json, uint32_t tamanho);

  // Fecha o envelope e devolve o tamanho final (sem o NUL), ou 0 se o lote
  // esta vazio -- lote vazio o servidor recusa com 400, e nao ha por que
  // gastar radio com isso.
  uint32_t fechar();

  uint32_t quantidade() const { return quantidade_; }

 private:
  char *destino_;
  uint32_t capacidade_;
  uint32_t usado_;
  uint32_t quantidade_;
};

enum AcaoDoLote {
  // Confirmar `confirmar` epocas do inicio da fila e seguir.
  LOTE_CONFIRMAR = 0,
  // Nada sai da fila; esperar o backoff (`reconexao.h`) e tentar de novo.
  LOTE_RECUAR = 1,
  // 413: o lote era grande demais. Nada sai da fila; mandar metade.
  LOTE_DIVIDIR = 2,
};

struct DecisaoDoLote {
  AcaoDoLote acao;
  uint32_t confirmar;   // quantas epocas saem do inicio da fila
  uint32_t aceitas;     // gravadas (para o log)
  uint32_t rejeitadas;  // invalidas, descartadas de vez (para o log)
  uint32_t pendentes;   // voltam no proximo lote
  // Com pendentes, o servidor parou por falha do banco ou fim do tempo:
  // depois de confirmar o prefixo, esperar o backoff antes do proximo lote,
  // em vez de reenviar no mesmo instante contra o mesmo banco caido.
  bool recuar_depois;
  bool resposta_ilegivel;
};

// Le o status e o corpo da resposta de um lote de `enviadas` leituras.
//
//   200 ou 503 com as tres listas coerentes -> CONFIRMAR o prefixo antes do
//       primeiro pendente (com 503 esse prefixo e vazio por definicao do
//       servidor, mas a regra e a mesma). Se nao sobrou nada confirmado e ha
//       pendentes, RECUAR em vez de reenviar no mesmo instante.
//   413 -> DIVIDIR.
//   qualquer outro (400, 401, 404, 5xx sem corpo, erro de transporte < 0)
//       -> RECUAR, sem tirar nada da fila.
//
// `corpo` pode ser 0 ou nao ter NUL ate `tamanho`: so `tamanho` bytes sao
// lidos.
DecisaoDoLote interpretar_resposta_do_lote(int status_http, const char *corpo,
                                           uint32_t tamanho, uint32_t enviadas);

}  // namespace dormio

#endif  // DORMIO_NUCLEO_LOTE_H
