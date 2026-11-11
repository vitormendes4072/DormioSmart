// ponte.cpp -- a camada JNI entre o app Android e o `ColetorCelular` (APP-02).
//
// Fina de proposito: nenhuma conta mora aqui. Tudo o que calcula esta em
// `firmware/nucleo/`, testado no host. Aqui so se convertem tipos.
//
// O lado Java e `app.dormiosmart.coleta.NucleoNativo`. O ponteiro do coletor
// viaja como `long`; ele e criado e destruido pelo Java, uma noite por vez.

#include <jni.h>
#include <stdint.h>

#include "calibracao.h"
#include "coletor_celular.h"

using dormio::Calibracao;
using dormio::COLETOR_NADA;
using dormio::COLETOR_PAYLOAD;
using dormio::ColetorCelular;
using dormio::ResolucaoDeParede;
using dormio::ResultadoDoColetor;
using dormio::TAMANHO_DO_PAYLOAD;

namespace {

ColetorCelular *coletor(jlong ponteiro) {
  return reinterpret_cast<ColetorCelular *>(static_cast<intptr_t>(ponteiro));
}

}  // namespace

extern "C" {

JNIEXPORT jlong JNICALL Java_app_dormiosmart_coleta_NucleoNativo_criar(JNIEnv *, jclass) {
  // ~57 KiB (a grade, a janela das features e o anel da cadeia): no heap.
  return static_cast<jlong>(reinterpret_cast<intptr_t>(new ColetorCelular()));
}

JNIEXPORT void JNICALL Java_app_dormiosmart_coleta_NucleoNativo_destruir(JNIEnv *, jclass,
                                                                         jlong p) {
  delete coletor(p);
}

JNIEXPORT void JNICALL Java_app_dormiosmart_coleta_NucleoNativo_iniciar(
    JNIEnv *, jclass, jlong p, jlong origem_us, jlong mono_ref_ms, jlong parede_ref_ms) {
  ResolucaoDeParede parede;
  parede.sincronizar(static_cast<uint64_t>(mono_ref_ms), static_cast<int64_t>(parede_ref_ms));
  coletor(p)->iniciar(static_cast<uint64_t>(origem_us), parede);
}

// Um lote de amostras: `t_us[i]` e o instante monotonico da amostra i, e
// `xyz[3i..3i+2]` os tres eixos em m/s^2. Em lote para nao pagar uma chamada
// JNI por amostra (50 por segundo a noite toda).
JNIEXPORT void JNICALL Java_app_dormiosmart_coleta_NucleoNativo_amostrar(
    JNIEnv *env, jclass, jlong p, jlongArray t_us, jfloatArray xyz, jint n) {
  if (n <= 0) return;
  jlong *t = env->GetLongArrayElements(t_us, 0);
  jfloat *v = env->GetFloatArrayElements(xyz, 0);
  ColetorCelular *c = coletor(p);
  for (jint i = 0; i < n; i++) {
    c->amostrar(static_cast<uint64_t>(t[i]), v[3 * i], v[3 * i + 1], v[3 * i + 2]);
  }
  env->ReleaseFloatArrayElements(xyz, v, JNI_ABORT);
  env->ReleaseLongArrayElements(t_us, t, JNI_ABORT);
}

JNIEXPORT void JNICALL Java_app_dormiosmart_coleta_NucleoNativo_definirTemperatura(
    JNIEnv *, jclass, jlong p, jfloat graus_c) {
  coletor(p)->definir_temperatura(graus_c);
}

// O proximo payload pronto, ou null quando nenhuma epoca fechou. Epocas
// recusadas e sem payload sao contadas e puladas: quem quer saber delas le os
// contadores.
JNIEXPORT jstring JNICALL Java_app_dormiosmart_coleta_NucleoNativo_proximoPayload(JNIEnv *env,
                                                                                 jclass,
                                                                                 jlong p) {
  static char json[TAMANHO_DO_PAYLOAD];
  ColetorCelular *c = coletor(p);
  for (;;) {
    uint32_t n = 0;
    const ResultadoDoColetor r = c->proximo(json, sizeof(json), &n);
    if (r == COLETOR_NADA) return 0;
    if (r == COLETOR_PAYLOAD) return env->NewStringUTF(json);
  }
}

// [recebidas, fora_de_ordem, com_payload, recusadas, recusadas_por_taxa,
//  sem_features, sem_payload, taxa_mHz]
JNIEXPORT jlongArray JNICALL Java_app_dormiosmart_coleta_NucleoNativo_contadores(JNIEnv *env,
                                                                                jclass,
                                                                                jlong p) {
  const ColetorCelular *c = coletor(p);
  const jlong v[8] = {
      static_cast<jlong>(c->amostras_recebidas()),
      static_cast<jlong>(c->amostras_fora_de_ordem()),
      static_cast<jlong>(c->epocas_com_payload()),
      static_cast<jlong>(c->epocas_recusadas()),
      static_cast<jlong>(c->recusadas_por_taxa()),
      static_cast<jlong>(c->epocas_sem_features()),
      static_cast<jlong>(c->epocas_sem_payload()),
      static_cast<jlong>(c->ultima_taxa_hz() * 1000.0 + 0.5),
  };
  jlongArray saida = env->NewLongArray(8);
  env->SetLongArrayRegion(saida, 0, 8, v);
  return saida;
}

JNIEXPORT jlong JNICALL Java_app_dormiosmart_coleta_NucleoNativo_antecedenciaDaOrigemUs(JNIEnv *,
                                                                                       jclass) {
  return static_cast<jlong>(dormio::ANTECEDENCIA_DA_ORIGEM_US);
}

// ── CAL-03, etapa 2 ────────────────────────────────────────────────────────

JNIEXPORT jint JNICALL Java_app_dormiosmart_coleta_NucleoNativo_pontosMinimos(JNIEnv *, jclass) {
  return static_cast<jint>(dormio::PONTOS_MINIMOS_CALIBRACAO);
}

// [aceita, desvio x3, escala x3, coef_temp x3, temp_ref]: a ordem de
// `Calibracao.parametros()` no Java.
JNIEXPORT void JNICALL Java_app_dormiosmart_coleta_NucleoNativo_definirCalibracao(
    JNIEnv *env, jclass, jlong p, jdoubleArray parametros) {
  if (env->GetArrayLength(parametros) != 11) return;
  jdouble *v = env->GetDoubleArrayElements(parametros, 0);
  Calibracao c;
  c.aceita = v[0] != 0.0;
  for (int k = 0; k < 3; k++) {
    c.desvio[k] = v[1 + k];
    c.escala[k] = v[4 + k];
    c.coef_temp[k] = v[7 + k];
  }
  c.temp_ref_c = v[10];
  env->ReleaseDoubleArrayElements(parametros, v, JNI_ABORT);
  coletor(p)->definir_calibracao(c);
}

// {x, y, z, temp} do ponto parado da ultima epoca, ou null.
JNIEXPORT jdoubleArray JNICALL Java_app_dormiosmart_coleta_NucleoNativo_pontoParado(JNIEnv *env,
                                                                                   jclass,
                                                                                   jlong p) {
  double ponto[4];
  if (!coletor(p)->ponto_parado(ponto)) return 0;
  jdoubleArray saida = env->NewDoubleArray(4);
  env->SetDoubleArrayRegion(saida, 0, 4, ponto);
  return saida;
}

// `xyz` intercalado e `temps`, `n` pontos. Devolve os 19 numeros que
// `Calibracao.doResultado` le: [aceita, desvio x3, escala x3, coef_temp x3,
// temp_ref, modos x3, usou_temperatura, n, erro_antes, erro_depois, iteracoes].
JNIEXPORT jdoubleArray JNICALL Java_app_dormiosmart_coleta_NucleoNativo_estimar(
    JNIEnv *env, jclass, jdoubleArray xyz, jdoubleArray temps, jint n) {
  Calibracao c;
  if (n > 0 && env->GetArrayLength(xyz) >= 3 * n && env->GetArrayLength(temps) >= n) {
    jdouble *v = env->GetDoubleArrayElements(xyz, 0);
    jdouble *t = env->GetDoubleArrayElements(temps, 0);
    // `jdouble` e `double`: o vetor intercalado ja e o `double (*)[3]` do nucleo.
    c = dormio::estimar_calibracao(reinterpret_cast<const double(*)[3]>(v), t,
                                   static_cast<uint32_t>(n));
    env->ReleaseDoubleArrayElements(temps, t, JNI_ABORT);
    env->ReleaseDoubleArrayElements(xyz, v, JNI_ABORT);
  }
  const double r[19] = {
      c.aceita ? 1.0 : 0.0,
      c.desvio[0], c.desvio[1], c.desvio[2],
      c.escala[0], c.escala[1], c.escala[2],
      c.coef_temp[0], c.coef_temp[1], c.coef_temp[2],
      c.temp_ref_c,
      static_cast<double>(c.modos[0]), static_cast<double>(c.modos[1]),
      static_cast<double>(c.modos[2]),
      c.usou_temperatura ? 1.0 : 0.0,
      static_cast<double>(n > 0 ? n : 0),
      c.erro_antes_g, c.erro_depois_g,
      static_cast<double>(c.iteracoes),
  };
  jdoubleArray saida = env->NewDoubleArray(19);
  env->SetDoubleArrayRegion(saida, 0, 19, r);
  return saida;
}

}  // extern "C"
