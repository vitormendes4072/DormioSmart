// registro_flash.h -- o registro de 64 B que a fila grava na flash (FW-08).
//
// ── O QUE ELE GUARDA, E POR QUE CADA CAMPO ─────────────────────────────
//
// A fila em RAM (`buffer.h`) guarda so a `Epoca`, de 32 B. Para a noite
// chegar ao servidor com o vetor de caracteristicas, o registro durável
// precisa de mais tres coisas:
//
//   - o vetor quantizado (`VetorDeFeatures`, 18 B), que o DATA-07b ja definiu;
//   - o INSTANTE da epoca, resolvido na hora de gravar. A fila em RAM guarda
//     so o indice na grade e resolve a hora no envio, a partir do relogio
//     monotonico -- que volta a zero num reset. Na flash o registro sobrevive
//     ao reset, e o relogio que o datava nao;
//   - o que a flash exige para ser lida depois de um corte de energia: a
//     ordem (`seq`), a integridade (`crc`) e a marca de entregue.
//
// ── O LAYOUT, BYTE A BYTE ──────────────────────────────────────────────
//
//   0  seq          u32   ordem global de gravacao; 0xFFFFFFFF = slot vazio
//   4  sessao       u16   qual ligamento do dispositivo gravou
//   6  bandeiras    u8    REGISTRO_TEM_FEATURES, REGISTRO_INSTANTE_E_PAREDE
//   7  entregue     u8    0xFF pendente, 0x00 entregue -- FORA do CRC
//   8  instante_s   u32   inicio da epoca: unix s, ou s desde o boot
//  12  epoca        32 B  a `Epoca` de sempre
//  44  vetor        18 B  `VetorDeFeatures`; lixo definido (zeros) sem features
//  62  crc          u16   CRC-16/CCITT dos bytes 0..61, pulando o byte 7
//
// 64 B, quatro por pagina de 256 B, 64 por setor de 4 KiB: nenhum registro
// atravessa setor, e apagar um setor nunca leva meio registro.
//
// ── POR QUE `entregue` FICA FORA DO CRC ────────────────────────────────
//
// Flash NOR so muda bit de 1 para 0 sem apagar, e apaga de 4 KiB em 4 KiB.
// A confirmacao de entrega, entao, nao reescreve o registro: programa UM
// byte, de 0xFF para 0x00, no lugar. Se esse byte entrasse no CRC, todo
// registro entregue pareceria corrompido.
//
// E so `0x00` conta como entregue. Um corte de energia no meio da
// programacao desse byte pode deixar qualquer valor entre os dois; nesse
// caso o registro e tratado como PENDENTE e volta no proximo lote. Mesmo
// principio do lote (`lote.h`): duplicata no servidor, nunca perda aqui.
//
// ── POR QUE O INSTANTE TEM RESOLUCAO DE SEGUNDO ────────────────────────
//
// Sobravam 4 B para ele. Em segundos, unix cabe em u32 ate 2106. O preco e o
// `ts` sair com `.000` quando o instante foi resolvido na gravacao. A
// diferenca entre epocas consecutivas continua sendo 30 s exatos
// (piso(t + 30k) - piso(t + 30(k-1)) = 30, porque 30 e inteiro), que e o que
// a deteccao de lacuna do servidor usa.

#ifndef DORMIO_NUCLEO_REGISTRO_FLASH_H
#define DORMIO_NUCLEO_REGISTRO_FLASH_H

#include <stdint.h>

#include "caracteristicas.h"
#include "epoca.h"
#include "relogio.h"

namespace dormio {

const uint32_t TAMANHO_DO_REGISTRO_FLASH_BYTES = 64;
const uint32_t SEQ_VAZIA = 0xFFFFFFFFu;
const uint8_t ENTREGUE_PENDENTE = 0xFF;
const uint8_t ENTREGUE_CONFIRMADO = 0x00;

enum BandeirasDoRegistro {
  // O vetor em `vetor` vale. Sem a bandeira, `vetor` e zeros e o payload sai
  // sem `f` -- e o caso da epoca que a cadeia nao conseguiu medir.
  REGISTRO_TEM_FEATURES = 1 << 0,

  // `instante_s` e hora de parede (unix s). Sem a bandeira e tempo
  // monotonico em segundos desde o boot da `sessao` que gravou -- e so
  // resolvivel enquanto esta sessao for a corrente.
  REGISTRO_INSTANTE_E_PAREDE = 1 << 1,
};

// POD com larguras fixas: o `static_assert` no .cpp trava tamanho e offsets,
// pelo mesmo motivo de `Epoca` -- a medicao feita no host tem de valer na
// placa, e os dois sao little-endian de 32/64 bits sem padding aqui.
struct RegistroDeEpoca {
  uint32_t seq;
  uint16_t sessao;
  uint8_t bandeiras;
  uint8_t entregue;
  uint32_t instante_s;
  Epoca epoca;
  VetorDeFeatures vetor;
  uint16_t crc;

  bool tem_features() const { return (bandeiras & REGISTRO_TEM_FEATURES) != 0; }
  bool instante_e_parede() const { return (bandeiras & REGISTRO_INSTANTE_E_PAREDE) != 0; }
  bool foi_entregue() const { return entregue == ENTREGUE_CONFIRMADO; }
};

// Onde fica o byte de `entregue` dentro do registro gravado.
const uint32_t OFFSET_DO_ENTREGUE = 7;

// CRC-16/CCITT-FALSE (polinomio 0x1021, inicio 0xFFFF) dos 62 primeiros
// bytes, pulando `entregue`.
uint16_t crc_do_registro(const uint8_t *bytes);

// O que a varredura encontra num slot de 64 B.
enum EstadoDoSlot {
  SLOT_VAZIO = 0,      // os 64 B em 0xFF: apagado e nunca programado
  SLOT_VALIDO = 1,     // CRC confere
  SLOT_CORROMPIDO = 2  // nem vazio nem valido: gravacao cortada, ou apagamento cortado
};

EstadoDoSlot classificar_slot(const uint8_t *bytes, RegistroDeEpoca *saida);

// Serializa com o CRC calculado e `entregue` = pendente.
void serializar_registro(const RegistroDeEpoca &r, uint8_t *destino);

// ── O instante ─────────────────────────────────────────────────────────

struct InstanteDaEpoca {
  bool e_parede;
  uint32_t segundos;

  InstanteDaEpoca() : e_parede(false), segundos(0) {}
};

// Resolve, NA GRAVACAO, o instante de inicio da epoca. Com o relogio de parede
// sincronizado, grava hora de parede -- e o registro deixa de depender do
// relogio monotonico deste boot. Sem sincronia, grava o monotonico, e so esta
// sessao consegue resolve-lo depois.
InstanteDaEpoca instante_para_gravar(const ResolucaoDeParede &parede, uint64_t mono_inicio_ms);

// Monta o que `montar_payload` precisa para datar um registro: a resolucao a
// usar e o instante monotonico a passar. Tres casos:
//
//   - parede gravada: resolucao fixa em (0 -> instante), mono 0;
//   - monotonico DESTA sessao, com a parede ja sincronizada agora: a
//     resolucao corrente, mono = instante;
//   - monotonico de outra sessao, ou parede ainda nao sincronizada:
//     resolucao invalida -- o payload sai SEM `ts`, e o servidor usa a hora
//     de chegada. A hora daquela epoca se perdeu com o reset; a leitura nao.
void resolucao_para_envio(const RegistroDeEpoca &r, uint16_t sessao_atual,
                          const ResolucaoDeParede &parede_atual, ResolucaoDeParede *usar,
                          uint64_t *mono_ms);

}  // namespace dormio

#endif  // DORMIO_NUCLEO_REGISTRO_FLASH_H
