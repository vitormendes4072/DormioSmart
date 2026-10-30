#include "lote.h"

#include <string.h>

namespace dormio {

// ── O envelope ────────────────────────────────────────────────────────

static const char ABERTURA[] = "{\"leituras\":[";
static const char FECHAMENTO[] = "]}";
static const uint32_t TAMANHO_ABERTURA = sizeof(ABERTURA) - 1;
static const uint32_t TAMANHO_FECHAMENTO = sizeof(FECHAMENTO) - 1;

MontadorDeLote::MontadorDeLote(char *destino, uint32_t capacidade)
    : destino_(destino), capacidade_(capacidade), usado_(0), quantidade_(0) {
  // Abertura + fechamento + NUL tem de caber, senao o montador nasce cheio.
  if (destino_ == 0 || capacidade_ < TAMANHO_ABERTURA + TAMANHO_FECHAMENTO + 1) {
    capacidade_ = 0;
    return;
  }
  memcpy(destino_, ABERTURA, TAMANHO_ABERTURA);
  usado_ = TAMANHO_ABERTURA;
}

bool MontadorDeLote::adicionar(const char *leitura_json, uint32_t tamanho) {
  if (capacidade_ == 0 || leitura_json == 0 || tamanho == 0) return false;
  if (quantidade_ >= MAX_LEITURAS_POR_LOTE) return false;
  const uint32_t virgula = quantidade_ > 0 ? 1u : 0u;
  if (usado_ + virgula + tamanho + TAMANHO_FECHAMENTO + 1 > capacidade_) return false;
  if (virgula) destino_[usado_++] = ',';
  memcpy(destino_ + usado_, leitura_json, tamanho);
  usado_ += tamanho;
  quantidade_++;
  return true;
}

uint32_t MontadorDeLote::fechar() {
  if (capacidade_ == 0 || quantidade_ == 0) return 0;
  memcpy(destino_ + usado_, FECHAMENTO, TAMANHO_FECHAMENTO);
  usado_ += TAMANHO_FECHAMENTO;
  destino_[usado_] = '\0';
  return usado_;
}

// ── A resposta ────────────────────────────────────────────────────────
//
// Um leitor minimo, so para a forma que o servidor devolve:
//   {"aceitas":[0,1],"rejeitadas":[{"indice":2,"erro":"..."}],"pendentes":[3]}
// com chaves em qualquer ordem e chaves a mais toleradas (pulando o valor).
// Nao e o `leitor_json` dos testes de proposito: aquele aloca contexto para
// ler o dourado inteiro, e este precisa caber no firmware e so reconhecer
// inteiros, strings para pular e dois niveis de aninhamento.

namespace {

const uint32_t PROFUNDIDADE_MAXIMA = 8;

struct Leitor {
  const char *s;
  uint32_t n;
  uint32_t i;
  bool erro;

  void espaco() {
    while (i < n && (s[i] == ' ' || s[i] == '\n' || s[i] == '\r' || s[i] == '\t')) i++;
  }
  bool olhar(char c) {
    espaco();
    return i < n && s[i] == c;
  }
  bool exigir(char c) {
    espaco();
    if (i < n && s[i] == c) {
      i++;
      return true;
    }
    erro = true;
    return false;
  }
  // Uma string inteira, com escapes. Copia ate `cap - 1` bytes em `destino`
  // (pode ser 0 para so pular).
  bool string(char *destino, uint32_t cap) {
    if (!exigir('"')) return false;
    uint32_t k = 0;
    while (i < n) {
      char c = s[i++];
      if (c == '"') {
        if (destino != 0 && cap > 0) destino[k < cap ? k : cap - 1] = '\0';
        return true;
      }
      if (c == '\\') {
        if (i >= n) break;
        c = s[i++];  // o caractere escapado; \uXXXX passa como texto, basta
      }
      if (destino != 0 && k + 1 < cap) destino[k++] = c;
    }
    erro = true;
    return false;
  }
  // Inteiro nao negativo que caiba em 32 bits. Sinal, fracao ou expoente
  // tornam a resposta ilegivel: indice nao tem nenhum dos tres.
  bool inteiro(uint32_t *saida) {
    espaco();
    if (i >= n || s[i] < '0' || s[i] > '9') {
      erro = true;
      return false;
    }
    uint64_t v = 0;
    while (i < n && s[i] >= '0' && s[i] <= '9') {
      v = v * 10u + static_cast<uint64_t>(s[i] - '0');
      if (v > 0xFFFFFFFFull) {
        erro = true;
        return false;
      }
      i++;
    }
    if (i < n && (s[i] == '.' || s[i] == 'e' || s[i] == 'E')) {
      erro = true;
      return false;
    }
    *saida = static_cast<uint32_t>(v);
    return true;
  }
  bool pular(uint32_t profundidade) {
    if (profundidade > PROFUNDIDADE_MAXIMA) {
      erro = true;
      return false;
    }
    espaco();
    if (i >= n) {
      erro = true;
      return false;
    }
    const char c = s[i];
    if (c == '"') return string(0, 0);
    if (c == '{' || c == '[') {
      const char fim = (c == '{') ? '}' : ']';
      i++;
      if (olhar(fim)) {
        i++;
        return true;
      }
      for (;;) {
        if (c == '{') {
          if (!string(0, 0) || !exigir(':')) return false;
        }
        if (!pular(profundidade + 1)) return false;
        if (olhar(',')) {
          i++;
          continue;
        }
        return exigir(fim);
      }
    }
    // numero ou literal: ate o proximo delimitador
    const uint32_t inicio = i;
    while (i < n && s[i] != ',' && s[i] != '}' && s[i] != ']' && s[i] != ' ' &&
           s[i] != '\n' && s[i] != '\r' && s[i] != '\t') {
      i++;
    }
    if (i == inicio) {
      erro = true;
      return false;
    }
    return true;
  }
};

// Marca `indice` como visto. Falha se estiver fora do lote ou repetido.
bool marcar(uint32_t indice, uint32_t enviadas, uint8_t *visto) {
  if (indice >= enviadas || visto[indice]) return false;
  visto[indice] = 1;
  return true;
}

// Le `[i, j, ...]`, marcando cada um. Conta em `contador` e guarda o menor.
bool ler_lista_de_indices(Leitor &l, uint32_t enviadas, uint8_t *visto, uint32_t *contador,
                          uint32_t *menor) {
  if (!l.exigir('[')) return false;
  if (l.olhar(']')) {
    l.i++;
    return true;
  }
  for (;;) {
    uint32_t v;
    if (!l.inteiro(&v) || !marcar(v, enviadas, visto)) return false;
    (*contador)++;
    if (v < *menor) *menor = v;
    if (l.olhar(',')) {
      l.i++;
      continue;
    }
    return l.exigir(']');
  }
}

// Le `[{"indice": i, ...}, ...]`. Cada objeto tem de ter exatamente um
// `indice`; o resto (`erro`) e pulado.
bool ler_rejeitadas(Leitor &l, uint32_t enviadas, uint8_t *visto, uint32_t *contador) {
  if (!l.exigir('[')) return false;
  if (l.olhar(']')) {
    l.i++;
    return true;
  }
  for (;;) {
    if (!l.exigir('{')) return false;
    bool achou = false;
    if (!l.olhar('}')) {
      for (;;) {
        char chave[16];
        if (!l.string(chave, sizeof(chave)) || !l.exigir(':')) return false;
        if (strcmp(chave, "indice") == 0) {
          uint32_t v;
          if (achou || !l.inteiro(&v) || !marcar(v, enviadas, visto)) return false;
          achou = true;
        } else if (!l.pular(2)) {
          return false;
        }
        if (l.olhar(',')) {
          l.i++;
          continue;
        }
        break;
      }
    }
    if (!l.exigir('}') || !achou) return false;
    (*contador)++;
    if (l.olhar(',')) {
      l.i++;
      continue;
    }
    return l.exigir(']');
  }
}

}  // namespace

DecisaoDoLote interpretar_resposta_do_lote(int status_http, const char *corpo,
                                           uint32_t tamanho, uint32_t enviadas) {
  DecisaoDoLote d;
  d.acao = LOTE_RECUAR;
  d.confirmar = 0;
  d.aceitas = 0;
  d.rejeitadas = 0;
  d.pendentes = 0;
  d.recuar_depois = false;
  d.resposta_ilegivel = false;

  if (status_http == 413) {
    d.acao = LOTE_DIVIDIR;
    return d;
  }
  if (status_http != 200 && status_http != 503) return d;
  if (enviadas == 0 || enviadas > MAX_LEITURAS_POR_LOTE) {
    d.resposta_ilegivel = true;
    return d;
  }
  // 503 sem corpo (o gateway, nao o nosso servidor) e so recuar.
  if (corpo == 0 || tamanho == 0) {
    d.resposta_ilegivel = (status_http == 200);
    return d;
  }

  uint8_t visto[MAX_LEITURAS_POR_LOTE];
  memset(visto, 0, sizeof(visto));
  uint32_t aceitas = 0, rejeitadas = 0, pendentes = 0;
  uint32_t menor_aceita = enviadas, menor_pendente = enviadas;
  bool tem_aceitas = false, tem_rejeitadas = false, tem_pendentes = false;

  Leitor l = {corpo, tamanho, 0, false};
  bool ok = l.exigir('{');
  if (ok && l.olhar('}')) ok = false;  // objeto vazio nao tem as tres listas
  while (ok) {
    char chave[16];
    if (!l.string(chave, sizeof(chave)) || !l.exigir(':')) {
      ok = false;
      break;
    }
    if (strcmp(chave, "aceitas") == 0) {
      ok = !tem_aceitas && ler_lista_de_indices(l, enviadas, visto, &aceitas, &menor_aceita);
      tem_aceitas = true;
    } else if (strcmp(chave, "pendentes") == 0) {
      ok = !tem_pendentes &&
           ler_lista_de_indices(l, enviadas, visto, &pendentes, &menor_pendente);
      tem_pendentes = true;
    } else if (strcmp(chave, "rejeitadas") == 0) {
      ok = !tem_rejeitadas && ler_rejeitadas(l, enviadas, visto, &rejeitadas);
      tem_rejeitadas = true;
    } else {
      ok = l.pular(1);
    }
    if (!ok) break;
    if (l.olhar(',')) {
      l.i++;
      continue;
    }
    ok = l.exigir('}');
    break;
  }
  (void)menor_aceita;

  // Coerencia: as tres listas presentes, todo indice visto uma vez, e os
  // pendentes formando um sufixo (o menor deles e `enviadas - pendentes`).
  if (!ok || l.erro || !tem_aceitas || !tem_rejeitadas || !tem_pendentes ||
      aceitas + rejeitadas + pendentes != enviadas ||
      (pendentes > 0 && menor_pendente != enviadas - pendentes)) {
    d.resposta_ilegivel = true;
    return d;
  }

  d.aceitas = aceitas;
  d.rejeitadas = rejeitadas;
  d.pendentes = pendentes;
  d.confirmar = enviadas - pendentes;
  d.recuar_depois = pendentes > 0;
  d.acao = d.confirmar > 0 ? LOTE_CONFIRMAR : LOTE_RECUAR;
  return d;
}

}  // namespace dormio
