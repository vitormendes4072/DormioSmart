// leitor_json.h -- leitor JSON minimo, para o alvo de teste do vetor dourado.
//
// ╔══════════════════════════════════════════════════════════════════════╗
// ║ ESTE ARQUIVO NAO EMBARCA. Ele vive em `testes/` de proposito.        ║
// ╚══════════════════════════════════════════════════════════════════════╝
//
// O firmware nao le JSON: ele ESCREVE (`payload.cpp`, com `snprintf`). Quem
// precisa ler e o alvo de teste, no host, para conferir a paridade contra
// `ml/testes/vetor_dourado.json`. Pondo o leitor em `testes/`, nenhum sketch
// consegue inclui-lo por acidente e o `FONTES` do Makefile continua sendo so
// o que roda na placa.
//
// ── AS TRES SAIDAS QUE EXISTIAM, E POR QUE ESTA ───────────────────────
//
// O `DATA-07b` registrou o problema assim: "nao ha parser JSON no nucleo, que
// e `-fno-exceptions -fno-rtti` de proposito". As opcoes eram tres.
//
// (1) VENDORAR UMA BIBLIOTECA (nlohmann/json, RapidJSON, cJSON). Recusada.
//     As duas primeiras sao C++ com excecoes e RTTI no caminho de erro --
//     `nlohmann` lanca `json::parse_error`, e com `-fno-exceptions` isso nao
//     compila, nem deve: desligar excecoes e escolha do projeto, nao acidente.
//     A `cJSON` e C e compilaria, mas aloca um no por elemento: o dourado tem
//     5 casos x 960 amostras x 3 eixos = 14 400 numeros, e a arvore
//     resultante custaria mais que o arquivo. E qualquer das tres acrescenta
//     uma dependencia versionada a um repositorio de TCC para ler um arquivo
//     de teste.
//
// (2) GERAR UM .cpp A PARTIR DO JSON (um script que transcreve o dourado para
//     um `static const float[]`). Tecnicamente o mais simples, e foi a
//     primeira ideia. Recusada por um motivo que e o proprio assunto do item:
//     **o gerador seria um segundo lugar onde as definicoes podem divergir.**
//     O vetor dourado existe para que duas implementacoes da mesma formula
//     nao se afastem em silencio; introduzir um transcodificador entre o
//     arquivo versionado e o teste cria exatamente mais uma copia para sair
//     de sincronia -- e uma que ninguem olharia, porque seria "codigo
//     gerado". O `DATA-07c` ja gastou uma entrada inteira de diario
//     descobrindo que o dourado se regravava sozinho; um gerador no caminho
//     e o mesmo defeito com outra roupa.
//
// (3) UM LEITOR MINIMO QUE LE O ARQUIVO VERSIONADO. Escolhida. O teste abre
//     `ml/testes/vetor_dourado.json` -- o mesmo arquivo que o pytest confere,
//     byte a byte, sem etapa intermediaria. Se o dourado mudar, os dois lados
//     veem a mudanca no mesmo instante.
//
// ── COMO ELE EVITA PRECISAR DE EXCECOES ───────────────────────────────
//
// Um parser que constroi uma arvore precisa de um canal de erro, e em C++ o
// canal idiomatico e a excecao. Este nao constroi arvore nenhuma: e um leitor
// PULL. Quem chama diz o que espera encontrar, na ordem, e cada metodo
// devolve `bool`.
//
// O erro e PEGAJOSO (um `erro_` interno): no primeiro problema ele registra a
// mensagem e a posicao, e todas as chamadas seguintes falham sem fazer nada.
// Isso e o que torna seguro escrever a leitura em linha reta -- nao e preciso
// conferir cada chamada, basta conferir `erro()` no fim. E e o que uma
// excecao faria, com a diferenca de que aqui o desenrolamento e explicito.
//
// Nenhuma alocacao: o leitor trabalha sobre um buffer que o chamador possui.
// Nenhum `virtual`, nenhum `dynamic_cast`: `-fno-rtti` nao incomoda.
//
// ── O QUE ELE NAO FAZ ─────────────────────────────────────────────────
//
// Nao e um parser de JSON de uso geral, e nao deve ser confundido com um:
//
//   * numeros saem sempre como `double` (via `strtod`), inclusive inteiros;
//   * `\uXXXX` em string vira '?' -- as chaves do dourado sao ASCII, e os
//     valores de texto (`descricao`, `nota`) o teste nao le;
//   * profundidade maxima 8, suficiente para o dourado (4) com folga;
//   * nao valida o que pula: `pular_valor` confere delimitadores, nao
//     gramatica interna.
//
// Essas limitacoes estao aqui escritas em vez de descobertas depois. O teste
// compensa a ultima delas da unica forma honesta: ele CONFERE QUANTIDADES
// (5 casos, 960 amostras, 3 eixos, 6 features + g) em vez de confiar que leu
// o que queria. Um leitor silenciosamente errado que devolvesse menos
// amostras faria a paridade passar sobre dado pela metade -- e e por isso que
// as contagens sao assercao, nao informacao.

#ifndef DORMIO_TESTES_LEITOR_JSON_H
#define DORMIO_TESTES_LEITOR_JSON_H

#include <stdint.h>

namespace dormio {
namespace testes {

// Le um arquivo inteiro para memoria, com NUL no fim. Devolve 0 em falha.
// O chamador libera com `liberar_arquivo`.
//
// So existe no lado de teste: no host o arquivo tem 437 KB e cabe de sobra, e
// e o jeito mais simples de dar ao leitor um buffer continuo.
char *ler_arquivo_inteiro(const char *caminho, uint32_t *tamanho);
void liberar_arquivo(char *conteudo);

class LeitorJson {
 public:
  // `texto` precisa sobreviver ao leitor e terminar em NUL.
  LeitorJson(const char *texto);

  bool erro() const { return erro_; }
  const char *mensagem() const { return mensagem_; }
  uint32_t posicao() const { return posicao_do_erro_; }

  // Registra um erro de quem CHAMA (ex.: "esperava a chave 'casos'"), para
  // que a mensagem final descreva a expectativa violada e nao so a sintaxe.
  void falhar(const char *mensagem);

  // ── Objetos ──
  // Consome '{'.
  bool entrar_objeto();
  // Le a proxima chave para `destino`. Devolve false quando o objeto acabou
  // (e consome o '}') ou em erro -- distinga pelo `erro()`.
  bool proxima_chave(char *destino, uint32_t tamanho);

  // ── Arranjos ──
  // Consome '['.
  bool entrar_array();
  // Devolve true se ha proximo elemento (consumindo a ',' quando preciso).
  // Devolve false quando o arranjo acabou (consumindo o ']') ou em erro.
  bool proximo_elemento();

  // ── Valores ──
  bool ler_numero(double *saida);
  bool ler_string(char *destino, uint32_t tamanho);
  bool ler_booleano(bool *saida);
  // Pula o valor corrente, qualquer que seja o tipo.
  bool pular_valor();

  // Conveniencia para o padrao mais comum do dourado: um arranjo de numeros
  // de tamanho conhecido. Confere a QUANTIDADE, que e o ponto -- ver a nota
  // sobre contagens no topo deste arquivo.
  bool ler_array_de_numeros(double *destino, uint32_t esperados);

 private:
  void pular_espaco();
  bool exigir(char c, const char *contexto);
  char olhar();
  bool pular_bruto(uint32_t profundidade);
  bool pular_string_bruta();

  const char *texto_;
  uint32_t i_;
  bool erro_;
  const char *mensagem_;
  uint32_t posicao_do_erro_;

  // Pilha de contexto: para cada objeto/arranjo aberto, se o proximo item e o
  // primeiro (e portanto nao vem precedido de ','). Sem isso o leitor nao
  // sabe quando exigir a virgula, e aceitar virgula opcional deixaria passar
  // `[1,,2]` -- um JSON invalido que, num arquivo de referencia, seria
  // justamente o tipo de corrupcao que se quer ver.
  struct Nivel {
    bool objeto;
    bool primeiro;
  };
  static const uint32_t PROFUNDIDADE_MAXIMA = 8;
  Nivel pilha_[PROFUNDIDADE_MAXIMA];
  uint32_t profundidade_;
};

// Autoteste do proprio leitor, sobre JSON pequeno escrito a mao.
//
// ⚠️ ISTO NAO E ZELO EXCESSIVO, E A CONDICAO PARA O RESTO VALER. O alvo de
// paridade usa este leitor como regua; uma regua torta faria a paridade
// passar ou falhar por motivo nenhum, e o diagnostico apontaria para o
// filtro. Entao o leitor e testado ANTES, inclusive nos casos em que ele deve
// RECUSAR -- um leitor que aceita JSON malformado nao avisa quando o dourado
// corrompe.
//
// Devolve o numero de falhas.
int autotestar_leitor_json();

}  // namespace testes
}  // namespace dormio

#endif  // DORMIO_TESTES_LEITOR_JSON_H
