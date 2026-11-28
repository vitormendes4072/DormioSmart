// envio_da_fila.h -- da fila na flash ao POST /api/data/lote, e de volta (FW-07 (b)).
//
// As tres pecas ja existiam e estao testadas: a fila (`fila_flash.h`), o
// envelope do lote e a leitura da resposta (`lote.h`). O que faltava e a
// regra que as junta, e ela tem duas armadilhas que nao podem ficar no
// sketch, onde nada as testa:
//
// ── O LOTE E SEMPRE UM PREFIXO CONTIGUO DA FILA ────────────────────────
//
// O servidor responde "as k primeiras do lote sairam" (`DecisaoDoLote`), e a
// fila confirma "os k pendentes mais antigos" (`FilaNaFlash::confirmar`). Os
// dois so falam da mesma coisa se o lote for exatamente o comeco da fila, na
// ordem, sem pular nenhum registro.
//
// ── UM REGISTRO QUE NAO VIRA PAYLOAD NAO PODE TRAVAR A FILA ────────────
//
// `montar_payload` recusa epoca vazia e pico fora da faixa fisica. Um
// registro assim nunca sera enviavel, e se ficar na frente da fila o lote sai
// vazio para sempre -- a noite inteira atras dele nao chega. Ele e
// confirmado localmente (sai da fila) e contado. So quando esta NA FRENTE:
// no meio de um lote, o lote para antes dele, e ele chega a frente na
// proxima volta. E o que mantem o lote um prefixo contiguo.

#ifndef DORMIO_NUCLEO_ENVIO_DA_FILA_H
#define DORMIO_NUCLEO_ENVIO_DA_FILA_H

#include <stdint.h>

#include "fila_flash.h"
#include "lote.h"
#include "relogio.h"

namespace dormio {

struct PreparoDoLote {
  uint32_t no_lote;      // leituras no envelope = `enviadas` da resposta
  uint32_t descartados;  // registros sem payload possivel, tirados da frente
  uint32_t tamanho;      // bytes do JSON (0 = nada a enviar)
};

// Monta em `destino` o lote com o comeco da fila, ate `max` leituras.
// `rascunho` precisa de `max` posicoes (64 B cada).
PreparoDoLote preparar_lote(FilaNaFlash *fila, const ResolucaoDeParede &parede,
                            RegistroDeEpoca *rascunho, uint32_t max, char *destino,
                            uint32_t tamanho, const char *sensor = nullptr);

// Le a resposta do servidor e confirma na fila o prefixo que saiu.
DecisaoDoLote aplicar_resposta(FilaNaFlash *fila, int status_http, const char *corpo,
                               uint32_t tamanho, uint32_t enviadas);

// ── O tamanho do lote (FW-14, etapa 2) ─────────────────────────────────
//
// O maior texto que uma leitura da fila de flash vira em `preparar_lote`.
// Ate 17/11 o buffer do lote era dimensionado a 520 B por leitura, sem
// conta; na noite de 17/11 o maior lote de 20 deu 6 127 B (~306 B cada).
// O pior caso soma o texto mais longo de cada campo: os eixos e o pico no
// teto plausivel (-135,87), a temperatura no fim da faixa do registrador
// (-59,9), o `ts`, `amostras` 65535 e cada uma das 9 features no valor
// quantizado de texto mais longo -- 341 B. `testar_pior_caso_da_leitura`
// refaz a conta e reprova se ela passar deste numero. Se um dia passar (um
// campo novo no contrato), o lote nao estoura: fecha com menos leituras, e o
// resto vai no seguinte.
const uint32_t PIOR_LEITURA_BYTES = 360;

// Inclui o maior texto de sensor no envelope, uma vez por lote.
// O buffer de um lote de `leituras` no pior caso: a abertura
// `{"leituras":[` (13), as leituras com as virgulas entre elas, `]}` e o NUL.
constexpr uint32_t tamanho_do_lote(uint32_t leituras) {
  return 13u + SENSOR_DO_LOTE_BYTES + leituras * PIOR_LEITURA_BYTES + (leituras > 0 ? leituras - 1u : 0u) + 2u + 1u;
}

// ── A folga de memoria do envio (FW-14) ───────────────────────────────
//
// O handshake TLS pede ~67 KB de uma vez, e o minimo de heap no envio vinha
// caindo (14 772 B em 12/11, 12 868 B em 16/11). Antes de cortar qualquer
// coisa, medir de onde vem a falta: as pilhas das duas tarefas (dimensionadas
// sem medida), o maior bloco contiguo (o TLS precisa dele, nao do total) e o
// maior lote montado (o buffer era dimensionado a 520 B por leitura; desde a
// etapa 2, pelo pior caso, `tamanho_do_lote`).
struct FolgaDeMemoria {
  uint32_t heap_livre;
  uint32_t heap_minimo;           // o pior desde o boot
  uint32_t maior_bloco_antes;     // antes de ligar o radio
  uint32_t maior_bloco_depois;    // depois do envio
  uint32_t pilha_envio_livre;     // o que nunca foi usado da pilha, em bytes
  uint32_t pilha_envio_total;
  uint32_t pilha_medicao_livre;
  uint32_t pilha_medicao_total;
  uint32_t maior_lote;            // bytes do maior JSON montado
  uint32_t buffer_do_lote;
  uint32_t conexoes_tls;          // conexoes abertas (handshakes) nesta sessao
  uint32_t lotes;                 // lotes enviados nesta sessao
};

// Abaixo disto livre numa das pilhas, a linha `[memoria]` termina em
// `; PILHA BAIXA` (FW-14, etapa 2). As pilhas foram cortadas pela medida de
// uma noite; um caminho que a noite nao exercitou aparece aqui antes de
// estourar (e, estourando, a protecao de estouro do FreeRTOS reinicia a placa).
const uint32_t LIMIAR_DE_PILHA_BAIXA_BYTES = 1024;

// Escreve a linha `[memoria] ...` do log em `destino`. Devolve os caracteres
// escritos, ou 0 se nao coube.
uint32_t formatar_folga(const FolgaDeMemoria &f, char *destino, uint32_t tamanho);

}  // namespace dormio

#endif  // DORMIO_NUCLEO_ENVIO_DA_FILA_H
