// testes_fila_flash.cpp -- a fila na flash (FW-08) contra uma flash simulada.
//
// A simulacao obedece as duas regras da NOR que a fila precisa respeitar, e
// CONTA as violacoes em vez de corrigi-las:
//
//   - programar so leva bits de 1 a 0: o byte gravado e `antigo & novo`, e
//     pedir um bit 0 -> 1 conta uma violacao;
//   - apagar leva o setor inteiro de 4 KiB a 0xFF.
//
// E sabe cortar a energia: no meio de uma programacao (depois de N bytes) ou
// no meio de um apagamento (metade do setor). Depois do corte a "placa" e
// religada e a fila e montada de novo sobre a mesma memoria -- que e o que
// acontece de verdade quando a tomada solta a noite.

#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "../caracteristicas.h"
#include "../epoca.h"
#include "../fila_flash.h"
#include "../payload.h"
#include "../registro_flash.h"
#include "../relogio.h"

using namespace dormio;

static int falhas = 0;
static int total = 0;

#define VERIFICAR(cond, msg)                                              \
  do {                                                                    \
    total++;                                                              \
    if (!(cond)) {                                                        \
      falhas++;                                                           \
      printf("  FALHOU  %s\n          (%s:%d)  %s\n", msg, __FILE__,      \
             __LINE__, #cond);                                            \
    }                                                                     \
  } while (0)

static void secao(const char *nome) { printf("\n== %s\n", nome); }

// ── A flash simulada ──────────────────────────────────────────────────

class FlashSimulada : public MidiaFlash {
 public:
  explicit FlashSimulada(uint32_t setores)
      : violacoes(0), n_(setores * TAMANHO_DO_SETOR_BYTES), setores_(setores), orcamento_(-1),
        desligada_(false), cortar_apagamento_(false), engolir_(false) {
    mem_ = static_cast<uint8_t *>(malloc(n_));
    apagamentos_ = static_cast<uint32_t *>(calloc(setores, sizeof(uint32_t)));
    memset(mem_, 0xFF, n_);
  }
  ~FlashSimulada() {
    free(mem_);
    free(apagamentos_);
  }

  uint32_t tamanho() const { return n_; }

  bool ler(uint32_t endereco, void *destino, uint32_t n) {
    if (desligada_ || endereco + n > n_) return false;
    memcpy(destino, mem_ + endereco, n);
    return true;
  }

  bool programar(uint32_t endereco, const void *origem, uint32_t n) {
    if (desligada_ || endereco + n > n_) return false;
    if (engolir_) return true;  // aceita o comando e nao grava nada
    const uint8_t *o = static_cast<const uint8_t *>(origem);
    for (uint32_t i = 0; i < n; i++) {
      if (orcamento_ == 0) {
        desligada_ = true;
        return false;
      }
      if (orcamento_ > 0) orcamento_--;
      if ((o[i] & ~mem_[endereco + i]) != 0) violacoes++;
      mem_[endereco + i] = static_cast<uint8_t>(mem_[endereco + i] & o[i]);
    }
    return true;
  }

  bool apagar_setor(uint32_t endereco) {
    if (desligada_ || endereco % TAMANHO_DO_SETOR_BYTES != 0 || endereco >= n_) return false;
    if (cortar_apagamento_) {
      memset(mem_ + endereco, 0xFF, TAMANHO_DO_SETOR_BYTES / 2);
      desligada_ = true;
      return false;
    }
    memset(mem_ + endereco, 0xFF, TAMANHO_DO_SETOR_BYTES);
    apagamentos_[endereco / TAMANHO_DO_SETOR_BYTES]++;
    return true;
  }

  // Corta a energia depois de `bytes` bytes programados.
  void cortar_apos(int64_t bytes) { orcamento_ = bytes; }
  void cortar_no_proximo_apagamento() { cortar_apagamento_ = true; }
  // Um chip com defeito: diz que programou e nao programou.
  void engolir_programacao(bool sim) { engolir_ = sim; }
  void religar() {
    desligada_ = false;
    orcamento_ = -1;
    cortar_apagamento_ = false;
  }

  uint8_t *memoria() { return mem_; }
  uint32_t apagamentos_do_setor(uint32_t s) const { return apagamentos_[s]; }
  uint32_t setores() const { return setores_; }

  uint32_t violacoes;

 private:
  uint8_t *mem_;
  uint32_t n_;
  uint32_t setores_;
  uint32_t *apagamentos_;
  int64_t orcamento_;
  bool desligada_;
  bool cortar_apagamento_;
  bool engolir_;
};

// ── Fabricas ──────────────────────────────────────────────────────────

static Epoca fabricar(uint32_t indice) {
  Epoca e;
  e.indice = indice;
  e.pico_total = 9.85f;
  e.pico_ax = 0;
  e.pico_ay = 0;
  e.pico_az = 9.85f;
  e.temp_pico = 25.0f;
  e.amostras = 1500;
  e.esperadas = 1500;
  e.duracao_s = DURACAO_EPOCA_BASE_S;
  e.nivel = 0;
  e.flags = 0;
  return e;
}

static FeaturesDeEpoca vetor_tipico() {
  FeaturesDeEpoca f;
  f.enmo_media = 0.000123456;
  f.enmo_desvio = 0.0021;
  f.enmo_max = 0.0876;
  f.mag_din_media = 0.0244;
  f.gx = 0.6;
  f.gy = 0.0;
  f.gz = 0.8;
  f.cruzamentos = 400;     // zcr = 400/959
  f.amostras_acima = 12;   // p_frac = 12/960
  f.amostras = 960;
  f.zcr = 400.0 / 959.0;
  f.p_frac = 12.0 / 960.0;
  return f;
}

static InstanteDaEpoca no_mono(uint32_t s) {
  InstanteDaEpoca i;
  i.e_parede = false;
  i.segundos = s;
  return i;
}

// Grava `n` epocas de indices `primeiro..`, alternando com e sem vetor.
static uint32_t gravar(FilaNaFlash *fila, uint32_t primeiro, uint32_t n) {
  const VetorDeFeatures v = quantizar(vetor_tipico());
  uint32_t ok = 0;
  for (uint32_t i = 0; i < n; i++) {
    const uint32_t idx = primeiro + i;
    if (fila->guardar(fabricar(idx), (idx % 2u) ? 0 : &v, no_mono(idx * 30u)) == GUARDADO) ok++;
  }
  return ok;
}

// Os pendentes estao em ordem crescente de indice, sem buraco, a partir de
// `primeiro`? E a propriedade que a analise precisa: a fila nunca troca nem
// pula epoca.
static bool pendentes_contiguos(FilaNaFlash *fila, uint32_t primeiro, uint32_t n) {
  static RegistroDeEpoca lidos[40000];
  if (n > 40000) return false;
  if (fila->ler_pendentes(lidos, n) != n) return false;
  for (uint32_t i = 0; i < n; i++) {
    if (lidos[i].epoca.indice != primeiro + i) return false;
    if (i > 0 && lidos[i].seq <= lidos[i - 1].seq) return false;
  }
  return true;
}

// ── O registro ────────────────────────────────────────────────────────

static void testar_registro() {
  secao("registro -- 64 B, e o CRC pega cada byte menos o de entregue");
  VERIFICAR(sizeof(RegistroDeEpoca) == 64, "64 B: quatro por pagina, 64 por setor");
  VERIFICAR(REGISTROS_POR_SETOR == 64, "nenhum registro atravessa setor");

  RegistroDeEpoca r;
  r.seq = 7;
  r.sessao = 3;
  r.bandeiras = REGISTRO_TEM_FEATURES;
  r.entregue = ENTREGUE_PENDENTE;
  r.instante_s = 123456;
  r.epoca = fabricar(42);
  r.vetor = quantizar(vetor_tipico());
  r.crc = 0;
  uint8_t bytes[64];
  serializar_registro(r, bytes);

  RegistroDeEpoca lido;
  VERIFICAR(classificar_slot(bytes, &lido) == SLOT_VALIDO, "o registro serializado e valido");
  VERIFICAR(lido.epoca.indice == 42 && lido.instante_s == 123456 && lido.sessao == 3,
            "ida e volta preserva os campos");

  // Cada byte coberto, virado, tem de invalidar o registro. Um CRC que
  // pulasse o vetor ou a epoca deixaria passar lixo como medida.
  int nao_detectados = 0;
  for (uint32_t i = 0; i < 64; i++) {
    if (i == OFFSET_DO_ENTREGUE) continue;
    uint8_t c[64];
    memcpy(c, bytes, 64);
    c[i] = static_cast<uint8_t>(c[i] ^ 0x01);
    if (classificar_slot(c, 0) == SLOT_VALIDO) nao_detectados++;
  }
  VERIFICAR(nao_detectados == 0, "um bit virado em qualquer byte coberto invalida o registro");

  uint8_t c[64];
  memcpy(c, bytes, 64);
  c[OFFSET_DO_ENTREGUE] = ENTREGUE_CONFIRMADO;
  VERIFICAR(classificar_slot(c, &lido) == SLOT_VALIDO && lido.foi_entregue(),
            "marcar entregue nao invalida o registro");
  c[OFFSET_DO_ENTREGUE] = 0x0F;
  VERIFICAR(classificar_slot(c, &lido) == SLOT_VALIDO && !lido.foi_entregue(),
            "byte de entregue pela metade = PENDENTE (duplicata, nunca perda)");

  uint8_t vazio[64];
  memset(vazio, 0xFF, 64);
  VERIFICAR(classificar_slot(vazio, 0) == SLOT_VAZIO, "0xFF inteiro e slot vazio");
  vazio[10] = 0x00;
  VERIFICAR(classificar_slot(vazio, 0) == SLOT_CORROMPIDO, "um byte programado e corte");
}

static void testar_instante() {
  secao("instante -- parede quando ha, monotonico quando nao ha");
  ResolucaoDeParede sem;
  InstanteDaEpoca i = instante_para_gravar(sem, 95500);
  VERIFICAR(!i.e_parede && i.segundos == 95, "sem sincronia: segundos desde o boot");

  ResolucaoDeParede com;
  com.sincronizar(100000, 1793404800000ll);  // 2026-10-31T00:00:00Z no mono 100 s
  i = instante_para_gravar(com, 130000);
  VERIFICAR(i.e_parede && i.segundos == 1793404830u, "com sincronia: unix s do inicio");
  i = instante_para_gravar(com, 130999);
  VERIFICAR(i.segundos == 1793404830u, "o ms some para baixo, nunca para cima");
}

// ── A fila ────────────────────────────────────────────────────────────

static void testar_ida_e_volta() {
  secao("fila -- grava, le na ordem, confirma, e o reset nao apaga nada");
  FlashSimulada flash(8);
  {
    FilaNaFlash fila(&flash);
    VERIFICAR(fila.montar(), "particao de 8 setores monta");
    VERIFICAR(fila.pendentes() == 0 && fila.sessao() == 1, "vazia, sessao 1");
    VERIFICAR(gravar(&fila, 0, 10) == 10, "10 epocas guardadas");
    VERIFICAR(fila.pendentes() == 10, "10 pendentes");

    RegistroDeEpoca r[10];
    VERIFICAR(fila.ler_pendentes(r, 10) == 10, "le as 10");
    VERIFICAR(r[0].tem_features() && !r[1].tem_features(), "a bandeira do vetor viaja");
    VERIFICAR(r[0].vetor.cruzamentos == 400 && r[0].vetor.amostras_acima == 12,
              "o vetor guardado e o quantizado");
    VERIFICAR(pendentes_contiguos(&fila, 0, 10), "ordem de gravacao");
    VERIFICAR(fila.confirmar(4) == 4 && fila.pendentes() == 6, "confirma as 4 mais antigas");
  }
  {
    FilaNaFlash fila(&flash);
    VERIFICAR(fila.montar(), "remonta depois do 'reset'");
    VERIFICAR(fila.pendentes() == 6, "as 6 pendentes sobreviveram, as 4 confirmadas nao voltam");
    VERIFICAR(pendentes_contiguos(&fila, 4, 6), "a cauda e a epoca 4");
    VERIFICAR(fila.sessao() == 2, "cada montagem e uma sessao nova");
    VERIFICAR(gravar(&fila, 10, 5) == 5 && pendentes_contiguos(&fila, 4, 11),
              "o que se grava depois continua a serie");
  }
  {
    FilaNaFlash fila(&flash);
    VERIFICAR(fila.montar() && fila.sessao() == 3, "terceira sessao");
  }
  VERIFICAR(flash.violacoes == 0, "nenhum bit 0 -> 1 pedido a flash");
}

static void testar_fila_cheia() {
  secao("fila cheia -- recusa a nova, nunca apaga pendente");
  FlashSimulada flash(4);
  FilaNaFlash fila(&flash);
  fila.montar();
  uint32_t aceitas = 0;
  ResultadoDaGuarda ultimo = GUARDADO;
  for (uint32_t i = 0; i < 1000; i++) {
    ultimo = fila.guardar(fabricar(i), 0, no_mono(i));
    if (ultimo != GUARDADO) break;
    aceitas++;
  }
  VERIFICAR(ultimo == FILA_CHEIA, "chega a FILA_CHEIA");
  VERIFICAR(aceitas >= fila.capacidade_garantida() && aceitas <= fila.slots(),
            "aceita pelo menos a capacidade garantida");
  VERIFICAR(fila.estatisticas().descartes == 1, "a recusa e contada");
  VERIFICAR(pendentes_contiguos(&fila, 0, aceitas), "tudo o que foi aceito continua la, em ordem");

  VERIFICAR(fila.confirmar(64) == 64, "o servidor confirma um setor");
  VERIFICAR(fila.guardar(fabricar(aceitas), 0, no_mono(0)) == GUARDADO,
            "com um setor livre, volta a aceitar");
  VERIFICAR(pendentes_contiguos(&fila, 64, aceitas - 64 + 1), "e a serie continua sem buraco");

  // Agora os pendentes atravessam o fim fisico da particao: os mais antigos
  // estao no fim, o mais novo no slot 0. A montagem tem de achar a cauda pela
  // ordem de gravacao, nao pela posicao -- procurar do slot 0 daria o mais
  // novo como o mais antigo, e o lote sairia fora de ordem.
  FilaNaFlash remontada(&flash);
  VERIFICAR(remontada.montar() && remontada.pendentes() == aceitas - 64 + 1,
            "remonta com os pendentes dando a volta");
  VERIFICAR(pendentes_contiguos(&remontada, 64, aceitas - 64 + 1),
            "a cauda e a mais antiga, nao a do slot 0");
  VERIFICAR(flash.violacoes == 0, "nenhuma violacao de NOR");
}

static void testar_muitas_voltas() {
  secao("muitas voltas -- o desgaste fica igual entre setores");
  FlashSimulada flash(8);
  FilaNaFlash fila(&flash);
  fila.montar();
  uint32_t proximo_pendente = 0;
  uint32_t ok = 0;
  const uint32_t N = 20000;
  for (uint32_t i = 0; i < N; i++) {
    if (fila.guardar(fabricar(i), 0, no_mono(i)) == GUARDADO) ok++;
    if (i % 37 == 36) {
      // Confirma quase tudo, deixando pendentes atravessarem a volta do log.
      const uint32_t c = fila.pendentes() > 5 ? fila.pendentes() - 5 : 0;
      proximo_pendente += fila.confirmar(c);
    }
  }
  VERIFICAR(ok == N, "nenhuma epoca recusada com o servidor confirmando");
  VERIFICAR(pendentes_contiguos(&fila, proximo_pendente, fila.pendentes()),
            "pendentes contiguos depois de dezenas de voltas");

  uint32_t mn = 0xFFFFFFFFu, mx = 0;
  for (uint32_t s = 0; s < flash.setores(); s++) {
    if (flash.apagamentos_do_setor(s) < mn) mn = flash.apagamentos_do_setor(s);
    if (flash.apagamentos_do_setor(s) > mx) mx = flash.apagamentos_do_setor(s);
  }
  printf("  %u epocas em 8 setores: %u a %u apagamentos por setor\n", N, mn, mx);
  VERIFICAR(mx - mn <= 1, "nivelamento por construcao: setores diferem em no maximo 1 apagamento");
  VERIFICAR(mn >= 30, "o log deu dezenas de voltas");

  FilaNaFlash remontada(&flash);
  VERIFICAR(remontada.montar() && remontada.pendentes() == fila.pendentes(),
            "remontar no meio da volta acha os mesmos pendentes");
  VERIFICAR(pendentes_contiguos(&remontada, proximo_pendente, remontada.pendentes()),
            "e na mesma ordem");
  VERIFICAR(flash.violacoes == 0, "nenhuma violacao de NOR");
}

static void testar_corte_na_gravacao() {
  secao("corte de energia em cada byte de uma gravacao");
  int perdas = 0, quebras = 0, violacoes = 0;
  for (int64_t corte = 0; corte <= 64; corte++) {
    FlashSimulada flash(4);
    {
      FilaNaFlash fila(&flash);
      fila.montar();
      gravar(&fila, 0, 5);
      flash.cortar_apos(corte);
      fila.guardar(fabricar(5), 0, no_mono(5));
    }
    flash.religar();
    FilaNaFlash fila(&flash);
    if (!fila.montar()) {
      quebras++;
      continue;
    }
    const uint32_t esperado = corte >= 64 ? 6u : 5u;
    if (fila.pendentes() != esperado || !pendentes_contiguos(&fila, 0, esperado)) perdas++;
    // A fila tem de seguir gravando depois do corte, sem programar por cima
    // do slot sujo.
    if (fila.guardar(fabricar(100), 0, no_mono(0)) != GUARDADO) quebras++;
    if (fila.pendentes() != esperado + 1) perdas++;
    violacoes += static_cast<int>(flash.violacoes);
  }
  VERIFICAR(perdas == 0, "nenhum corte apaga o que ja estava gravado");
  VERIFICAR(quebras == 0, "depois de qualquer corte a fila monta e volta a gravar");
  VERIFICAR(violacoes == 0, "o slot sujo e pulado, nunca reprogramado");
}

static void testar_corte_na_confirmacao() {
  secao("corte no meio da confirmacao -- reenvia, nao perde");
  FlashSimulada flash(4);
  {
    FilaNaFlash fila(&flash);
    fila.montar();
    gravar(&fila, 0, 3);
  }
  // O byte de entregue do primeiro registro ficou pela metade: 0x0F.
  const uint8_t meio = 0x0F;
  flash.programar(OFFSET_DO_ENTREGUE, &meio, 1);
  FilaNaFlash fila(&flash);
  fila.montar();
  VERIFICAR(fila.pendentes() == 3, "o registro pela metade continua pendente");
  VERIFICAR(fila.confirmar(1) == 1 && fila.pendentes() == 2, "confirmar de novo termina o servico");
  VERIFICAR(pendentes_contiguos(&fila, 1, 2), "e a cauda anda");
  VERIFICAR(flash.violacoes == 0, "0x0F -> 0x00 so leva bits a zero");
}

static void testar_corte_no_apagamento() {
  secao("corte no meio do apagamento de um setor");
  FlashSimulada flash(4);
  uint32_t pendentes_antes = 0;
  {
    FilaNaFlash fila(&flash);
    fila.montar();
    // Enche tres setores e meio, confirma os dois primeiros: o proximo
    // apagamento sera o do setor 0, quando a cabeca der a volta.
    gravar(&fila, 0, 255);
    fila.confirmar(128);
    pendentes_antes = fila.pendentes();
    gravar(&fila, 255, 1);  // fecha o setor 3
    pendentes_antes++;
    flash.cortar_no_proximo_apagamento();
    VERIFICAR(fila.guardar(fabricar(256), 0, no_mono(0)) == FALHA_NA_FLASH,
              "o apagamento cortado devolve falha");
  }
  flash.religar();
  FilaNaFlash fila(&flash);
  VERIFICAR(fila.montar(), "monta com meio setor apagado");
  VERIFICAR(fila.pendentes() == pendentes_antes, "nenhum pendente perdido");
  VERIFICAR(fila.guardar(fabricar(256), 0, no_mono(0)) == GUARDADO,
            "o setor e apagado de novo e a gravacao segue");
  VERIFICAR(pendentes_contiguos(&fila, 128, pendentes_antes + 1), "serie inteira, em ordem");
  VERIFICAR(flash.violacoes == 0, "nenhuma violacao de NOR");
}

static void testar_releitura() {
  secao("releitura -- `programar` dizer sim nao prova que gravou");
  FlashSimulada flash(4);
  FilaNaFlash fila(&flash);
  fila.montar();
  gravar(&fila, 0, 3);
  flash.engolir_programacao(true);
  VERIFICAR(fila.guardar(fabricar(3), 0, no_mono(3)) == FALHA_NA_FLASH,
            "chip que engole a escrita: a releitura acusa");
  VERIFICAR(fila.pendentes() == 3 && fila.estatisticas().falhas_de_escrita == 1,
            "e a epoca nao conta como guardada");
  flash.engolir_programacao(false);
  VERIFICAR(fila.guardar(fabricar(3), 0, no_mono(3)) == GUARDADO &&
                pendentes_contiguos(&fila, 0, 4),
            "com o chip bom de novo, a serie segue");
}

// ── Do registro ao payload ────────────────────────────────────────────

static bool tem(const char *texto, const char *trecho) { return strstr(texto, trecho) != 0; }

static void testar_payload_do_registro() {
  secao("payload -- o registro guardado vira o JSON do contrato");
  FlashSimulada flash(4);
  const VetorDeFeatures v = quantizar(vetor_tipico());
  ResolucaoDeParede sincronizada;
  sincronizada.sincronizar(100000, 1793404800000ll);

  uint16_t sessao_antiga = 0;
  {
    FilaNaFlash fila(&flash);
    fila.montar();
    sessao_antiga = fila.sessao();
    // 0: parede gravada, com vetor. 1: monotonico, sem vetor.
    fila.guardar(fabricar(0), &v, instante_para_gravar(sincronizada, 130000));
    fila.guardar(fabricar(1), 0, no_mono(160));

    RegistroDeEpoca r[2];
    fila.ler_pendentes(r, 2);
    char buf[512];
    uint32_t n = 0;
    bool incluiu = false;
    VERIFICAR(montar_payload_do_registro(r[1], fila.sessao(), sincronizada, buf, sizeof(buf),
                                         &n, &incluiu) == PAYLOAD_OK,
              "monotonico desta sessao monta");
    VERIFICAR(tem(buf, "\"ts\":\"2026-10-31T00:01:00.000Z\""),
              "monotonico desta sessao com parede valida: ts resolvido agora");
    VERIFICAR(!incluiu && !tem(buf, "\"f\""), "sem vetor, sem `f`");
  }

  FilaNaFlash fila(&flash);
  fila.montar();
  VERIFICAR(fila.sessao() != sessao_antiga, "o reset abriu outra sessao");
  RegistroDeEpoca r[2];
  fila.ler_pendentes(r, 2);
  char buf[512];
  uint32_t n = 0;
  bool incluiu = false;

  VERIFICAR(montar_payload_do_registro(r[0], fila.sessao(), ResolucaoDeParede(), buf, sizeof(buf),
                                       &n, &incluiu) == PAYLOAD_OK,
            "parede gravada monta mesmo sem relogio agora");
  VERIFICAR(tem(buf, "\"ts\":\"2026-10-31T00:00:30.000Z\""),
            "a hora gravada sobrevive ao reset");
  VERIFICAR(incluiu && tem(buf, "\"f\":[") && tem(buf, "\"fs\":32"), "o vetor vai, com fs = 32 Hz");

  // `zcr` volta da contagem: 400/959. Le o quinto numero de `f`.
  const char *p = strstr(buf, "\"f\":[");
  double f[6] = {0, 0, 0, 0, 0, 0};
  if (p) {
    p += 5;
    for (int i = 0; i < 6; i++) {
      char *fim = 0;
      f[i] = strtod(p, &fim);
      p = fim + 1;
    }
  }
  VERIFICAR(fabs(f[4] - 400.0 / 959.0) < 1e-9, "zcr exato: a contagem nao e quantizada");
  VERIFICAR(fabs(f[0] - 0.000123456) < 1.6e-5, "enmo_media dentro de um passo do u16");

  VERIFICAR(montar_payload_do_registro(r[1], fila.sessao(), sincronizada, buf, sizeof(buf), &n,
                                       &incluiu) == PAYLOAD_OK,
            "monotonico de sessao antiga monta");
  VERIFICAR(!tem(buf, "\"ts\""),
            "monotonico de outra sessao sai SEM ts: o relogio que o datava morreu no reset");
}

int main() {
  printf("TESTES DA FILA NA FLASH (FW-08)\n");
  testar_registro();
  testar_instante();
  testar_ida_e_volta();
  testar_fila_cheia();
  testar_muitas_voltas();
  testar_corte_na_gravacao();
  testar_corte_na_confirmacao();
  testar_corte_no_apagamento();
  testar_releitura();
  testar_payload_do_registro();

  printf("\n-----------------------------------------\n");
  printf("%d verificacoes, %d falhas\n", total, falhas);
  return falhas == 0 ? 0 : 1;
}
