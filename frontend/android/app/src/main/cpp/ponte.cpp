// ponte.cpp -- a camada JNI entre o app Android e o `ColetorCelular` (APP-02).
//
// Fina de proposito: nenhuma conta mora aqui. Tudo o que calcula esta em
// `firmware/nucleo/`, testado no host. Aqui so se convertem tipos.
//
// O lado Java e `app.dormiosmart.coleta.NucleoNativo`. O ponteiro do coletor
// viaja como `long`; ele e criado e destruido pelo Java, uma noite por vez.

#include <jni.h>
#include <stdint.h>

#include "coletor_celular.h"

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

}  // extern "C"
