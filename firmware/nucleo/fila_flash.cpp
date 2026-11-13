// fila_flash.cpp -- ver fila_flash.h.

#include "fila_flash.h"

#include "cadeia_c2.h"
#include "reamostragem.h"

namespace dormio {

const uint8_t MARCA_DO_FORMATO_DA_FILA[8] = {'D', 'O', 'R', 'M', 'I', 'O', 'F', '1'};

FilaNaFlash::FilaNaFlash(MidiaFlash *midia)
    : midia_(midia), montada_(false), slots_(0), endereco_do_cabecalho_(0), cabeca_(0),
      cauda_(0), pendentes_(0),
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

// O cabecalho: marca (8 B), versao (u16), tamanho do registro (u16) e numero
// de slots (u32), little-endian. Qualquer diferenca -- inclusive de tamanho
// da particao -- e outro formato, e a area e refeita.
static void montar_cabecalho(uint32_t slots, uint8_t *c) {
  for (uint32_t i = 0; i < TAMANHO_DO_CABECALHO_DA_FILA; i++) c[i] = 0;
  for (uint32_t i = 0; i < 8; i++) c[i] = MARCA_DO_FORMATO_DA_FILA[i];
  c[8] = static_cast<uint8_t>(VERSAO_DO_FORMATO_DA_FILA & 0xFF);
  c[9] = static_cast<uint8_t>(VERSAO_DO_FORMATO_DA_FILA >> 8);
  c[10] = static_cast<uint8_t>(TAMANHO_DO_REGISTRO_FLASH_BYTES & 0xFF);
  c[11] = static_cast<uint8_t>(TAMANHO_DO_REGISTRO_FLASH_BYTES >> 8);
  for (uint32_t i = 0; i < 4; i++) c[12 + i] = static_cast<uint8_t>(slots >> (8 * i));
}

bool FilaNaFlash::formato_confere(bool *ok) {
  uint8_t lido[TAMANHO_DO_CABECALHO_DA_FILA];
  uint8_t esperado[TAMANHO_DO_CABECALHO_DA_FILA];
  *ok = midia_->ler(endereco_do_cabecalho_, lido, sizeof(lido));
  if (!*ok) return false;
  montar_cabecalho(slots_, esperado);
  for (uint32_t i = 0; i < TAMANHO_DO_CABECALHO_DA_FILA; i++) {
    if (lido[i] != esperado[i]) return false;
  }
  return true;
}

bool FilaNaFlash::setor_em_branco(uint32_t endereco, bool *ok) {
  uint8_t bloco[TAMANHO_DO_REGISTRO_FLASH_BYTES];
  for (uint32_t d = 0; d < TAMANHO_DO_SETOR_BYTES; d += sizeof(bloco)) {
    *ok = midia_->ler(endereco + d, bloco, sizeof(bloco));
    if (!*ok) return false;
    for (uint32_t i = 0; i < sizeof(bloco); i++) {
      if (bloco[i] != 0xFF) return false;
    }
  }
  return true;
}

// Apaga so os setores que nao estao em branco (uma placa nova nao gasta
// apagamento nenhum) e por ultimo escreve o cabecalho: um corte de energia no
// meio deixa a area sem marca, e a proxima montagem recomeca a formatacao.
bool FilaNaFlash::formatar() {
  stats_.formatada_na_montagem = true;
  stats_.setores_apagados_na_formatacao = 0;
  const uint32_t setores = endereco_do_cabecalho_ / TAMANHO_DO_SETOR_BYTES + SETORES_DO_CABECALHO_DA_FILA;
  for (uint32_t s = 0; s < setores; s++) {
    const uint32_t endereco = s * TAMANHO_DO_SETOR_BYTES;
    bool ok;
    if (setor_em_branco(endereco, &ok)) continue;
    if (!ok) return false;
    if (!midia_->apagar_setor(endereco)) {
      stats_.falhas_de_escrita++;
      return false;
    }
    stats_.setores_apagados_na_formatacao++;
  }
  uint8_t c[TAMANHO_DO_CABECALHO_DA_FILA];
  montar_cabecalho(slots_, c);
  bool ok;
  if (!midia_->programar(endereco_do_cabecalho_, c, sizeof(c)) || !formato_confere(&ok)) {
    stats_.falhas_de_escrita++;
    return false;
  }
  return true;
}

bool FilaNaFlash::montar() {
  montada_ = false;
  const uint32_t bytes = midia_->tamanho();
  const uint32_t minimo = (2u + SETORES_DO_CABECALHO_DA_FILA) * TAMANHO_DO_SETOR_BYTES;
  if (bytes % TAMANHO_DO_SETOR_BYTES != 0 || bytes < minimo) return false;
  endereco_do_cabecalho_ = bytes - SETORES_DO_CABECALHO_DA_FILA * TAMANHO_DO_SETOR_BYTES;
  slots_ = endereco_do_cabecalho_ / TAMANHO_DO_REGISTRO_FLASH_BYTES;
  stats_.formatada_na_montagem = false;
  {
    bool ok;
    if (!formato_confere(&ok)) {
      if (!ok || !formatar()) return false;
    }
  }

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
                                       const InstanteDaEpoca &instante, bool calibrada) {
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
  if (calibrada) r.bandeiras |= REGISTRO_CALIBRADA;
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
  FeaturesDeEpoca f = desquantizar(r.vetor, static_cast<uint16_t>(AMOSTRAS_NA_GRADE));
  // A marca sai junto do vetor (contrato 2.9.0); o `gn` nao, porque o
  // registro nao o guarda (FW-11: caberia so aumentando o registro).
  f.calibrada = r.calibrada() ? 1 : 0;
  return montar_payload(r.epoca, usar, mono_ms, destino, tamanho, escritos, &f, TAXA_DA_GRADE_HZ,
                        features_incluidas);
}

}  // namespace dormio
