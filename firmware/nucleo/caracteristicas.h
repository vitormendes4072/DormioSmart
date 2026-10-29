// caracteristicas.h -- as SEIS caracteristicas intra-epoca e o vetor `g`.
//
// ⚠️ O ARQUIVO NAO SE CHAMA `features.h`, E O MOTIVO NAO E ESTILO.
//
// Ele se chamou, por quinze minutos, e NADA COMPILAVA -- nem este modulo, nem
// `filtro.cpp`, que nem o inclui. A glibc tem um `<features.h>` proprio, e
// praticamente todo cabecalho de sistema o inclui para descobrir quais
// extensoes estao habilitadas (`__GLIBC_USE`, `__GNUC_PREREQ`). Com o `-I.`
// do Makefile, a busca por `features.h` achava ESTE arquivo primeiro, e a
// `stdint.h` passava a ser compilada sem as macros que ela espera. O erro que
// saia era `missing binary operator before token "("` dentro de
// `/usr/include/`, apontando para codigo da biblioteca padrao -- ou seja, o
// diagnostico apontava para todo lugar menos para a causa.
//
// Vale o registro porque o modo de falha e desproporcional: um nome de arquivo
// plausivel, escolhido sem pensar, derruba a compilacao inteira com uma
// mensagem que nao menciona o arquivo culpado. O resto do nucleo ja usava
// nomes em portugues (`epoca`, `cadencia`, `relogio`, `payload`), e seguir o
// padrao da casa teria evitado o problema de graca.
//
// Contrato: `docs/DATA-CONTRACT.md` secao 2.6 (v2.5.1).
// Referencia executavel: `features_estilo_firmware` em
// `ml/testes/test_vetor_dourado.py`. Este arquivo copia aquela funcao linha
// por linha; onde ele divergir dela, ele esta errado, e nao o contrario.
//
// ╔══════════════════════════════════════════════════════════════════════╗
// ║ POR QUE ISTO NAO ESTA DENTRO DE `Epoca`                              ║
// ╚══════════════════════════════════════════════════════════════════════╝
//
// A leitura obvia do estudo do buffer (`docs/DECISAO-BUFFER-E-FEATURES.md`,
// "O registro: 40 bytes") seria acrescentar os 18 B de features ao `Epoca` e
// pronto. Nao foi feito, por um motivo que nao e de bytes:
//
//     **O `Epoca` e o registro que o buffer FUNDE quando degrada resolucao, e
//     as features NAO FUNDEM.**
//
// A degradacao de `epoca.h` e exata porque o metodo de agregacao e o pico, e
// o maximo e associativo: o pico de duas epocas de 30 s E o pico da epoca de
// 60 s que as cobre, nao uma estimativa. Das sete quantidades deste modulo,
// isso vale para TRES e falha para QUATRO:
//
//   funde exato  `enmo_max` ........ maximo, associativo.
//   funde exato  `p_frac` .......... e uma contagem contra um limiar FIXO
//                                    (0,1224 g); somar as contagens e somar
//                                    as amostras da o valor exato da janela
//                                    dobrada.
//   funde exato  `enmo_media` ...... media ponderada por contagem.
//   funde exato  `enmo_desvio` ..... reconstruivel de (media, desvio) por
//                                    E[x^2] = s^2 + m^2, ponderado.
//   NAO funde    `mag_din_media` ... depende do filtro. `filtfilt` sobre 60 s
//                                    NAO e a concatenacao de dois `filtfilt`
//                                    de 30 s -- a janela de suporte do filtro
//                                    muda, e a borda no meio desaparece.
//   NAO funde    `zcr` ............. os cruzamentos sao contados contra a
//                                    MEDIA DA PROPRIA JANELA. Na janela
//                                    dobrada a media e outra, entao os
//                                    cruzamentos sao outros -- e nao ha como
//                                    recupera-los de duas contagens.
//   NAO funde    `g` ............... media da gravidade FILTRADA, normalizada
//                                    depois. Guardamos so a direcao unitaria
//                                    quantizada: a magnitude, que seria o
//                                    peso da media ponderada, foi descartada.
//                                    Media de duas direcoes unitarias e um
//                                    estimador diferente da direcao da media.
//
// Embutir as features no registro que o buffer funde criaria, portanto, tres
// numeros que a degradacao corromperia **em silencio**, dentro de todas as
// faixas do contrato -- a divergencia silenciosa que o `DATA-07` inteiro
// existe para evitar. E `g` e o pior dos tres, porque e o unico insumo das
// duas features que o servidor deriva: um `g` fundido errado nao aparece em
// nenhuma das seis features transmitidas e corrompe `inclinacao_rel` e
// `d_angulo`.
//
// Entao a decisao registrada e: **as features sao uma unidade separada, de
// vida mais curta que a epoca.** Elas valem para a epoca de nivel 0 em que
// foram medidas. Quem armazenar, drenar e eventualmente DESCARTAR features de
// epocas degradadas e o item de armazenamento -- e descartar e a resposta
// certa ali, porque epoca degradada ja nao e a epoca de 30 s que o pipeline
// de ML consome.
//
// ⚠️ CONSEQUENCIA ORCAMENTARIA, declarada em vez de escondida: o pareamento
// `Epoca` (32 B, picos em float) + `VetorDeFeatures` (18 B) da 50 B, contra os
// 40 B do layout D do estudo. Os 12 B de diferenca sao os 5 floats de pico que
// o layout D quantiza e este codigo nao toca. O recalculo da autonomia esta em
// `capacidade.cpp`, que agora mede os dois pareamentos, e o custo esta no
// diario (entrada do `DATA-07b`). Quantizar os picos e uma mudanca
// independente desta, com efeito proprio sobre a precisao TRANSMITIDA
// (`ax/ay/az/total` do payload) e sobre a checagem de coerencia da secao 5.1
// do contrato -- juntar as duas num item so tornaria impossivel dizer qual
// delas quebrou o que.

#ifndef DORMIO_NUCLEO_CARACTERISTICAS_H
#define DORMIO_NUCLEO_CARACTERISTICAS_H

#include <stdint.h>

namespace dormio {

// ── Constantes que SAO do contrato ────────────────────────────────────
//
// Nenhuma delas e escolhida aqui. Cada uma e a copia de um numero que vive em
// `ml/src/features.py` ou na secao 2.6 do contrato, e mudar uma delas de um
// lado so quebra a paridade.

// Limiar de `p_frac`, em g, sobre a magnitude dinamica ||a - g||.
//
// 1,2 / 9,80665 = 0,12236... -- e o limiar de movimento que o Dormio ja usa
// (`DATA-02`), convertido de m/s^2 para g.
//
// ⚠️ A DIVISAO ESTA ESCRITA, e nao o resultado. Se estivesse escrito
// `0.1223664f`, o ultimo digito seria uma terceira definicao do mesmo limiar
// (uma no Python, uma no contrato, uma aqui) e `p_frac` e uma contagem contra
// limiar RIGIDO: uma amostra perto da fronteira muda a contagem em 1. Com a
// divisao escrita, os dois lados calculam o mesmo quociente.
//
// ⚠️ Provisorio, como no Python: nasceu de medicao por contato de jumper,
// antes da solda e do `FW-06`. Recalibrar com `CAL-01`/`CAL-02`.
const float LIMIAR_P_FRAC_G = 1.2f / 9.80665f;

// Quantas amostras cabem na janela de uma epoca.
//
// 960 = 30 s x 32 Hz, que e a grade comum do pipeline de ML (`DATA-02`).
//
// ⚠️ ESTE NUMERO NAO E A CADENCIA DE HOJE. O `envio-continuo.ino` amostra a
// cada 10 s (`INTERVALO_AMOSTRA_MS = 10000`), ou seja TRES amostras por
// epoca. Com tres amostras nao existe feature nenhuma: o contrato (secao 2.6,
// "Epoca incompleta nao tem paridade") mede 54 % de divergencia em 8
// amostras, porque abaixo de 9 o Python nem filtra -- devolve a media. Ate o
// `FW-06` fixar a taxa, este modulo e codigo correto que o dispositivo nao
// tem insumo para alimentar, e `fechar()` RECUSA a epoca em vez de emitir um
// vetor plausivel e errado.
const uint32_t AMOSTRAS_POR_EPOCA_NOMINAL = 960;

// Teto da janela estatica. Igual ao nominal: dimensionar para mais seria
// reservar RAM para uma taxa que ninguem decidiu.
const uint32_t AMOSTRAS_MAXIMAS_POR_EPOCA = AMOSTRAS_POR_EPOCA_NOMINAL;

// Minimo de amostras para a paridade ser DECLARADA.
//
// Nao e "o minimo para a conta nao estourar": e o minimo medido em que as duas
// implementacoes calculam a mesma coisa. Abaixo da epoca completa a
// divergencia de `mag_din_media` vai de 0,26 % (960) a 3,0 % (64) a 54 % (8) —
// `test_epoca_incompleta_nao_tem_paridade`. O contrato ja decidiu a
// consequencia: o dispositivo nao emite `f` de epoca truncada.
const uint32_t AMOSTRAS_MINIMAS_PARA_PARIDADE = AMOSTRAS_POR_EPOCA_NOMINAL;

// ── Fundos de escala do ponto fixo de 16 bits ─────────────────────────
//
// Sao as faixas fisicas da tabela da secao 2.6 do contrato. O fundo de escala
// DEFINE o passo de quantizacao, entao estes numeros nao sao livres.
const float FUNDO_ESCALA_ENMO_MEDIA = 1.0f;    // g,  faixa 0 a 1
const float FUNDO_ESCALA_ENMO_DESVIO = 1.0f;   // g,  faixa 0 a 1
const float FUNDO_ESCALA_ENMO_MAX = 16.0f;     // g,  faixa 0 a 16
const float FUNDO_ESCALA_MAG_DIN = 2.0f;       // g,  faixa 0 a 2

// ── O vetor, em ponto flutuante: o que a PARIDADE compara ─────────────
//
// Esta e a saida do calculo, antes de qualquer quantizacao. E contra ESTA
// struct que o vetor dourado e conferido, e a razao esta na nota de
// `quantizar()` abaixo -- em resumo, o passo do u16 e 150x mais grosso que a
// tolerancia do ENMO, entao conferir o valor quantizado contra a regua de
// paridade reprovaria um firmware correto.
struct FeaturesDeEpoca {
  // Na ordem canonica de `NOMES_FEATURES` (contrato secao 2.6). Trocar a
  // ordem e mudanca MAJOR do contrato: um vetor na ordem errada passa em toda
  // validacao de faixa e produz um modelo errado em silencio.
  double enmo_media;     // 0  g
  double enmo_desvio;    // 1  g
  double enmo_max;       // 2  g
  double mag_din_media;  // 3  g
  double zcr;            // 4  adimensional, 0 a 1
  double p_frac;         // 5  adimensional, 0 a 1

  // `g`, unitario. NAO e feature: e o insumo do qual o SERVIDOR deriva
  // `inclinacao_rel` e `d_angulo` sobre a noite inteira (o dispositivo nao
  // pode derivar: `g_ref` e a mediana geometrica de todas as epocas, e quando
  // ele envia a epoca 12 as epocas 13..960 ainda nao existem).
  double gx, gy, gz;

  // As contagens inteiras de que `zcr` e `p_frac` sao fracoes. O contrato
  // (secao 2.6, "Representacao") manda guardar a CONTAGEM, nao a fracao: em
  // uint16 isso e representacao exata, nao quantizacao.
  uint16_t cruzamentos;      // numerador de zcr; denominador e (amostras - 1)
  uint16_t amostras_acima;   // numerador de p_frac; denominador e amostras
  uint16_t amostras;         // quantas amostras entraram na janela

  FeaturesDeEpoca()
      : enmo_media(0), enmo_desvio(0), enmo_max(0), mag_din_media(0), zcr(0),
        p_frac(0), gx(0), gy(0), gz(1), cruzamentos(0), amostras_acima(0),
        amostras(0) {}
};

// ── O vetor, empacotado: o que o ARMAZENAMENTO guarda ─────────────────
//
// 18 bytes. Larguras fixas e ordem decrescente de alinhamento, pelo mesmo
// motivo de `Epoca`: a medicao de capacidade roda no host (x86-64) e so vale
// para o alvo (xtensa 32 bits) se o layout for o mesmo nos dois.
struct VetorDeFeatures {
  uint16_t enmo_media;     // ponto fixo, fundo de escala 1 g
  uint16_t enmo_desvio;    // ponto fixo, fundo de escala 1 g
  uint16_t enmo_max;       // ponto fixo, fundo de escala 16 g
  uint16_t mag_din_media;  // ponto fixo, fundo de escala 2 g
  uint16_t cruzamentos;    // CONTAGEM exata -- zcr = cruzamentos/(amostras-1)
  uint16_t amostras_acima; // CONTAGEM exata -- p_frac = acima/amostras
  int16_t gx, gy, gz;      // ponto fixo, fundo de escala 1 (unitario)

  VetorDeFeatures()
      : enmo_media(0), enmo_desvio(0), enmo_max(0), mag_din_media(0),
        cruzamentos(0), amostras_acima(0), gx(0), gy(0), gz(32767) {}
};

// Travado no .cpp, como o de `Epoca`. Se alguem acrescentar um campo, o build
// quebra ANTES de a medicao de autonomia passar a mentir.
const uint32_t TAMANHO_DO_VETOR_DE_FEATURES_BYTES = 18;

// Quantiza para o ponto fixo de 16 bits do armazenamento.
//
// ⚠️⚠️ ISTO NAO E UMA OPERACAO NEUTRA, E O NUMERO IMPORTA.
//
// `enmo_media` tem fundo de escala 1 g e 16 bits: passo = 1/65535 = 1,526e-5 g,
// meio passo = 7,6e-6 g. A tolerancia de paridade do ENMO e **1e-7 g**. Ou
// seja: **a quantizacao e 76x mais grossa que a regua de paridade.** Conferir
// o valor quantizado contra aquela tolerancia reprovaria duas implementacoes
// perfeitamente corretas.
//
// Isso NAO e defeito de nenhum dos dois lados, nem motivo para afrouxar a
// tolerancia. Sao dois orcamentos de erro diferentes, e confundi-los e o
// mesmo erro que o contrato ja registra para o `||g|| = 1 +- 1e-3`:
//
//   PARIDADE (1e-7 g) ...... "as duas implementacoes calculam a MESMA
//                            formula?". Mede-se no valor computado, em
//                            `FeaturesDeEpoca`, antes daqui.
//   QUANTIZACAO (7,6e-6 g).. "a representacao de 16 bits custa desempenho?".
//                            Ja foi medido e aprovado por outro criterio:
//                            Delta-kappa ~1e-4 nas tres bases
//                            (`ml/experimentos/quantizacao_features.py`),
//                            contra +0,123 de ganho do HMM.
//
// E a quantizacao fica 84x abaixo do piso de ruido do ENMO no MPU6050
// (0,64 mg): ela nao e observavel no sensor que o projeto usa. O caso mais
// grosso dos quatro e `enmo_max`, com fundo de escala 16 g: passo 2,44e-4 g,
// que e 0,38x o piso de ruido -- ainda abaixo, mas com folga de menos de 3x.
// E o numero a revisar se o fundo de escala mudar.
//
// `testar_perda_de_quantizacao` em testes_dourado.cpp mede os quatro.
VetorDeFeatures quantizar(const FeaturesDeEpoca &f);

// Desfaz a quantizacao. `amostras` e necessario porque `zcr` e `p_frac` sao
// guardados como contagem, e a contagem sozinha nao e a fracao.
FeaturesDeEpoca desquantizar(const VetorDeFeatures &v, uint16_t amostras);

// ── Acumulador ────────────────────────────────────────────────────────
//
// ⚠️ ESTE ACUMULADOR GUARDA A JANELA INTEIRA, e isso nao e desleixo: e
// imposto pela matematica do estimador.
//
// O filtro de gravidade e de FASE ZERO -- aplicado ida e volta. A passagem de
// volta le a janela do fim para o comeco, entao a gravidade estimada na
// amostra 0 depende da amostra 959. Nao existe forma O(1) de calcular isto em
// streaming: qualquer acumulador incremental seria um filtro CAUSAL, que e um
// estimador diferente, com divergencia nao-declarada -- a mesma armadilha que
// o contrato ja fecha para `g_ref` na secao 2.6.
//
// O custo em RAM, medido por `sizeof` e reportado por `capacidade.cpp`:
//
//     bruto[3][960]    float ... 11 520 B   as amostras, preservadas porque a
//                                           dinamica e (bruto - gravidade)
//     din2[960]        float .... 3 840 B   soma dos quadrados da dinamica,
//                                           acumulada eixo a eixo
//     gravidade[960]   float .... 3 840 B   um eixo filtrado por vez; na
//                                           primeira fase serve de vetor de
//                                           magnitudes para o `zcr`
//     ------------------------------------
//     total ..................... 19 200 B  ~18,8 KiB
//
// Note que NAO ha um quarto vetor de rascunho para o filtro: ele roda no
// lugar (ver `filtrar_ida_e_volta`), e o vetor `gravidade` e reaproveitado
// entre as duas fases do calculo. Sem essas duas economias o custo seria
// 26,9 KB em vez de 18,8 KB.
//
// Isso e 58 % do orcamento de heap "conservador" (32 KiB) que o estudo do
// buffer usou para dimensionar a autonomia -- e o estudo NAO contabilizou
// este custo, porque na epoca nao havia implementacao para medir. E o achado
// orcamentario desta implementacao, e esta registrado no diario.
//
// A alternativa que economizaria metade -- guardar a janela em int16 em vez de
// float -- foi recusada: ela injetaria quantizacao DENTRO do calculo das
// features (um passo de 2,4e-3 g sobre amostras de ~1 g), e nao na saida dele.
// Isso moveria o piso de paridade do ENMO de 1e-7 para a ordem de 1e-3 g,
// quatro ordens de grandeza, por 9,6 KB.
class AcumuladorDeFeatures {
 public:
  AcumuladorDeFeatures();

  // Zera a janela para uma epoca nova.
  void iniciar();

  // Arquiva uma amostra, em **g** (nao em m/s^2 -- ver a armadilha de unidade
  // da secao 2.6 do contrato: `f` esta em g, o resto do payload em m/s^2).
  //
  // Depois de `AMOSTRAS_MAXIMAS_POR_EPOCA` a amostra NAO entra, e o excedente
  // e contado em `descartadas()`. Nao e silencioso de proposito: uma janela
  // que transbordou produz features de uma fracao da epoca, e quem consome
  // precisa poder saber.
  void amostrar(float ax, float ay, float az);

  // Fecha a epoca e calcula as sete quantidades.
  //
  // Devolve false -- e NAO escreve em `saida` -- quando a epoca nao tem
  // paridade declarada: menos de `AMOSTRAS_MINIMAS_PARA_PARIDADE` amostras,
  // ou `fs` invalido para o filtro. Essa recusa E a implementacao da decisao
  // do contrato "o dispositivo nao emite `f` de epoca truncada": em vez de
  // decidir isso no servidor, o dispositivo nao produz o vetor.
  bool fechar(float fs, FeaturesDeEpoca *saida);

  uint32_t arquivadas() const { return n_; }
  uint32_t descartadas() const { return descartadas_; }

 private:
  float bruto_[3][AMOSTRAS_MAXIMAS_POR_EPOCA];
  float din2_[AMOSTRAS_MAXIMAS_POR_EPOCA];
  float gravidade_[AMOSTRAS_MAXIMAS_POR_EPOCA];
  uint32_t n_;
  uint32_t descartadas_;
};

}  // namespace dormio

#endif  // DORMIO_NUCLEO_CARACTERISTICAS_H
