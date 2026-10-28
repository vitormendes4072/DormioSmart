#include "epoca.h"

namespace dormio {

// O layout do registro e contrato, nao detalhe: a medicao de capacidade roda
// no host e so vale para a placa se o tamanho for o mesmo nos dois. Se alguem
// acrescentar um campo aqui, esta linha quebra o build ANTES de a medicao
// passar a mentir.
//
// Se precisar mesmo crescer: mude tambem TAMANHO_DA_EPOCA_BYTES e rode
// `make capacidade` -- a autonomia offline muda junto, e por isso o numero
// precisa ser refeito, nao so o assert.
static_assert(sizeof(Epoca) == TAMANHO_DA_EPOCA_BYTES,
              "Epoca mudou de tamanho: refaca a medicao de capacidade");

void fundir(Epoca *a, const Epoca &b) {
  // Fotografa o estado ANTES de mexer nas flags. A primeira versao consultava
  // `a->vazia()` depois do OU de flags, e ai a resposta ja era a de `b` -- uma
  // epoca com dado fundida com uma lacuna saia marcada como lacuna, apagando o
  // dado que ela tinha. Os testes pegaram; a placa nao pegaria.
  const bool a_era_vazia = a->vazia();
  const bool b_era_vazia = b.vazia();

  // Maximo e associativo: o pico das duas E o pico da janela dobrada, exato.
  if (b_era_vazia && a_era_vazia) {
    // Duas lacunas viram uma lacuna maior. Nao ha pico a escolher.
  } else if (a_era_vazia) {
    // So `b` tem dado: o pico e o de `b`.
    a->pico_total = b.pico_total;
    a->pico_ax = b.pico_ax;
    a->pico_ay = b.pico_ay;
    a->pico_az = b.pico_az;
    a->temp_pico = b.temp_pico;
  } else if (!b_era_vazia && b.pico_total > a->pico_total) {
    a->pico_total = b.pico_total;
    a->pico_ax = b.pico_ax;
    a->pico_ay = b.pico_ay;
    a->pico_az = b.pico_az;
    a->temp_pico = b.temp_pico;
  }

  // Contagens somam. Saturam em vez de dar a volta: uma epoca com 65540
  // amostras reportando 4 seria pior que uma reportando 65535.
  uint32_t soma_amostras = static_cast<uint32_t>(a->amostras) + b.amostras;
  uint32_t soma_esperadas = static_cast<uint32_t>(a->esperadas) + b.esperadas;
  a->amostras = soma_amostras > 0xFFFFu ? 0xFFFFu : static_cast<uint16_t>(soma_amostras);
  a->esperadas = soma_esperadas > 0xFFFFu ? 0xFFFFu : static_cast<uint16_t>(soma_esperadas);

  // Flags se propagam por OU: qualquer ressalva de uma das metades vale para
  // o todo. Silenciar aqui seria fabricar confianca que a medicao nao tem.
  a->flags = static_cast<uint8_t>(a->flags | b.flags);

  // VAZIA so sobrevive se AMBAS eram vazias -- senao a epoca fundida tem
  // dado, e marca-la de vazia seria mentira.
  if (!a_era_vazia || !b_era_vazia) {
    a->flags = static_cast<uint8_t>(a->flags & ~EPOCA_VAZIA);
    if (a_era_vazia || b_era_vazia) {
      // Metade da janela sem amostra nenhuma: o todo e incompleto.
      a->flags = static_cast<uint8_t>(a->flags | EPOCA_INCOMPLETA);
    }
  }

  a->flags = static_cast<uint8_t>(a->flags | EPOCA_DEGRADADA);
  a->nivel = static_cast<uint8_t>(a->nivel + 1);
  a->indice = a->indice / 2;  // indice passa a ser o da grade do novo nivel

  uint32_t nova_duracao = static_cast<uint32_t>(a->duracao_s) + b.duracao_s;
  a->duracao_s = nova_duracao > 0xFFFFu ? 0xFFFFu : static_cast<uint16_t>(nova_duracao);
}

// ── Acumulador ─────────────────────────────────────────────────────────

AcumuladorDeEpoca::AcumuladorDeEpoca()
    : iniciado_(false), ancora_ms_(0), esperadas_(0), slot_corrente_(0),
      corrente_tem_amostra_(false), callback_(0), contexto_(0) {}

void AcumuladorDeEpoca::iniciar(uint64_t mono_ms, uint16_t amostras_esperadas_por_epoca,
                                AoFechar callback, void *contexto) {
  iniciado_ = true;
  ancora_ms_ = mono_ms;
  esperadas_ = amostras_esperadas_por_epoca;
  callback_ = callback;
  contexto_ = contexto;
  zerar_corrente(0);
}

uint32_t AcumuladorDeEpoca::slot_de(uint64_t mono_ms) const {
  if (mono_ms <= ancora_ms_) return 0;
  uint64_t decorrido = mono_ms - ancora_ms_;
  return static_cast<uint32_t>(decorrido / (static_cast<uint64_t>(DURACAO_EPOCA_BASE_S) * 1000u));
}

uint64_t AcumuladorDeEpoca::inicio_do_slot(uint32_t slot) const {
  return ancora_ms_ + static_cast<uint64_t>(slot) *
                          (static_cast<uint64_t>(DURACAO_EPOCA_BASE_S) * 1000u);
}

void AcumuladorDeEpoca::zerar_corrente(uint32_t slot) {
  corrente_ = Epoca();
  corrente_.indice = slot;
  corrente_.esperadas = esperadas_;
  corrente_.flags = EPOCA_VAZIA;  // ate a primeira amostra chegar, e lacuna
  slot_corrente_ = slot;
  corrente_tem_amostra_ = false;
}

void AcumuladorDeEpoca::amostrar(uint64_t mono_ms, float ax, float ay, float az,
                                 float total, float temp) {
  if (!iniciado_) return;

  // Fecha o que ja venceu ANTES de arquivar. Sem isto, a amostra da virada de
  // epoca era recusada como "de outro slot" e sumia.
  fechar_ate(mono_ms);

  uint32_t slot = slot_de(mono_ms);
  // Amostra de um slot ja fechado chega atrasada: descartar seria a resposta
  // errada (o dado existe), mas atribui-la ao slot corrente seria PIOR --
  // moveria um evento no tempo, que e exatamente a distorcao que este modulo
  // existe para evitar. Ela entra no slot corrente so se for o dela.
  if (slot != slot_corrente_) return;

  if (!corrente_tem_amostra_ || total > corrente_.pico_total) {
    corrente_.pico_total = total;
    corrente_.pico_ax = ax;
    corrente_.pico_ay = ay;
    corrente_.pico_az = az;
    corrente_.temp_pico = temp;
  }
  corrente_tem_amostra_ = true;
  corrente_.flags = static_cast<uint8_t>(corrente_.flags & ~EPOCA_VAZIA);
  if (corrente_.amostras < 0xFFFFu) corrente_.amostras++;
}

void AcumuladorDeEpoca::amostrar_invalida(uint64_t mono_ms) {
  if (!iniciado_) return;
  fechar_ate(mono_ms);
  if (slot_de(mono_ms) != slot_corrente_) return;
  corrente_.flags = static_cast<uint8_t>(corrente_.flags | EPOCA_COM_AMOSTRA_INVALIDA);
  // Nao incrementa `amostras`: a tentativa aconteceu, a medida nao. A
  // diferenca para `esperadas` e o que registra a perda.
}

void AcumuladorDeEpoca::fechar_ate(uint64_t mono_ms) {
  if (!iniciado_) return;

  uint32_t slot_agora = slot_de(mono_ms);
  while (slot_corrente_ < slot_agora) {
    // Marca incompleta a epoca que recebeu menos amostras do que a cadencia
    // prometia. Este e o ponto do modulo inteiro: a perda de cadencia vira
    // um CAMPO no dado. Sem isso, uma noite com a metade das amostras sairia
    // indistinguivel de uma noite perfeita -- e dado distorcido que parece
    // valido e pior que lacuna, porque a lacuna a analise ve.
    if (corrente_.amostras < corrente_.esperadas) {
      corrente_.flags = static_cast<uint8_t>(corrente_.flags | EPOCA_INCOMPLETA);
    }
    if (callback_) callback_(corrente_, contexto_);
    zerar_corrente(slot_corrente_ + 1);
  }
}

}  // namespace dormio
