#include "payload.h"

#include <stdio.h>

namespace dormio {

// Algoritmo de dias civis (Howard Hinnant, dominio publico): converte dias
// desde 1970-01-01 em (ano, mes, dia) sem tabela de meses e sem caso especial
// de bissexto -- ele desloca o ano para comecar em marco, e ai a duracao dos
// meses vira uma progressao regular.
static void civil_de_dias(int64_t z, int32_t *ano, uint32_t *mes, uint32_t *dia) {
  z += 719468;
  const int64_t era = (z >= 0 ? z : z - 146096) / 146097;
  const uint64_t doe = static_cast<uint64_t>(z - era * 146097);            // [0, 146096]
  const uint64_t yoe = (doe - doe / 1460 + doe / 36524 - doe / 146096) / 365;
  const int64_t y = static_cast<int64_t>(yoe) + era * 400;
  const uint64_t doy = doe - (365 * yoe + yoe / 4 - yoe / 100);            // [0, 365]
  const uint64_t mp = (5 * doy + 2) / 153;                                  // [0, 11]
  const uint64_t d = doy - (153 * mp + 2) / 5 + 1;                          // [1, 31]
  const uint64_t m = mp < 10 ? mp + 3 : mp - 9;                             // [1, 12]
  *ano = static_cast<int32_t>(y + (m <= 2 ? 1 : 0));
  *mes = static_cast<uint32_t>(m);
  *dia = static_cast<uint32_t>(d);
}

uint32_t formatar_iso8601_utc(int64_t unix_ms, char *destino, uint32_t tamanho) {
  if (destino == 0 || tamanho < 25) return 0;

  // Divisao que arredonda para BAIXO tambem em datas anteriores a 1970 -- a
  // divisao de C trunca em direcao a zero, o que daria o dia errado para
  // negativos. Nao deveria ocorrer com relogio sincronizado, mas um relogio
  // nao sincronizado e justamente o cenario que este modulo trata.
  int64_t segundos = unix_ms / 1000;
  int64_t ms = unix_ms % 1000;
  if (ms < 0) {
    ms += 1000;
    segundos -= 1;
  }

  int64_t dias = segundos / 86400;
  int64_t resto = segundos % 86400;
  if (resto < 0) {
    resto += 86400;
    dias -= 1;
  }

  int32_t ano;
  uint32_t mes, dia;
  civil_de_dias(dias, &ano, &mes, &dia);

  int hora = static_cast<int>(resto / 3600);
  int minuto = static_cast<int>((resto % 3600) / 60);
  int segundo = static_cast<int>(resto % 60);

  int n = snprintf(destino, tamanho, "%04d-%02u-%02uT%02d:%02d:%02d.%03dZ",
                   static_cast<int>(ano), mes, dia, hora, minuto, segundo,
                   static_cast<int>(ms));
  if (n < 0 || static_cast<uint32_t>(n) >= tamanho) return 0;
  return static_cast<uint32_t>(n);
}

ResultadoDeMontagem montar_payload(const Epoca &e, const ResolucaoDeParede &parede,
                                   uint64_t mono_do_inicio_da_epoca_ms, char *destino,
                                   uint32_t tamanho, uint32_t *escritos) {
  if (escritos) *escritos = 0;
  if (destino == 0 || tamanho < 64) return PAYLOAD_BUFFER_PEQUENO;

  if (e.vazia()) return PAYLOAD_EPOCA_VAZIA;
  if (!magnitude_plausivel(e.pico_total)) return PAYLOAD_MAGNITUDE_IMPLAUSIVEL;
  if (e.duracao_s > DURACAO_MAXIMA_S || e.duracao_s < 1) return PAYLOAD_EPOCA_LONGA_DEMAIS;

  char ts[32];
  bool tem_ts = false;
  if (parede.valida) {
    tem_ts = formatar_iso8601_utc(parede.resolver(mono_do_inicio_da_epoca_ms), ts,
                                  sizeof(ts)) > 0;
  }

  // Duas casas decimais, como o contrato descreve. A tolerancia de coerencia
  // do backend e 0,5 m/s^2, entao o arredondamento nao chega perto de
  // incomodar. `amostras` precisa ser >= 1 (validacao do backend), e como so
  // chegamos aqui com a epoca nao-vazia, e.
  uint32_t amostras = e.amostras < 1 ? 1 : e.amostras;

  int n;
  if (tem_ts) {
    n = snprintf(destino, tamanho,
                 "{\"ax\":%.2f,\"ay\":%.2f,\"az\":%.2f,\"t\":%.1f,\"total\":%.2f,"
                 "\"status\":\"%s\",\"ts\":\"%s\",\"epoca_s\":%u,\"metodo\":\"%s\","
                 "\"amostras\":%u}",
                 e.pico_ax, e.pico_ay, e.pico_az, e.temp_pico, e.pico_total,
                 classificar(e.pico_total), ts,
                 static_cast<unsigned>(e.duracao_s), METODO_AGREGACAO,
                 static_cast<unsigned>(amostras));
  } else {
    n = snprintf(destino, tamanho,
                 "{\"ax\":%.2f,\"ay\":%.2f,\"az\":%.2f,\"t\":%.1f,\"total\":%.2f,"
                 "\"status\":\"%s\",\"epoca_s\":%u,\"metodo\":\"%s\","
                 "\"amostras\":%u}",
                 e.pico_ax, e.pico_ay, e.pico_az, e.temp_pico, e.pico_total,
                 classificar(e.pico_total),
                 static_cast<unsigned>(e.duracao_s), METODO_AGREGACAO,
                 static_cast<unsigned>(amostras));
  }

  if (n < 0 || static_cast<uint32_t>(n) >= tamanho) return PAYLOAD_BUFFER_PEQUENO;
  if (escritos) *escritos = static_cast<uint32_t>(n);
  return PAYLOAD_OK;
}

}  // namespace dormio
