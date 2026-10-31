// registro_flash.cpp -- ver registro_flash.h.

#include "registro_flash.h"

#include <stddef.h>
#include <string.h>

namespace dormio {

// O layout e o contrato com o que ja esta gravado na flash: mudar um offset
// torna ilegivel toda noite guardada. O build quebra antes.
static_assert(sizeof(RegistroDeEpoca) == TAMANHO_DO_REGISTRO_FLASH_BYTES,
              "o registro da flash tem 64 B; um campo novo muda a capacidade e o layout gravado");
static_assert(offsetof(RegistroDeEpoca, entregue) == OFFSET_DO_ENTREGUE,
              "a confirmacao programa este byte no lugar");
static_assert(offsetof(RegistroDeEpoca, epoca) == 12, "layout gravado");
static_assert(offsetof(RegistroDeEpoca, vetor) == 44, "layout gravado");
static_assert(offsetof(RegistroDeEpoca, crc) == 62, "layout gravado");
static_assert(4096 % TAMANHO_DO_REGISTRO_FLASH_BYTES == 0,
              "registro nenhum pode atravessar setor");

static const uint32_t BYTES_COBERTOS_PELO_CRC = 62;

uint16_t crc_do_registro(const uint8_t *bytes) {
  uint16_t crc = 0xFFFF;
  for (uint32_t i = 0; i < BYTES_COBERTOS_PELO_CRC; i++) {
    if (i == OFFSET_DO_ENTREGUE) continue;
    crc = static_cast<uint16_t>(crc ^ static_cast<uint16_t>(bytes[i] << 8));
    for (int b = 0; b < 8; b++) {
      crc = (crc & 0x8000u) ? static_cast<uint16_t>((crc << 1) ^ 0x1021u)
                            : static_cast<uint16_t>(crc << 1);
    }
  }
  return crc;
}

EstadoDoSlot classificar_slot(const uint8_t *bytes, RegistroDeEpoca *saida) {
  bool vazio = true;
  for (uint32_t i = 0; i < TAMANHO_DO_REGISTRO_FLASH_BYTES; i++) {
    if (bytes[i] != 0xFF) {
      vazio = false;
      break;
    }
  }
  if (vazio) return SLOT_VAZIO;

  RegistroDeEpoca r;
  memcpy(&r, bytes, sizeof(r));
  // `seq` vazia com o resto programado tambem e corte: um registro valido
  // nunca tem essa seq, porque ela e o marcador de slot vazio.
  if (r.seq == SEQ_VAZIA || r.crc != crc_do_registro(bytes)) return SLOT_CORROMPIDO;
  if (saida) *saida = r;
  return SLOT_VALIDO;
}

void serializar_registro(const RegistroDeEpoca &r, uint8_t *destino) {
  RegistroDeEpoca copia = r;
  copia.entregue = ENTREGUE_PENDENTE;
  copia.crc = 0;
  memcpy(destino, &copia, sizeof(copia));
  copia.crc = crc_do_registro(destino);
  memcpy(destino, &copia, sizeof(copia));
}

InstanteDaEpoca instante_para_gravar(const ResolucaoDeParede &parede, uint64_t mono_inicio_ms) {
  InstanteDaEpoca i;
  if (parede.valida) {
    const int64_t unix_ms = parede.resolver(mono_inicio_ms);
    if (unix_ms >= 0 && unix_ms / 1000 <= 0xFFFFFFFFll) {
      i.e_parede = true;
      i.segundos = static_cast<uint32_t>(unix_ms / 1000);
      return i;
    }
  }
  i.e_parede = false;
  i.segundos = static_cast<uint32_t>(mono_inicio_ms / 1000u);
  return i;
}

void resolucao_para_envio(const RegistroDeEpoca &r, uint16_t sessao_atual,
                          const ResolucaoDeParede &parede_atual, ResolucaoDeParede *usar,
                          uint64_t *mono_ms) {
  *usar = ResolucaoDeParede();
  if (r.instante_e_parede()) {
    usar->sincronizar(0, static_cast<int64_t>(r.instante_s) * 1000);
    *mono_ms = 0;
    return;
  }
  *mono_ms = static_cast<uint64_t>(r.instante_s) * 1000u;
  if (r.sessao == sessao_atual && parede_atual.valida) *usar = parede_atual;
}

}  // namespace dormio
