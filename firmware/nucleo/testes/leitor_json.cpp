#include "leitor_json.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

namespace dormio {
namespace testes {

// ── Leitura do arquivo ────────────────────────────────────────────────

char *ler_arquivo_inteiro(const char *caminho, uint32_t *tamanho) {
  if (tamanho) *tamanho = 0;
  FILE *f = fopen(caminho, "rb");
  if (f == 0) return 0;
  if (fseek(f, 0, SEEK_END) != 0) {
    fclose(f);
    return 0;
  }
  long n = ftell(f);
  if (n < 0) {
    fclose(f);
    return 0;
  }
  rewind(f);
  char *buf = static_cast<char *>(malloc(static_cast<size_t>(n) + 1u));
  if (buf == 0) {
    fclose(f);
    return 0;
  }
  size_t lidos = fread(buf, 1, static_cast<size_t>(n), f);
  fclose(f);
  buf[lidos] = '\0';
  if (tamanho) *tamanho = static_cast<uint32_t>(lidos);
  return buf;
}

void liberar_arquivo(char *conteudo) { free(conteudo); }

// ── Leitor ────────────────────────────────────────────────────────────

LeitorJson::LeitorJson(const char *texto)
    : texto_(texto), i_(0), erro_(false), mensagem_(""), posicao_do_erro_(0),
      profundidade_(0) {
  if (texto_ == 0) {
    texto_ = "";
    falhar("texto nulo");
  }
}

void LeitorJson::falhar(const char *mensagem) {
  // Primeiro erro vence. Os seguintes sao consequencia dele, e sobrescrever a
  // mensagem trocaria a causa pelo sintoma -- o leitor erraria na posicao 12 e
  // reportaria a posicao 400 000.
  if (erro_) return;
  erro_ = true;
  mensagem_ = mensagem;
  posicao_do_erro_ = i_;
}

void LeitorJson::pular_espaco() {
  while (texto_[i_] == ' ' || texto_[i_] == '\t' || texto_[i_] == '\n' ||
         texto_[i_] == '\r') {
    i_++;
  }
}

char LeitorJson::olhar() {
  pular_espaco();
  return texto_[i_];
}

bool LeitorJson::exigir(char c, const char *contexto) {
  if (erro_) return false;
  pular_espaco();
  if (texto_[i_] != c) {
    falhar(contexto);
    return false;
  }
  i_++;
  return true;
}

bool LeitorJson::entrar_objeto() {
  if (erro_) return false;
  if (profundidade_ >= PROFUNDIDADE_MAXIMA) {
    falhar("profundidade maxima excedida ao entrar em objeto");
    return false;
  }
  if (!exigir('{', "esperava '{' para abrir objeto")) return false;
  pilha_[profundidade_].objeto = true;
  pilha_[profundidade_].primeiro = true;
  profundidade_++;
  return true;
}

bool LeitorJson::entrar_array() {
  if (erro_) return false;
  if (profundidade_ >= PROFUNDIDADE_MAXIMA) {
    falhar("profundidade maxima excedida ao entrar em arranjo");
    return false;
  }
  if (!exigir('[', "esperava '[' para abrir arranjo")) return false;
  pilha_[profundidade_].objeto = false;
  pilha_[profundidade_].primeiro = true;
  profundidade_++;
  return true;
}

bool LeitorJson::proxima_chave(char *destino, uint32_t tamanho) {
  if (erro_) return false;
  if (profundidade_ == 0 || !pilha_[profundidade_ - 1].objeto) {
    falhar("proxima_chave fora de um objeto");
    return false;
  }
  pular_espaco();
  if (texto_[i_] == '}') {
    i_++;
    profundidade_--;
    return false;  // fim do objeto: nao e erro
  }
  if (!pilha_[profundidade_ - 1].primeiro) {
    if (!exigir(',', "esperava ',' entre membros do objeto")) return false;
    pular_espaco();
  }
  pilha_[profundidade_ - 1].primeiro = false;
  if (!ler_string(destino, tamanho)) return false;
  if (!exigir(':', "esperava ':' depois da chave")) return false;
  return true;
}

bool LeitorJson::proximo_elemento() {
  if (erro_) return false;
  if (profundidade_ == 0 || pilha_[profundidade_ - 1].objeto) {
    falhar("proximo_elemento fora de um arranjo");
    return false;
  }
  pular_espaco();
  if (texto_[i_] == ']') {
    i_++;
    profundidade_--;
    return false;  // fim do arranjo: nao e erro
  }
  if (!pilha_[profundidade_ - 1].primeiro) {
    if (!exigir(',', "esperava ',' entre elementos do arranjo")) return false;
  }
  pilha_[profundidade_ - 1].primeiro = false;
  return true;
}

bool LeitorJson::ler_numero(double *saida) {
  if (erro_) return false;
  pular_espaco();
  const char *inicio = texto_ + i_;
  char *fim = 0;
  // `strtod` e o caminho certo aqui, e nao uma conversao escrita a mao: ele e
  // o MESMO procedimento de arredondamento que o `json` do Python usa para
  // transformar o texto do arquivo em float64. Uma conversao propria erraria
  // no ultimo bit, e o ultimo bit importa -- o `enmo_media` e conferido com
  // tolerancia 1e-7 g sobre valores de ~6e-3 g, e o teste de borda do
  // `arccos` do projeto ja mostrou que 1 ulp vira 6e-7 grau num angulo.
  double v = strtod(inicio, &fim);
  if (fim == inicio) {
    falhar("esperava um numero");
    return false;
  }
  i_ += static_cast<uint32_t>(fim - inicio);
  if (saida) *saida = v;
  return true;
}

bool LeitorJson::ler_booleano(bool *saida) {
  if (erro_) return false;
  pular_espaco();
  if (strncmp(texto_ + i_, "true", 4) == 0) {
    i_ += 4;
    if (saida) *saida = true;
    return true;
  }
  if (strncmp(texto_ + i_, "false", 5) == 0) {
    i_ += 5;
    if (saida) *saida = false;
    return true;
  }
  falhar("esperava true ou false");
  return false;
}

bool LeitorJson::ler_string(char *destino, uint32_t tamanho) {
  if (erro_) return false;
  if (destino == 0 || tamanho == 0) {
    falhar("destino de string invalido");
    return false;
  }
  if (!exigir('"', "esperava '\"' para abrir string")) return false;

  uint32_t escritos = 0;
  while (texto_[i_] != '\0' && texto_[i_] != '"') {
    char c = texto_[i_];
    if (c == '\\') {
      i_++;
      char e = texto_[i_];
      switch (e) {
        case 'n': c = '\n'; break;
        case 't': c = '\t'; break;
        case 'r': c = '\r'; break;
        case 'b': c = '\b'; break;
        case 'f': c = '\f'; break;
        case '"': c = '"'; break;
        case '\\': c = '\\'; break;
        case '/': c = '/'; break;
        case 'u':
          // ⚠️ `\uXXXX` NAO e decodificado: vira '?'. O dourado tem acentos em
          // `descricao` e `nota` (o Python grava com `ensure_ascii=True`), e
          // nenhum deles e lido pelo teste. Decodificar UTF-16 com pares
          // substitutos seria codigo nao exercitado -- e codigo nao
          // exercitado num instrumento de medicao e pior que uma limitacao
          // declarada. As CHAVES, que sao o que o teste compara, sao ASCII.
          if (texto_[i_ + 1] == '\0' || texto_[i_ + 2] == '\0' ||
              texto_[i_ + 3] == '\0' || texto_[i_ + 4] == '\0') {
            falhar("escape \\u truncado");
            return false;
          }
          i_ += 4;
          c = '?';
          break;
        case '\0':
          falhar("escape truncado no fim do texto");
          return false;
        default:
          falhar("escape desconhecido em string");
          return false;
      }
    }
    if (escritos + 1u < tamanho) {
      destino[escritos] = c;
      escritos++;
    } else {
      // Truncar em silencio faria duas chaves longas e diferentes virarem a
      // mesma -- e o teste compara chaves por igualdade.
      falhar("string nao cabe no destino");
      return false;
    }
    i_++;
  }
  if (texto_[i_] != '"') {
    falhar("string sem fechamento");
    return false;
  }
  i_++;
  destino[escritos] = '\0';
  return true;
}

bool LeitorJson::pular_string_bruta() {
  if (!exigir('"', "esperava '\"' ao pular string")) return false;
  while (texto_[i_] != '\0' && texto_[i_] != '"') {
    if (texto_[i_] == '\\') {
      i_++;
      if (texto_[i_] == '\0') {
        falhar("escape truncado ao pular string");
        return false;
      }
    }
    i_++;
  }
  if (texto_[i_] != '"') {
    falhar("string sem fechamento ao pular");
    return false;
  }
  i_++;
  return true;
}

// Pulo bruto, com recursao limitada. NAO usa a pilha publica de proposito:
// pular um valor nao pode mexer no contexto de quem esta lendo em volta.
bool LeitorJson::pular_bruto(uint32_t profundidade) {
  if (erro_) return false;
  if (profundidade > 32u) {
    falhar("aninhamento profundo demais ao pular valor");
    return false;
  }
  pular_espaco();
  char c = texto_[i_];
  if (c == '{' || c == '[') {
    const char fecha = (c == '{') ? '}' : ']';
    i_++;
    pular_espaco();
    if (texto_[i_] == fecha) {
      i_++;
      return true;
    }
    for (;;) {
      pular_espaco();
      if (c == '{') {
        if (!pular_string_bruta()) return false;
        if (!exigir(':', "esperava ':' ao pular membro de objeto")) return false;
      }
      if (!pular_bruto(profundidade + 1u)) return false;
      pular_espaco();
      if (texto_[i_] == ',') {
        i_++;
        continue;
      }
      if (texto_[i_] == fecha) {
        i_++;
        return true;
      }
      falhar("delimitador inesperado ao pular valor composto");
      return false;
    }
  }
  if (c == '"') return pular_string_bruta();
  if (strncmp(texto_ + i_, "null", 4) == 0) {
    i_ += 4;
    return true;
  }
  if (strncmp(texto_ + i_, "true", 4) == 0) {
    i_ += 4;
    return true;
  }
  if (strncmp(texto_ + i_, "false", 5) == 0) {
    i_ += 5;
    return true;
  }
  return ler_numero(0);
}

bool LeitorJson::pular_valor() { return pular_bruto(0); }

bool LeitorJson::ler_array_de_numeros(double *destino, uint32_t esperados) {
  if (!entrar_array()) return false;
  uint32_t lidos = 0;
  while (proximo_elemento()) {
    double v = 0.0;
    if (!ler_numero(&v)) return false;
    if (lidos < esperados && destino) destino[lidos] = v;
    lidos++;
  }
  if (erro_) return false;
  if (lidos != esperados) {
    // A assercao que faz o resto valer. Ver a nota sobre contagens no .h.
    falhar("arranjo de numeros com quantidade diferente da esperada");
    return false;
  }
  return true;
}

// ── Autoteste ─────────────────────────────────────────────────────────

static int falhas_autoteste = 0;

static void conferir(bool condicao, const char *o_que) {
  if (!condicao) {
    falhas_autoteste++;
    printf("  FALHOU (leitor_json)  %s\n", o_que);
  }
}

int autotestar_leitor_json() {
  falhas_autoteste = 0;

  // 1. Objeto simples, chaves na ordem, numero e string.
  {
    LeitorJson l("{\"a\": 1.5, \"b\": \"xy\", \"c\": [1, 2, 3]}");
    char chave[32];
    double v = 0.0;
    conferir(l.entrar_objeto(), "entra em objeto simples");
    conferir(l.proxima_chave(chave, sizeof(chave)) && strcmp(chave, "a") == 0,
             "primeira chave e 'a'");
    conferir(l.ler_numero(&v) && v == 1.5, "le 1.5");
    char s[8];
    conferir(l.proxima_chave(chave, sizeof(chave)) && strcmp(chave, "b") == 0,
             "segunda chave e 'b'");
    conferir(l.ler_string(s, sizeof(s)) && strcmp(s, "xy") == 0, "le \"xy\"");
    conferir(l.proxima_chave(chave, sizeof(chave)) && strcmp(chave, "c") == 0,
             "terceira chave e 'c'");
    double tres[3] = {0, 0, 0};
    conferir(l.ler_array_de_numeros(tres, 3), "le arranjo de 3");
    conferir(tres[0] == 1 && tres[1] == 2 && tres[2] == 3, "valores do arranjo");
    conferir(!l.proxima_chave(chave, sizeof(chave)), "objeto termina");
    conferir(!l.erro(), "nenhum erro no caso simples");
  }

  // 2. Notacao cientifica e sinal -- o dourado tem valores como 1e-07.
  {
    LeitorJson l("[1e-07, -2.5E+3, 0.0]");
    double v[3] = {0, 0, 0};
    conferir(l.ler_array_de_numeros(v, 3), "le arranjo cientifico");
    conferir(v[0] == 1e-07, "le 1e-07");
    conferir(v[1] == -2500.0, "le -2.5E+3");
    conferir(v[2] == 0.0, "le 0.0");
  }

  // 3. `pular_valor` atravessa estrutura aninhada sem perder o lugar.
  {
    LeitorJson l("{\"lixo\": {\"a\": [1, {\"b\": 2}], \"c\": \"x\"}, \"alvo\": 7}");
    char chave[32];
    double v = 0.0;
    conferir(l.entrar_objeto(), "entra");
    conferir(l.proxima_chave(chave, sizeof(chave)) && strcmp(chave, "lixo") == 0,
             "acha 'lixo'");
    conferir(l.pular_valor(), "pula objeto aninhado");
    conferir(l.proxima_chave(chave, sizeof(chave)) && strcmp(chave, "alvo") == 0,
             "acha 'alvo' depois do pulo");
    conferir(l.ler_numero(&v) && v == 7.0, "le 7 depois do pulo");
    conferir(!l.erro(), "pulo nao deixou erro");
  }

  // 4. Escapes, inclusive `\u` virando '?'.
  {
    LeitorJson l("[\"a\\\"b\", \"c\\u00e3o\"]");
    char s[16];
    conferir(l.entrar_array(), "entra no arranjo de strings");
    conferir(l.proximo_elemento() && l.ler_string(s, sizeof(s)), "le 1a string");
    conferir(strcmp(s, "a\"b") == 0, "escape de aspas");
    conferir(l.proximo_elemento() && l.ler_string(s, sizeof(s)), "le 2a string");
    conferir(strcmp(s, "c?o") == 0, "escape \\u vira '?'");
    conferir(!l.proximo_elemento(), "arranjo de strings termina");
    conferir(!l.erro(), "escapes sem erro");
  }

  // 5. O QUE ELE TEM DE RECUSAR. Um leitor que aceita de tudo nao avisa
  //    quando o dourado corrompe -- e e para avisar que ele existe.
  {
    LeitorJson l("[1,,2]");
    double v[3];
    l.ler_array_de_numeros(v, 3);
    conferir(l.erro(), "recusa virgula dupla em arranjo");
  }
  {
    LeitorJson l("[1, 2");
    double v[2];
    l.ler_array_de_numeros(v, 2);
    conferir(l.erro(), "recusa arranjo sem fechamento");
  }
  {
    LeitorJson l("{\"a\" 1}");
    char chave[8];
    l.entrar_objeto();
    l.proxima_chave(chave, sizeof(chave));
    conferir(l.erro(), "recusa chave sem ':'");
  }
  {
    // A assercao de QUANTIDADE: tres numeros onde o teste espera dois.
    LeitorJson l("[1, 2, 3]");
    double v[2];
    conferir(!l.ler_array_de_numeros(v, 2), "recusa arranjo maior que o esperado");
    conferir(l.erro(), "e marca erro");
  }
  {
    LeitorJson l("[1]");
    double v[2];
    conferir(!l.ler_array_de_numeros(v, 2), "recusa arranjo menor que o esperado");
  }
  {
    LeitorJson l("{\"chave_muito_comprida\": 1}");
    char curto[5];
    l.entrar_objeto();
    l.proxima_chave(curto, sizeof(curto));
    conferir(l.erro(), "recusa chave que nao cabe, em vez de truncar");
  }
  {
    // Erro PEGAJOSO: depois do primeiro, nada mais acontece, e a mensagem
    // continua sendo a da causa.
    LeitorJson l("{\"a\" 1}");
    char chave[8];
    l.entrar_objeto();
    l.proxima_chave(chave, sizeof(chave));
    const char *primeira = l.mensagem();
    double v = 0.0;
    conferir(!l.ler_numero(&v), "operacao apos erro falha");
    conferir(l.mensagem() == primeira, "mensagem do primeiro erro sobrevive");
  }

  return falhas_autoteste;
}

}  // namespace testes
}  // namespace dormio
