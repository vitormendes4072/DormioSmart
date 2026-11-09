// coletor_celular.cpp -- ver coletor_celular.h.

#include "coletor_celular.h"

#include <math.h>

#include "epoca_c2.h"
#include "reamostragem.h"

namespace dormio {

int16_t g_para_lsb(float g) {
  const float lsb = g * LSB_POR_G;
  if (!(lsb == lsb)) return 0;  // NaN: o sensor nao mediu; zero e o menos inventado
  if (lsb >= 32767.0f) return 32767;
  if (lsb <= -32768.0f) return -32768;
  return static_cast<int16_t>(lroundf(lsb));
}

ColetorCelular::ColetorCelular()
    : origem_us_(0),
      iniciado_(false),
      n_pendentes_(0),
      t_primeira_pendente_us_(0),
      t_ultima_us_(0),
      t_ultima_drenagem_us_(0),
      tem_amostra_(false),
      temperatura_c_(25.0f),
      recebidas_(0),
      fora_de_ordem_(0),
      com_payload_(0),
      recusadas_(0),
      recusadas_taxa_(0),
      sem_features_(0),
      sem_payload_(0),
      ultima_taxa_hz_(0.0),
      ultima_teve_features_(false) {}

void ColetorCelular::iniciar(uint64_t origem_us, const ResolucaoDeParede &parede) {
  cadeia_.iniciar(origem_us);
  parede_ = parede;
  origem_us_ = origem_us;
  iniciado_ = true;
  n_pendentes_ = 0;
  tem_amostra_ = false;
  t_ultima_drenagem_us_ = origem_us;
  recebidas_ = 0;
  fora_de_ordem_ = 0;
  com_payload_ = 0;
  recusadas_ = 0;
  recusadas_taxa_ = 0;
  sem_features_ = 0;
  sem_payload_ = 0;
  ultima_taxa_hz_ = 0.0;
}

void ColetorCelular::drenar() {
  if (n_pendentes_ == 0) return;
  // Meio passo depois da ultima amostra: a drenagem que deixa a contagem em C
  // acontece, em media, meio periodo depois da amostra C-1 (`cadeia_c2.h`).
  // Com uma amostra so nao ha periodo medido; usa o nominal.
  uint64_t meio_passo_us = static_cast<uint64_t>(0.5e6 / TAXA_NOMINAL_C2_HZ);
  if (n_pendentes_ >= 2) {
    meio_passo_us = (t_ultima_us_ - t_primeira_pendente_us_) / (2u * (n_pendentes_ - 1u));
  }
  const uint64_t t_us = t_ultima_us_ + meio_passo_us;
  cadeia_.registrar_drenagem(t_us, pendentes_, n_pendentes_, false);
  t_ultima_drenagem_us_ = t_us;
  n_pendentes_ = 0;
}

void ColetorCelular::amostrar(uint64_t t_us, float ax_ms2, float ay_ms2, float az_ms2) {
  if (!iniciado_) return;
  if (tem_amostra_ && t_us <= t_ultima_us_) {
    fora_de_ordem_++;
    return;
  }
  // A primeira amostra pode vir antes da origem (a grade comeca na proxima
  // fronteira de 30 s); o intervalo de drenagem conta a partir dela.
  if (!tem_amostra_) t_ultima_drenagem_us_ = t_us;
  // A drenagem fecha ANTES de a amostra nova entrar: depois de um buraco (o
  // sistema parou o sensor por minutos), as amostras de antes do buraco nao
  // podem ser carimbadas com o instante de depois dele.
  if (n_pendentes_ > 0 &&
      (t_us - t_ultima_drenagem_us_ >= INTERVALO_DE_DRENAGEM_US ||
       n_pendentes_ >= CAPACIDADE_DA_DRENAGEM)) {
    drenar();
  }
  AmostraBruta &a = pendentes_[n_pendentes_];
  a.x = g_para_lsb(ax_ms2 / G_PADRAO_MS2);
  a.y = g_para_lsb(ay_ms2 / G_PADRAO_MS2);
  a.z = g_para_lsb(az_ms2 / G_PADRAO_MS2);
  if (n_pendentes_ == 0) t_primeira_pendente_us_ = t_us;
  n_pendentes_++;
  t_ultima_us_ = t_us;
  tem_amostra_ = true;
  recebidas_++;
}

ResultadoDoColetor ColetorCelular::proximo(char *destino, uint32_t tamanho, uint32_t *escritos) {
  if (escritos) *escritos = 0;
  if (!iniciado_) return COLETOR_NADA;

  EpocaReamostrada info;
  const ResultadoDaEpoca r = cadeia_.proxima_epoca(&info, grade_x_, grade_y_, grade_z_);
  if (r == EPOCA_AINDA_NAO) return COLETOR_NADA;
  if (r != EPOCA_PRONTA) {
    recusadas_++;
    if (r == EPOCA_RECUSADA_TAXA) recusadas_taxa_++;
    return COLETOR_EPOCA_RECUSADA;
  }
  ultima_taxa_hz_ = 1.0 / info.linha.b_s;

  // O mesmo caminho da placa: features da grade, e o vetor pela ida e volta
  // da quantizacao que a fila de flash faz (`montar_payload_do_registro`).
  acumulador_.iniciar();
  for (uint32_t i = 0; i < AMOSTRAS_NA_GRADE; i++) {
    acumulador_.amostrar(grade_x_[i], grade_y_[i], grade_z_[i]);
  }
  FeaturesDeEpoca f;
  const bool tem_features = acumulador_.fechar(TAXA_DA_GRADE_HZ, &f);
  ultimas_features_ = f;
  ultima_teve_features_ = tem_features;
  FeaturesDeEpoca f_enviada;
  if (tem_features) {
    f_enviada = desquantizar(quantizar(f), static_cast<uint16_t>(AMOSTRAS_NA_GRADE));
  }

  const Epoca e = epoca_da_grade(info.indice, grade_x_, grade_y_, grade_z_, AMOSTRAS_NA_GRADE,
                                 temperatura_c_);
  bool incluidas = false;
  const ResultadoDeMontagem m = montar_payload(
      e, parede_, inicio_da_epoca_c2_ms(origem_us_, info.indice), destino, tamanho, escritos,
      tem_features ? &f_enviada : 0, TAXA_DA_GRADE_HZ, &incluidas);
  if (m != PAYLOAD_OK) {
    sem_payload_++;
    return COLETOR_SEM_PAYLOAD;
  }
  com_payload_++;
  if (!incluidas) sem_features_++;
  return COLETOR_PAYLOAD;
}

}  // namespace dormio
