#include "cadeia_c2.h"

#include <math.h>

#include "reamostragem.h"

namespace dormio {

uint32_t intervalo_de_drenagem_us(uint32_t *estado) {
  uint32_t x = (estado != 0 && *estado != 0) ? *estado : 0x9E3779B9u;
  x ^= x << 13;
  x ^= x >> 17;
  x ^= x << 5;
  if (estado != 0) *estado = x;
  return INTERVALO_DE_DRENAGEM_US + x % VARIACAO_DA_DRENAGEM_US;
}

bool ajustar_linha_do_tempo(const double *t_s, const double *acumulado, uint32_t n,
                            LinhaDoTempo *saida) {
  if (t_s == 0 || acumulado == 0 || saida == 0) return false;
  if (n < MINIMO_DE_DRENAGENS) return false;
  // Duas passagens: medias, depois somas centradas. Com `acumulado` na casa
  // das dezenas de milhares (uma noite a 50 Hz passa de 1,4 milhao), a forma
  // de uma passagem `Sxx - n*mx^2` cancela catastroficamente.
  double mx = 0.0, my = 0.0;
  for (uint32_t i = 0; i < n; i++) {
    mx += acumulado[i];
    my += t_s[i];
  }
  mx /= static_cast<double>(n);
  my /= static_cast<double>(n);
  double sxx = 0.0, sxy = 0.0;
  for (uint32_t i = 0; i < n; i++) {
    sxx += (acumulado[i] - mx) * (acumulado[i] - mx);
    sxy += (acumulado[i] - mx) * (t_s[i] - my);
  }
  if (!(sxx > 0.0)) return false;
  saida->b_s = sxy / sxx;
  saida->a_s = my - saida->b_s * mx;
  saida->n_drenagens = n;
  return true;
}

CadeiaC2::CadeiaC2()
    : total_amostras_(0), total_drenagens_(0), origem_us_(0), proxima_epoca_(0),
      iniciada_(false) {}

void CadeiaC2::iniciar(uint64_t origem_us) {
  total_amostras_ = 0;
  total_drenagens_ = 0;
  origem_us_ = origem_us;
  proxima_epoca_ = 0;
  iniciada_ = true;
}

double CadeiaC2::relativo_s(uint64_t t_us) const {
  // Pela diferenca inteira, e so depois para double: e o que o Python faz
  // (`(t_us - origem_us) / 1e6` com inteiros). Converter os dois para double
  // antes de subtrair perde os microssegundos depois de ~285 anos de uptime
  // -- irrelevante --, mas daria um arredondamento diferente do da referencia.
  const int64_t d = static_cast<int64_t>(t_us) - static_cast<int64_t>(origem_us_);
  return static_cast<double>(d) / 1e6;
}

uint32_t CadeiaC2::drenagens_guardadas() const {
  return total_drenagens_ < CAPACIDADE_DE_DRENAGENS ? total_drenagens_
                                                    : CAPACIDADE_DE_DRENAGENS;
}

const CadeiaC2::RegistroDeDrenagem &CadeiaC2::drenagem(uint32_t i) const {
  const uint32_t primeira = total_drenagens_ - drenagens_guardadas();
  return drenagens_[(primeira + i) % CAPACIDADE_DE_DRENAGENS];
}

void CadeiaC2::registrar_drenagem(uint64_t t_us, const AmostraBruta *amostras, uint16_t n,
                                  bool transbordou) {
  if (!iniciada_) return;
  if (!transbordou && amostras != 0) {
    for (uint16_t i = 0; i < n; i++) {
      anel_[(total_amostras_ + i) % CAPACIDADE_DE_AMOSTRAS] = amostras[i];
    }
    total_amostras_ += n;
  }
  RegistroDeDrenagem &r = drenagens_[total_drenagens_ % CAPACIDADE_DE_DRENAGENS];
  r.t_us = t_us;
  r.acumulado = total_amostras_;
  r.transbordou = transbordou;
  total_drenagens_++;
}

ResultadoDaEpoca CadeiaC2::proxima_epoca(EpocaReamostrada *info, float *gx, float *gy,
                                         float *gz) {
  if (!iniciada_ || total_drenagens_ == 0) return EPOCA_AINDA_NAO;

  const double e0 = static_cast<double>(proxima_epoca_) * DURACAO_EPOCA_C2_S;
  const double jan_ini = e0 - MARGEM_S;
  const double jan_fim = e0 + DURACAO_EPOCA_C2_S + MARGEM_S;
  const double sel_ini = jan_ini - FOLGA_DO_AJUSTE_S;
  const double sel_fim = jan_fim + FOLGA_DO_AJUSTE_S;

  const uint32_t guardadas = drenagens_guardadas();
  if (!(relativo_s(drenagem(guardadas - 1).t_us) > sel_fim)) return EPOCA_AINDA_NAO;

  EpocaReamostrada local;
  EpocaReamostrada &e = (info != 0) ? *info : local;
  e.indice = proxima_epoca_;
  e.linha.a_s = 0.0;
  e.linha.b_s = 0.0;
  e.linha.n_drenagens = 0;
  e.k_ini = 0;
  e.k_fim = 0;
  proxima_epoca_++;  // daqui em diante a epoca e consumida, pronta ou recusada

  // Historico que ja saiu do anel de drenagens e caia na selecao: o ajuste
  // teria menos pontos do que a referencia, e nao ha como saber quantos.
  if (total_drenagens_ > CAPACIDADE_DE_DRENAGENS && relativo_s(drenagem(0).t_us) >= sel_ini) {
    e.resultado = EPOCA_RECUSADA_SEM_AMOSTRAS;
    return e.resultado;
  }

  double ts[CAPACIDADE_DE_DRENAGENS];
  double xs[CAPACIDADE_DE_DRENAGENS];
  uint32_t n = 0;
  for (uint32_t i = 0; i < guardadas; i++) {
    const RegistroDeDrenagem &r = drenagem(i);
    const double t = relativo_s(r.t_us);
    if (t < sel_ini || t > sel_fim) continue;
    if (r.transbordou) {
      e.resultado = EPOCA_RECUSADA_TRANSBORDO;
      return e.resultado;
    }
    ts[n] = t;
    xs[n] = static_cast<double>(r.acumulado);
    n++;
  }
  if (!ajustar_linha_do_tempo(ts, xs, n, &e.linha)) {
    e.linha.n_drenagens = n;
    e.resultado = EPOCA_RECUSADA_POUCAS_DRENAGENS;
    return e.resultado;
  }

  const double a = e.linha.a_s;
  const double b = e.linha.b_s;
  const double fs = 1.0 / b;
  const double nominal = static_cast<double>(TAXA_NOMINAL_C2_HZ);
  if (!(fs >= TAXA_MINIMA_FRAC * nominal && fs <= TAXA_MAXIMA_FRAC * nominal)) {
    e.resultado = EPOCA_RECUSADA_TAXA;
    return e.resultado;
  }

  const int64_t k_ini = static_cast<int64_t>(floor((jan_ini - a) / b - 0.5));
  const int64_t k_fim = static_cast<int64_t>(ceil((jan_fim - a) / b - 0.5));
  e.k_ini = k_ini;
  e.k_fim = k_fim;
  const int64_t total = static_cast<int64_t>(total_amostras_);
  const int64_t mais_antiga = total - static_cast<int64_t>(
      total_amostras_ < CAPACIDADE_DE_AMOSTRAS ? total_amostras_ : CAPACIDADE_DE_AMOSTRAS);
  if (k_ini < 0 || k_ini < mais_antiga || k_fim + 1 > total ||
      k_fim - k_ini + 1 > static_cast<int64_t>(CAPACIDADE_DE_AMOSTRAS)) {
    e.resultado = EPOCA_RECUSADA_SEM_AMOSTRAS;
    return e.resultado;
  }

  const uint32_t n_janela = static_cast<uint32_t>(k_fim - k_ini + 1);
  const double x0 = (e0 - a) / b - 0.5 - static_cast<double>(k_ini);
  const double dx = (1.0 / static_cast<double>(TAXA_DA_GRADE_HZ)) / b;
  float *saidas[3] = {gx, gy, gz};
  for (int eixo = 0; eixo < 3; eixo++) {
    for (uint32_t i = 0; i < n_janela; i++) {
      const AmostraBruta &s =
          anel_[static_cast<uint64_t>(k_ini + static_cast<int64_t>(i)) % CAPACIDADE_DE_AMOSTRAS];
      const int16_t v = (eixo == 0) ? s.x : (eixo == 1) ? s.y : s.z;
      trabalho_[i] = lsb_para_g(v);
    }
    filtrar_antialiasing(trabalho_, n_janela, static_cast<float>(fs));
    if (saidas[eixo] != 0) {
      interpolar_linear(trabalho_, n_janela, x0, dx, saidas[eixo], AMOSTRAS_NA_GRADE);
    }
  }
  e.resultado = EPOCA_PRONTA;
  return e.resultado;
}

}  // namespace dormio
