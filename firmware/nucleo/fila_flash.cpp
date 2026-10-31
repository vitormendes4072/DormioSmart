// fila_flash.cpp -- ver fila_flash.h.

#include "fila_flash.h"

#include "cadeia_c2.h"
#include "reamostragem.h"

namespace dormio {

FilaNaFlash::FilaNaFlash(MidiaFlash *midia)
    : midia_(midia), montada_(false), slots_(0), cabeca_(0), cauda_(0), pendentes_(0),
      prox_seq_(1), sessao_(1) {}

EstadoDoSlot FilaNaFlash::ler_slot(uint32_t slot, RegistroDeEpoca *r, bool *ok) {
  uint8_t bytes[TAMANHO_DO_REGISTRO_FLASH_BYTES];
  *ok = midia_->ler(slot * TAMANHO_DO_REGISTRO_FLASH_BYTES, bytes, sizeof(bytes));
  if (!*ok) return SLOT_CORROMPIDO;
  return classificar_slot(bytes, r);
}

bool FilaNaFlash::slot_em_branco(uint32_t slot, bool *ok) {
  return ler_slot(slot, 0, ok) == SLOT_VAZIO;
}

bool FilaNaFlash::setor_tem_pendente(uint32_t primeiro_slot, bool *ok) {
  for (uint32_t i = 0; i < REGISTROS_POR_SETOR; i++) {
    RegistroDeEpoca r;
    if (ler_slot(primeiro_slot + i, &r, ok) == SLOT_VALIDO && !r.foi_entregue()) return true;
    if (!*ok) return true;  // na duvida, nao apaga
  }
  return false;
}

bool FilaNaFlash::montar() {
  montada_ = false;
  const uint32_t bytes = midia_->tamanho();
  if (bytes % TAMANHO_DO_SETOR_BYTES != 0 || bytes < 2u * TAMANHO_DO_SETOR_BYTES) return false;
  slots_ = bytes / TAMANHO_DO_REGISTRO_FLASH_BYTES;

  bool achou = false;
  uint32_t maior_seq = 0;
  uint32_t slot_da_maior = 0;
  uint16_t maior_sessao = 0;
  stats_.corrompidos_na_montagem = 0;

  for (uint32_t s = 0; s < slots_; s++) {
    RegistroDeEpoca r;
    bool ok;
    const EstadoDoSlot e = ler_slot(s, &r, &ok);
    if (!ok) return false;
    if (e == SLOT_CORROMPIDO) stats_.corrompidos_na_montagem++;
    if (e != SLOT_VALIDO) continue;
    if (!achou || r.seq > maior_seq) {
      maior_seq = r.seq;
      slot_da_maior = s;
    }
    if (!achou || r.sessao > maior_sessao) maior_sessao = r.sessao;
    achou = true;
  }

  cabeca_ = achou ? proximo(slot_da_maior) : 0;
  prox_seq_ = achou ? maior_seq + 1u : 1u;
  sessao_ = static_cast<uint16_t>(achou ? maior_sessao + 1u : 1u);

  // A ordem fisica, a partir da cabeca e dando a volta, e a ordem de
  // gravacao: a cabeca esta sobre o setor mais antigo (ou sobre o fim do
  // atual, em branco). O primeiro pendente nesse caminho e o mais antigo.
  pendentes_ = 0;
  cauda_ = cabeca_;
  bool primeiro = true;
  uint32_t s = cabeca_;
  for (uint32_t passo = 0; passo < slots_; passo++, s = proximo(s)) {
    RegistroDeEpoca r;
    bool ok;
    if (ler_slot(s, &r, &ok) != SLOT_VALIDO || r.foi_entregue()) continue;
    if (primeiro) {
      cauda_ = s;
      primeiro = false;
    }
    pendentes_++;
  }

  montada_ = true;
  return true;
}

ResultadoDaGuarda FilaNaFlash::guardar(const Epoca &e, const VetorDeFeatures *vetor,
                                       const InstanteDaEpoca &instante) {
  if (!montada_) return FILA_NAO_MONTADA;

  // Acha um slot em branco a partir da cabeca. No primeiro slot de um setor,
  // o setor inteiro e apagado -- se nao tiver pendente. No meio de um setor,
  // slot sujo (gravacao cortada antes de um reset) e pulado: programar por
  // cima dele so poderia levar bits a 0, e o resultado seria lixo.
  for (uint32_t tentativas = 0; tentativas <= REGISTROS_POR_SETOR; tentativas++) {
    bool ok;
    if (cabeca_ % REGISTROS_POR_SETOR == 0) {
      bool limpo = true;
      for (uint32_t i = 0; i < REGISTROS_POR_SETOR && limpo; i++) {
        limpo = slot_em_branco(cabeca_ + i, &ok);
        if (!ok) return FALHA_NA_FLASH;
      }
      if (!limpo) {
        if (setor_tem_pendente(cabeca_, &ok)) {
          if (!ok) return FALHA_NA_FLASH;
          stats_.descartes++;
          return FILA_CHEIA;
        }
        if (!midia_->apagar_setor(cabeca_ * TAMANHO_DO_REGISTRO_FLASH_BYTES)) {
          stats_.falhas_de_escrita++;
          return FALHA_NA_FLASH;
        }
        stats_.apagamentos++;
      }
      break;
    }
    if (slot_em_branco(cabeca_, &ok)) break;
    if (!ok) return FALHA_NA_FLASH;
    stats_.slots_pulados++;
    cabeca_ = proximo(cabeca_);
  }

  RegistroDeEpoca r;
  r.seq = prox_seq_;
  r.sessao = sessao_;
  r.bandeiras = 0;
  if (vetor) r.bandeiras |= REGISTRO_TEM_FEATURES;
  if (instante.e_parede) r.bandeiras |= REGISTRO_INSTANTE_E_PAREDE;
  r.entregue = ENTREGUE_PENDENTE;
  r.instante_s = instante.segundos;
  r.epoca = e;
  if (vetor) {
    r.vetor = *vetor;
  } else {
    // Zeros definidos, e nao o construtor (que poe gz = 32767): o CRC cobre
    // estes bytes, e o conteudo deles tem de ser o mesmo em toda placa.
    VetorDeFeatures zero;
    zero.gz = 0;
    r.vetor = zero;
  }
  r.crc = 0;

  uint8_t bytes[TAMANHO_DO_REGISTRO_FLASH_BYTES];
  serializar_registro(r, bytes);
  const uint32_t slot = cabeca_;
  cabeca_ = proximo(cabeca_);
  prox_seq_++;

  // A releitura e a unica prova de que a flash guardou: `programar` devolver
  // true diz que o comando foi aceito, nao que os bits ficaram.
  RegistroDeEpoca lido;
  bool ok;
  if (!midia_->programar(slot * TAMANHO_DO_REGISTRO_FLASH_BYTES, bytes, sizeof(bytes)) ||
      ler_slot(slot, &lido, &ok) != SLOT_VALIDO || lido.seq != r.seq) {
    stats_.falhas_de_escrita++;
    return FALHA_NA_FLASH;
  }

  if (pendentes_ == 0) cauda_ = slot;
  pendentes_++;
  stats_.guardados++;
  return GUARDADO;
}

uint32_t FilaNaFlash::ler_pendentes(RegistroDeEpoca *destino, uint32_t max) {
  uint32_t n = 0;
  uint32_t s = cauda_;
  for (uint32_t passo = 0; passo < slots_ && n < max && n < pendentes_; passo++, s = proximo(s)) {
    RegistroDeEpoca r;
    bool ok;
    if (ler_slot(s, &r, &ok) != SLOT_VALIDO || r.foi_entregue()) continue;
    destino[n++] = r;
  }
  return n;
}

void FilaNaFlash::avancar_cauda() {
  if (pendentes_ == 0) {
    cauda_ = cabeca_;
    return;
  }
  uint32_t s = cauda_;
  for (uint32_t passo = 0; passo < slots_; passo++, s = proximo(s)) {
    RegistroDeEpoca r;
    bool ok;
    if (ler_slot(s, &r, &ok) == SLOT_VALIDO && !r.foi_entregue()) {
      cauda_ = s;
      return;
    }
  }
}

uint32_t FilaNaFlash::confirmar(uint32_t k) {
  uint32_t marcados = 0;
  uint32_t s = cauda_;
  for (uint32_t passo = 0; passo < slots_ && marcados < k && pendentes_ > 0;
       passo++, s = proximo(s)) {
    RegistroDeEpoca r;
    bool ok;
    if (ler_slot(s, &r, &ok) != SLOT_VALIDO || r.foi_entregue()) continue;
    const uint8_t zero = ENTREGUE_CONFIRMADO;
    if (!midia_->programar(s * TAMANHO_DO_REGISTRO_FLASH_BYTES + OFFSET_DO_ENTREGUE, &zero, 1)) {
      stats_.falhas_de_escrita++;
      break;
    }
    marcados++;
    pendentes_--;
  }
  stats_.confirmados += marcados;
  avancar_cauda();
  return marcados;
}

ResultadoDeMontagem montar_payload_do_registro(const RegistroDeEpoca &r, uint16_t sessao_atual,
                                               const ResolucaoDeParede &parede_atual,
                                               char *destino, uint32_t tamanho,
                                               uint32_t *escritos, bool *features_incluidas) {
  ResolucaoDeParede usar;
  uint64_t mono_ms = 0;
  resolucao_para_envio(r, sessao_atual, parede_atual, &usar, &mono_ms);
  if (!r.tem_features()) {
    return montar_payload(r.epoca, usar, mono_ms, destino, tamanho, escritos, 0, 0.0f,
                          features_incluidas);
  }
  // A cadeia C2 entrega sempre 960 pontos por epoca de 30 s, e e esse o
  // denominador de `zcr` e `p_frac` (`desquantizar` precisa dele).
  const FeaturesDeEpoca f = desquantizar(r.vetor, static_cast<uint16_t>(AMOSTRAS_NA_GRADE));
  return montar_payload(r.epoca, usar, mono_ms, destino, tamanho, escritos, &f, TAXA_DA_GRADE_HZ,
                        features_incluidas);
}

}  // namespace dormio
