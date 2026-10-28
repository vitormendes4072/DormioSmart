#include "caracteristicas.h"

#include <math.h>

#include "filtro.h"

namespace dormio {

// O mesmo guarda-corpo que `epoca.cpp` tem para `Epoca`, e pelo mesmo motivo:
// `capacidade.cpp` mede a autonomia com `sizeof`, no host, e o numero so vale
// para a placa se o layout for o mesmo. Campo novo aqui quebra o build ANTES
// de a medicao passar a mentir.
static_assert(sizeof(VetorDeFeatures) == TAMANHO_DO_VETOR_DE_FEATURES_BYTES,
              "VetorDeFeatures mudou de tamanho: refaca a medicao de capacidade");

// ── Quantizacao ───────────────────────────────────────────────────────

// Arredonda e satura em [0, 65535]. A saturacao e o comportamento certo para
// uma feature fora da faixa: o contrato declara a faixa fisica, e um valor
// acima dela ou e defeito de sensor ou e erro de unidade -- em nenhum dos dois
// casos dar a volta no inteiro ajuda (um `enmo_max` de 17 g virando 0,02 g
// seria a leitura mais tranquilizadora possivel do pior dado possivel).
static uint16_t para_u16(double valor, double fundo_de_escala) {
  if (!(valor > 0.0)) return 0;  // pega NaN tambem: NaN falha toda comparacao
  const double escalado = valor / fundo_de_escala * 65535.0;
  if (escalado >= 65535.0) return 65535u;
  return static_cast<uint16_t>(escalado + 0.5);
}

// Componente de `g` em [-1, 1] para int16.
//
// Fundo de escala 32767 (e nao 32768) de proposito: assim +1,0 e -1,0 sao
// ambos representaveis e a escala e SIMETRICA. Com 32768 o lado positivo
// saturaria antes do negativo, e `g` e uma direcao -- uma assimetria de escala
// viraria um vies direcional, que e exatamente o que `inclinacao_rel` mede.
static int16_t para_i16_unitario(double valor) {
  if (!(valor == valor)) return 0;  // NaN
  double escalado = valor * 32767.0;
  if (escalado >= 32767.0) return 32767;
  if (escalado <= -32767.0) return -32767;
  return static_cast<int16_t>(escalado >= 0.0 ? escalado + 0.5 : escalado - 0.5);
}

VetorDeFeatures quantizar(const FeaturesDeEpoca &f) {
  VetorDeFeatures v;
  v.enmo_media = para_u16(f.enmo_media, FUNDO_ESCALA_ENMO_MEDIA);
  v.enmo_desvio = para_u16(f.enmo_desvio, FUNDO_ESCALA_ENMO_DESVIO);
  v.enmo_max = para_u16(f.enmo_max, FUNDO_ESCALA_ENMO_MAX);
  v.mag_din_media = para_u16(f.mag_din_media, FUNDO_ESCALA_MAG_DIN);
  // Contagens: copia, nao quantizacao. Em uint16 uma contagem de 0 a 959 e
  // exata, e e por isso que o contrato manda guardar a contagem em vez da
  // fracao -- guardar `zcr` como u16 perderia precisao de graca.
  v.cruzamentos = f.cruzamentos;
  v.amostras_acima = f.amostras_acima;
  v.gx = para_i16_unitario(f.gx);
  v.gy = para_i16_unitario(f.gy);
  v.gz = para_i16_unitario(f.gz);
  return v;
}

FeaturesDeEpoca desquantizar(const VetorDeFeatures &v, uint16_t amostras) {
  FeaturesDeEpoca f;
  f.enmo_media = static_cast<double>(v.enmo_media) / 65535.0 * FUNDO_ESCALA_ENMO_MEDIA;
  f.enmo_desvio = static_cast<double>(v.enmo_desvio) / 65535.0 * FUNDO_ESCALA_ENMO_DESVIO;
  f.enmo_max = static_cast<double>(v.enmo_max) / 65535.0 * FUNDO_ESCALA_ENMO_MAX;
  f.mag_din_media = static_cast<double>(v.mag_din_media) / 65535.0 * FUNDO_ESCALA_MAG_DIN;
  f.cruzamentos = v.cruzamentos;
  f.amostras_acima = v.amostras_acima;
  f.amostras = amostras;
  // Os denominadores das duas fracoes sao diferentes, e isso nao e descuido:
  // `zcr` conta TRANSICOES entre amostras vizinhas, e em n amostras existem
  // n-1 pares; `p_frac` conta AMOSTRAS acima do limiar, e existem n. Dividir
  // as duas por n daria um `zcr` sistematicamente 0,1 % menor numa epoca de
  // 960 -- pequeno, constante, e portanto exatamente o tipo de vies que
  // nenhuma faixa do contrato pegaria.
  f.zcr = amostras > 1 ? static_cast<double>(v.cruzamentos) /
                             static_cast<double>(amostras - 1u)
                       : 0.0;
  f.p_frac = amostras > 0 ? static_cast<double>(v.amostras_acima) /
                                static_cast<double>(amostras)
                          : 0.0;
  f.gx = static_cast<double>(v.gx) / 32767.0;
  f.gy = static_cast<double>(v.gy) / 32767.0;
  f.gz = static_cast<double>(v.gz) / 32767.0;
  return f;
}

// ── Acumulador ────────────────────────────────────────────────────────

AcumuladorDeFeatures::AcumuladorDeFeatures() : n_(0), descartadas_(0) {}

void AcumuladorDeFeatures::iniciar() {
  n_ = 0;
  descartadas_ = 0;
  // A janela NAO e zerada aqui. Zerar 19 KB a cada 30 s seria trabalho para
  // nada: `fechar()` so le as `n_` primeiras posicoes, e `n_` e o que
  // `iniciar` zera. Resto de epoca anterior em posicao nao lida e inerte.
}

void AcumuladorDeFeatures::amostrar(float ax, float ay, float az) {
  if (n_ >= AMOSTRAS_MAXIMAS_POR_EPOCA) {
    descartadas_++;
    return;
  }
  bruto_[0][n_] = ax;
  bruto_[1][n_] = ay;
  bruto_[2][n_] = az;
  n_++;
}

bool AcumuladorDeFeatures::fechar(float fs, FeaturesDeEpoca *saida) {
  if (saida == 0) return false;

  // A recusa que implementa a decisao do contrato. Nao e uma guarda contra
  // divisao por zero -- e a declaracao de que abaixo daqui as duas
  // implementacoes nao calculam a mesma coisa, medida em
  // `test_epoca_incompleta_nao_tem_paridade`. Emitir um vetor aqui produziria
  // seis numeros dentro de todas as faixas da secao 2.6 e errados em ate 54 %.
  if (n_ < AMOSTRAS_MINIMAS_PARA_PARIDADE) return false;
  if (!filtro_aplicavel(fs, CORTE_GRAVIDADE_HZ)) return false;

  const uint32_t n = n_;
  const double dn = static_cast<double>(n);

  // ── Fase 1: ENMO e as magnitudes ────────────────────────────────────
  //
  // Nao passa pelo filtro, e por isso a tolerancia de paridade destas tres e
  // 1e-7 g absoluto (1 ULP de float32 em 1 g) e nao percentual: o ENMO faz
  // `||a|| - 1` com `||a|| ~ 1`, que e CANCELAMENTO CATASTROFICO -- quem
  // limita a precisao e a resolucao do float em 1 g, nao a do resultado.
  //
  // As magnitudes vao para `gravidade_`, que nesta fase ainda nao e
  // gravidade. O reaproveitamento esta declarado no cabecalho; o `zcr` precisa
  // de todas as magnitudes depois de conhecer a media delas, entao elas tem de
  // existir em algum vetor.
  double soma_enmo = 0.0;
  double soma_enmo2 = 0.0;
  double maximo_enmo = 0.0;
  double soma_mags = 0.0;

  for (uint32_t i = 0; i < n; i++) {
    const double x = static_cast<double>(bruto_[0][i]);
    const double y = static_cast<double>(bruto_[1][i]);
    const double z = static_cast<double>(bruto_[2][i]);
    const double mag = sqrt(x * x + y * y + z * z);
    gravidade_[i] = static_cast<float>(mag);
    soma_mags += mag;

    // O RETIFICADOR do ENMO: max(||a|| - 1, 0).
    //
    // ⚠️ Ele NAO e simetrico, e isso tem consequencia fisica registrada: em
    // repouso o valor verdadeiro e zero, mas o ruido oscila para os dois lados
    // e so o lado negativo e cortado. O ruido portanto nao se cancela -- vira
    // um VIES POSITIVO. E a origem do piso de ~0,64 mg no MPU6050
    // (ML-DATASETS secao 2.2), que depois serve de teto para a tolerancia de
    // paridade deste modulo.
    double e = mag - 1.0;
    if (e < 0.0) e = 0.0;
    soma_enmo += e;
    soma_enmo2 += e * e;
    if (e > maximo_enmo) maximo_enmo = e;
  }

  const double media_enmo = soma_enmo / dn;
  // Variancia POPULACIONAL (divide por n), nao amostral (n-1). E o que o
  // `np.std` do numpy faz por padrao (`ddof=0`) e portanto o que o modelo foi
  // treinado em cima. A forma E[x^2] - E[x]^2 pode dar negativo por
  // arredondamento quando o desvio e ~0 (epoca parada), e e por isso que o
  // `sqrt` e guardado atras do teste -- `sqrt` de negativo e NaN, e NaN
  // atravessa o pipeline ate o treino, longe da causa.
  const double variancia = soma_enmo2 / dn - media_enmo * media_enmo;

  // `zcr`: cruzamentos da magnitude SEM DC.
  //
  // O escalar e a magnitude menos a media DA PROPRIA EPOCA -- um escalar
  // invariante a rotacao, que e o requisito que vale para as oito features.
  // Contar cruzamentos do sinal bruto daria a contagem da gravidade cruzando
  // zero, que e zero sempre.
  const double media_mags = soma_mags / dn;
  uint32_t cruzamentos = 0;
  for (uint32_t i = 1; i < n; i++) {
    const bool antes = (static_cast<double>(gravidade_[i - 1]) - media_mags) < 0.0;
    const bool agora = (static_cast<double>(gravidade_[i]) - media_mags) < 0.0;
    if (antes != agora) cruzamentos++;
  }

  // ── Fase 2: gravidade, dinamica, `mag_din_media`, `p_frac` e `g` ────
  for (uint32_t i = 0; i < n; i++) din2_[i] = 0.0f;

  double soma_g[3] = {0.0, 0.0, 0.0};
  for (uint32_t k = 0; k < 3; k++) {
    // Copia o eixo e filtra no lugar: `gravidade_` passa a ser a componente
    // de gravidade daquele eixo. O bruto fica intacto porque a dinamica e
    // (bruto - gravidade) e precisa dos dois.
    for (uint32_t i = 0; i < n; i++) gravidade_[i] = bruto_[k][i];
    if (!filtrar_ida_e_volta(gravidade_, n, fs, CORTE_GRAVIDADE_HZ)) return false;

    for (uint32_t i = 0; i < n; i++) {
      const double g = static_cast<double>(gravidade_[i]);
      soma_g[k] += g;
      const double d = static_cast<double>(bruto_[k][i]) - g;
      din2_[i] = static_cast<float>(static_cast<double>(din2_[i]) + d * d);
    }
  }

  double soma_mag_din = 0.0;
  uint32_t acima = 0;
  const double limiar = static_cast<double>(LIMIAR_P_FRAC_G);
  for (uint32_t i = 0; i < n; i++) {
    // Norma L2 da dinamica. E a escolha que torna `mag_din_media`
    // EXATAMENTE invariante a rotacao (||Rv|| = ||v|| para R ortogonal). A
    // versao anterior desta feature usava norma L1 -- a SMA classica da
    // actigrafia -- e variava ~6 % sob rotacao do referencial, o que fez o
    // teste de invariancia reprova-la. Ver DECISAO TECNICA 2 em
    // `ml/src/features.py`. Nao trocar de volta: num travesseiro a orientacao
    // e arbitraria, e uma feature que mede a montagem nao transfere.
    const double mag_din = sqrt(static_cast<double>(din2_[i]));
    soma_mag_din += mag_din;

    // ⚠️⚠️ O `>` E ESTRITO, E ISSO FOI COPIADO POR LEITURA DO CONTRATO.
    //
    // A secao 2.6 define `p_frac` como "fracao de amostras com ||a - g||
    // ACIMA do limiar", e `ml/src/features.py` usa `>`. Trocar por `>=`
    // **nao e detectavel por teste nenhum**: a diferenca so aparece se alguma
    // amostra cair EXATAMENTE no limiar, o que em ponto flutuante sobre sinal
    // continuo tem medida zero. O vetor dourado registra isso como ponto cego
    // declarado (`p_frac_limiar_inclusivo` em
    // `ml/testes/verificar_vetor_dourado_por_mutacao.py`), e a instrucao
    // escrita la e exatamente esta: "o lado C++ precisa copiar o `>` do
    // contrato por leitura, nao por teste".
    //
    // Entao: se este `>` virar `>=` algum dia, a suite continuara verde e o
    // dado de campo estara errado. Nao mexer sem mexer no contrato primeiro.
    if (mag_din > limiar) acima++;
  }

  // `g`: media da gravidade filtrada NA EPOCA, normalizada DEPOIS.
  //
  // ⚠️ A ORDEM IMPORTA, e inverte-la e uma sabotagem que o vetor dourado
  // testa de proposito (`ordem_normaliza_antes`). Normalizar cada amostra
  // antes de promediar produz a MEDIA DE DIRECOES; promediar e normalizar
  // depois produz a DIRECAO DA MEDIA. Sao estimadores diferentes, e o segundo
  // e o do pipeline.
  const double gmx = soma_g[0] / dn;
  const double gmy = soma_g[1] / dn;
  const double gmz = soma_g[2] / dn;
  double norma = sqrt(gmx * gmx + gmy * gmy + gmz * gmz);
  // Mesmo guarda-corpo de `unitario()` no Python: vetor ~nulo volta
  // inalterado em vez de virar NaN. Nao deveria acontecer com um
  // acelerometro vivo (a gravidade e ~1 g), mas um acelerometro MORTO devolve
  // os tres eixos zerados -- que e justamente o modo de falha de 25/08/2026
  // registrado na secao 5.1 do contrato.
  if (norma < 1e-12) norma = 1.0;

  FeaturesDeEpoca f;
  f.enmo_media = media_enmo;
  f.enmo_desvio = variancia > 0.0 ? sqrt(variancia) : 0.0;
  f.enmo_max = maximo_enmo;
  f.mag_din_media = soma_mag_din / dn;
  f.cruzamentos = static_cast<uint16_t>(cruzamentos > 0xFFFFu ? 0xFFFFu : cruzamentos);
  f.amostras_acima = static_cast<uint16_t>(acima > 0xFFFFu ? 0xFFFFu : acima);
  f.amostras = static_cast<uint16_t>(n > 0xFFFFu ? 0xFFFFu : n);
  f.zcr = static_cast<double>(cruzamentos) / (dn - 1.0);
  f.p_frac = static_cast<double>(acima) / dn;
  f.gx = gmx / norma;
  f.gy = gmy / norma;
  f.gz = gmz / norma;

  *saida = f;
  return true;
}

}  // namespace dormio
