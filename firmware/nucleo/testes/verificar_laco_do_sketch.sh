#!/bin/sh
# verificar_laco_do_sketch.sh -- roda o laco REAL do sketch.ino com relogio
# falso, e sabota o sketch para conferir que o teste acusa (FW-10).
#
# Os stubs de `stubs-arduino/` sao so para compilar: devolvem 0 e nao fazem
# nada. Aqui uma copia deles ganha um relogio controlavel (`esp_timer`, sono
# leve, `vTaskDelay`) e um gancho na leitura I2C, que e onde o teste injeta o
# trabalho de cada volta. A troca de cada trecho tem de casar EXATAMENTE uma
# vez: um stub que mudou por baixo faz este script parar, em vez de testar o
# relogio errado em silencio.
set -u

AQUI=$(cd "$(dirname "$0")" && pwd)
NUCLEO=$(cd "$AQUI/.." && pwd)
FIRMWARE=$(cd "$NUCLEO/.." && pwd)
CXX=${CXX:-g++}
W=$(mktemp -d)
trap 'rm -rf "$W"' EXIT

troca() { # troca ARQUIVO DE PARA -- falha se DE nao casar exatamente uma vez
  DE="$2" PARA="$3" python3 -c '
import os, sys
p = sys.argv[1]
s = open(p).read().replace("\r\n", "\n")
n = s.count(os.environ["DE"])
if n != 1:
    sys.exit("TROCA QUEBRADA: casou %d vezes em %s" % (n, p))
open(p, "w").write(s.replace(os.environ["DE"], os.environ["PARA"]))
' "$1" || exit 2
}

cp -r "$AQUI/stubs-arduino" "$W/stubs"
troca "$W/stubs/esp_timer.h" "inline int64_t esp_timer_get_time() { return 0; }" \
  "int64_t esp_timer_get_time();"
troca "$W/stubs/esp_sleep.h" "inline int esp_sleep_enable_timer_wakeup(uint64_t) { return 0; }" \
  "int esp_sleep_enable_timer_wakeup(uint64_t);"
troca "$W/stubs/esp_sleep.h" "inline int esp_light_sleep_start() { return 0; }" \
  "int esp_light_sleep_start();"
troca "$W/stubs/freertos/task.h" "inline void vTaskDelay(const TickType_t) {}" \
  "void vTaskDelay(const TickType_t);"
troca "$W/stubs/Arduino.h" "class WireStub {" "void gancho_i2c();
class WireStub {"
# O gancho marca uma drenagem na leitura do INT_STATUS (0x3A), a primeira de
# cada uma: desde o FW-17 (etapa 2), o sketch tambem le o sensor quando libera
# o barramento, e essa leitura nao e uma volta do laco.
troca "$W/stubs/Arduino.h" "  size_t write(uint8_t) { return 1; }" \
  "  uint8_t reg_ = 0;
  size_t write(uint8_t v) { reg_ = v; return 1; }"
troca "$W/stubs/Arduino.h" "  uint8_t requestFrom(uint8_t, size_t) { return 0; }" \
  "  uint8_t requestFrom(uint8_t, size_t) { if (reg_ == 0x3A) gancho_i2c(); return 0; }"
printf '#define WIFI_SSID "x"\n#define WIFI_PASSWORD "y"\n#define DEVICE_TOKEN "z"\n' > "$W/stubs/secrets.h"

$CXX -std=c++11 -w -c -I"$W/stubs" "$FIRMWARE/nucleo_amalgama.cpp" -o "$W/amalgama.o" || exit 2
$CXX -std=c++11 -w -c -I"$W/stubs" "$W/stubs/stubs.cpp" -o "$W/stubs.o" || exit 2

# rodar SKETCH -> 0 se o teste passou, 1 se acusou, 2 se nao compilou
rodar() {
  $CXX -std=c++11 -w -x c++ -I"$W/stubs" -I"$FIRMWARE" -include Arduino.h \
    -DSKETCH="\"$1\"" "$AQUI/laco_do_sketch.cpp" -x none "$W/amalgama.o" "$W/stubs.o" \
    -o "$W/laco" 2>"$W/erro" || { cat "$W/erro"; return 2; }
  "$W/laco" >"$W/saida" 2>&1
}

rodar "$FIRMWARE/sketch.ino"
r=$?
grep -v '^\[' "$W/saida"
if [ $r -ne 0 ]; then
  echo "FALHOU -- o laco do sketch.ino nao se comporta como o nucleo promete."
  exit 1
fi

echo
echo "Sabotadores do LACO DO SKETCH -- o teste tem de acusar:"
falhas=0
total=0
sabotar() { # sabotar ROTULO DE PARA
  total=$((total + 1))
  cp "$FIRMWARE/sketch.ino" "$W/sabotado.ino"
  troca "$W/sabotado.ino" "$2" "$3"
  rodar "$W/sabotado.ino"
  r=$?
  n=$(grep -c "FALHA" "$W/saida")
  if [ $r -eq 1 ]; then
    printf '  %-48s acusou (%s falhas)\n' "$1" "$n"
  else
    printf '  %-48s NAO ACUSOU (saida %s)\n' "$1" "$r"
    falhas=$((falhas + 1))
  fi
}

sabotar "1. sono relativo (o defeito de ate 03/11)" \
  "    prazo_us = proximo_prazo_de_drenagem_us(prazo_us, agora_us, intervalo_de_drenagem_us(&xorshift));" \
  "    prazo_us = agora_us + intervalo_de_drenagem_us(&xorshift);"
sabotar "2. estouro do prazo nao contado" \
  "      contadores.prazos_estourados++;  // drena ja, sem dormir" \
  "      // drena ja, sem dormir"
sabotar "3. trabalho medido depois da drenagem" \
  "    const uint64_t inicio_us = static_cast<uint64_t>(esp_timer_get_time());
    drenar();" \
  "    drenar();
    const uint64_t inicio_us = static_cast<uint64_t>(esp_timer_get_time());"
sabotar "4. deriva medida depois de sincronizar" \
  "      deriva_no_intervalo = medir_deriva(parede, mono_ms, unix_ms);
      parede.sincronizar(mono_ms, unix_ms);" \
  "      parede.sincronizar(mono_ms, unix_ms);
      deriva_no_intervalo = medir_deriva(parede, mono_ms, unix_ms);"


# ── FW-11: o sketch contra um MPU6050 falso (`sensor_do_sketch.cpp`) ─────
# Outra copia dos stubs: o relogio vem do teste, e o `Wire` chama o sensor de
# mentira em vez de devolver "nada".
echo
echo "O sketch contra um MPU6050 falso (FW-11):"
cp -r "$AQUI/stubs-arduino" "$W/stubs-sensor"
troca "$W/stubs-sensor/esp_timer.h" "inline int64_t esp_timer_get_time() { return 0; }" \
  "int64_t esp_timer_get_time();"
troca "$W/stubs-sensor/esp_sleep.h" "inline int esp_sleep_enable_timer_wakeup(uint64_t) { return 0; }" \
  "int esp_sleep_enable_timer_wakeup(uint64_t);"
troca "$W/stubs-sensor/esp_sleep.h" "inline int esp_light_sleep_start() { return 0; }" \
  "int esp_light_sleep_start();"
troca "$W/stubs-sensor/freertos/task.h" "inline void vTaskDelay(const TickType_t) {}" \
  "void vTaskDelay(const TickType_t);"
python3 - "$W/stubs-sensor/Arduino.h" <<'PYSTUB' || exit 2
import sys
p = sys.argv[1]
s = open(p).read().replace("\r\n", "\n")
i = s.find("class WireStub {")
j = s.find("extern WireStub Wire;")
if i < 0 or j < 0 or s.count("class WireStub {") != 1:
    sys.exit("TROCA QUEBRADA: a classe WireStub mudou")
novo = """void wire_begin_tx(uint8_t);
void wire_write(uint8_t);
uint8_t wire_end_tx();
uint8_t wire_request(size_t);
int wire_read();
class WireStub {
 public:
  void begin(int, int) {}
  bool end() { return true; }
  void setClock(uint32_t) {}
  void beginTransmission(uint8_t a) { wire_begin_tx(a); }
  uint8_t endTransmission() { return wire_end_tx(); }
  uint8_t endTransmission(bool) { return wire_end_tx(); }
  size_t write(uint8_t v) { wire_write(v); return 1; }
  uint8_t requestFrom(uint8_t, size_t n) { return wire_request(n); }
  uint8_t requestFrom(uint8_t, size_t n, bool) { return wire_request(n); }
  int available() { return 1; }
  int read() { return wire_read(); }
};
"""
open(p, "w").write(s[:i] + novo + s[j:])
PYSTUB
# FW-17, etapa 2: os pinos tambem vao para o sensor falso (a liberacao do
# barramento mexe no SDA e no SCL na mao).
troca "$W/stubs-sensor/Arduino.h" "inline void pinMode(int, int) {}
inline int digitalRead(int) { return 0; }
inline void digitalWrite(int, int) {}" "void pinMode(int, int);
int digitalRead(int);
void digitalWrite(int, int);"
cp "$W/stubs/secrets.h" "$W/stubs-sensor/secrets.h"
$CXX -std=c++11 -w -c -I"$W/stubs-sensor" "$FIRMWARE/nucleo_amalgama.cpp" -o "$W/amalgama-sensor.o" || exit 2
$CXX -std=c++11 -w -c -I"$W/stubs-sensor" "$W/stubs-sensor/stubs.cpp" -o "$W/stubs-sensor.o" || exit 2

rodar_sensor() { # rodar_sensor SKETCH -> 0 passou, 1 acusou, 2 nao compilou
  $CXX -std=c++11 -w -x c++ -I"$W/stubs-sensor" -I"$FIRMWARE" -include Arduino.h \
    -DSKETCH="\"$1\"" "$AQUI/sensor_do_sketch.cpp" -x none "$W/amalgama-sensor.o" \
    "$W/stubs-sensor.o" -o "$W/sensor" 2>"$W/erro" || { cat "$W/erro"; return 2; }
  "$W/sensor" >"$W/saida" 2>&1
}

rodar_sensor "$FIRMWARE/sketch.ino"
r=$?
grep -v '^\[\|^Calibracao' "$W/saida"
if [ $r -ne 0 ]; then
  echo "FALHOU -- o sketch.ino nao calibra ou nao reacorda o sensor como o FW-11 promete."
  exit 1
fi

echo
echo "Sabotadores do SENSOR NO SKETCH -- o teste tem de acusar:"
sabotar_sensor() { # sabotar_sensor ROTULO DE PARA
  total=$((total + 1))
  cp "$FIRMWARE/sketch.ino" "$W/sabotado.ino"
  troca "$W/sabotado.ino" "$2" "$3"
  rodar_sensor "$W/sabotado.ino"
  r=$?
  n=$(grep -c "FALHA" "$W/saida")
  if [ $r -eq 1 ]; then
    printf '  %-48s acusou (%s falhas)\n' "$1" "$n"
  else
    printf '  %-48s NAO ACUSOU (saida %s)\n' "$1" "$r"
    falhas=$((falhas + 1))
  fi
}

sabotar_sensor "5. calibracao da unidade nao aplicada" \
  "  if (n > 0) calibrar_amostras(calibracao, ler_temperatura_c(), amostras, n);" \
  "  // sem calibracao"
sabotar_sensor "6. ninguem confere o sensor" \
  "  if (vigia.observar(n)) conferir_sensor();" \
  "  vigia.observar(n);"
sabotar_sensor "7. reconfigura mesmo com o sensor acordado" \
  "  if (!sensor_precisa_reconfigurar(pwr1, user, fifo_en)) return;" \
  "  (void)sensor_precisa_reconfigurar(pwr1, user, fifo_en);"
sabotar_sensor "8. reacordar sem configurar o sensor" \
  "  const bool ok = configurar_mpu();" \
  "  const bool ok = true;"

sabotar_sensor "9. toda perda vira i2c no estado" \
  "    registrar_perda(causa_da_leitura_recusada(n_fifo, estado), t_us, n_fifo, estado);" \
  "    registrar_perda(PERDA_I2C_NO_ESTADO, t_us, n_fifo, estado);"
sabotar_sensor "10. falha nos bytes contada como no estado" \
  "      registrar_perda(PERDA_I2C_NA_LEITURA, t_us, n_fifo, estado);" \
  "      registrar_perda(PERDA_I2C_NO_ESTADO, t_us, n_fifo, estado);"
sabotar_sensor "11. a causa nao e contada" \
  "  contadores.perdas[causa]++;" \
  "  (void)causa;"
sabotar_sensor "12. o total deixa de contar" \
  "  contadores.transbordos++;
  contadores.perdas[causa]++;" \
  "  contadores.perdas[causa]++;"

sabotar_sensor "13. ninguem libera o barramento" \
  "  if (guarda.observar(false)) liberar_barramento();" \
  "  guarda.observar(false);"
sabotar_sensor "14. liberar sem os pulsos no SCL" \
  "  while (pulsos < PULSOS_PARA_LIBERAR_O_SDA && digitalRead(PINO_SDA) == LOW) {" \
  "  while (false) {"
sabotar_sensor "15. liberar sem conferir o sensor" \
  "  conferir_sensor();
  resetar_fifo();
}" \
  "  resetar_fifo();
}"
sabotar_sensor "16. a resposta nao zera a guarda" \
  "  guarda.observar(true);
" \
  ""

# ── FW-14: o envio do sketch contra um servidor falso (`envio_do_sketch.cpp`) ─
# Terceira copia dos stubs: a particao `dormio` vira RAM (o teste a define), e
# o `HTTPClient`/`WiFiClientSecure` imitam o core do ESP32 no que importa --
# com `setReuse(true)`, `end()` deixa a conexao aberta.
echo
echo "O envio do sketch contra um servidor falso (FW-14):"
cp -r "$AQUI/stubs-arduino" "$W/stubs-envio"
python3 - "$W/stubs-envio" <<'PYSTUB' || exit 2
import sys, re
d = sys.argv[1]
p = d + "/esp_partition.h"
s = open(p).read().replace("\r\n", "\n")
n = 0
for nome in ("esp_partition_find_first", "esp_partition_read", "esp_partition_write",
             "esp_partition_erase_range"):
    m = re.search(r"inline ([^\n]*?\b" + nome + r"\((?:[^()]|\n)*?\))\s*\{[^}]*\}", s)
    if not m:
        sys.exit("TROCA QUEBRADA: " + nome + " mudou no stub")
    s = s[:m.start()] + m.group(1) + ";" + s[m.end():]
    n += 1
open(p, "w").write(s)
open(d + "/WiFiClientSecure.h", "w").write("""#ifndef STUB_WCS_H
#define STUB_WCS_H
#include "Arduino.h"
void wcs_stop(bool *conectado);
class WiFiClientSecure {
 public:
  void setInsecure() {}
  void setCACert(const char *) {}
  void setTimeout(uint32_t) {}
  void stop() { wcs_stop(&conectado_); }
  uint8_t connected() { return conectado_ ? 1 : 0; }
  bool conectado_ = false;
};
#endif
""")
open(d + "/HTTPClient.h", "w").write("""#ifndef STUB_HTTP_H
#define STUB_HTTP_H
#include "Arduino.h"
#include "WiFiClientSecure.h"
int http_post(bool *conectado, const uint8_t *corpo, size_t n);
const char *http_corpo();
class HTTPClient {
 public:
  bool begin(WiFiClientSecure &c, const char *) { c_ = &c; return true; }
  bool begin(WiFiClientSecure &c, const String &) { c_ = &c; return true; }
  void addHeader(const char *, const char *) {}
  void setTimeout(uint16_t) {}
  void setReuse(bool r) { reuse_ = r; }
  int POST(const char *) { return 201; }
  int POST(const String &) { return 201; }
  int POST(uint8_t *b, size_t n) { return http_post(&c_->conectado_, b, n); }
  String getString() { return String(http_corpo()); }
  void end() { if (c_ && !reuse_) wcs_stop(&c_->conectado_); }
 private:
  WiFiClientSecure *c_ = 0;
  bool reuse_ = false;
};
#endif
""")
PYSTUB
troca "$W/stubs-envio/esp_timer.h" "inline int64_t esp_timer_get_time() { return 0; }" \
  "int64_t esp_timer_get_time();"
troca "$W/stubs-envio/esp_sleep.h" "inline int esp_sleep_enable_timer_wakeup(uint64_t) { return 0; }" \
  "int esp_sleep_enable_timer_wakeup(uint64_t);"
troca "$W/stubs-envio/esp_sleep.h" "inline int esp_light_sleep_start() { return 0; }" \
  "int esp_light_sleep_start();"
troca "$W/stubs-envio/freertos/task.h" "inline void vTaskDelay(const TickType_t) {}" \
  "void vTaskDelay(const TickType_t);"
troca "$W/stubs-envio/freertos/task.h" "inline void vTaskDelete(TaskHandle_t) {}" \
  "void vTaskDelete(TaskHandle_t);"
cp "$W/stubs/secrets.h" "$W/stubs-envio/secrets.h"
$CXX -std=c++11 -w -c -I"$W/stubs-envio" "$FIRMWARE/nucleo_amalgama.cpp" -o "$W/amalgama-envio.o" || exit 2
$CXX -std=c++11 -w -c -I"$W/stubs-envio" "$W/stubs-envio/stubs.cpp" -o "$W/stubs-envio.o" || exit 2

rodar_envio() { # rodar_envio SKETCH -> 0 passou, 1 acusou, 2 nao compilou
  $CXX -std=c++11 -w -x c++ -I"$W/stubs-envio" -I"$FIRMWARE" -include Arduino.h \
    -DSKETCH="\"$1\"" "$AQUI/envio_do_sketch.cpp" -x none "$W/amalgama-envio.o" \
    "$W/stubs-envio.o" -o "$W/envio" 2>"$W/erro" || { cat "$W/erro"; return 2; }
  "$W/envio" >"$W/saida" 2>&1
}

rodar_envio "$FIRMWARE/sketch.ino"
r=$?
grep -v '^\[' "$W/saida"
if [ $r -ne 0 ]; then
  echo "FALHOU -- o envio do sketch.ino nao se comporta como o FW-14 promete."
  exit 1
fi

echo
echo "Sabotadores do ENVIO NO SKETCH -- o teste tem de acusar:"
sabotar_envio() { # sabotar_envio ROTULO DE PARA
  total=$((total + 1))
  cp "$FIRMWARE/sketch.ino" "$W/sabotado.ino"
  troca "$W/sabotado.ino" "$2" "$3"
  rodar_envio "$W/sabotado.ino"
  r=$?
  n=$(grep -c "FALHA" "$W/saida")
  if [ $r -eq 1 ]; then
    printf '  %-48s acusou (%s falhas)\n' "$1" "$n"
  else
    printf '  %-48s NAO ACUSOU (saida %s)\n' "$1" "$r"
    falhas=$((falhas + 1))
  fi
}

sabotar_envio "17. uma conexao por lote (o de ate 17/11)" \
  "  http.setReuse(true);
" \
  ""
sabotar_envio "18. a falha nao encerra a volta" \
  "    if (d.acao == LOTE_RECUAR || d.recuar_depois) {
      ok = false;
      break;
    }" \
  "    if (d.acao == LOTE_RECUAR || d.recuar_depois) {
      ok = false;
    }"
sabotar_envio "19. a conexao nova nao e contada" \
  "  if (!cliente.connected()) contadores.conexoes_tls++;" \
  ""
sabotar_envio "20. o maior lote nao e medido" \
  "    if (preparo.tamanho > contadores.maior_lote.load()) contadores.maior_lote.store(preparo.tamanho);" \
  ""
sabotar_envio "21. o loop() volta a so esperar" \
  "void loop() { vTaskDelete(NULL); }" \
  "void loop() { vTaskDelay(portMAX_DELAY); }"
sabotar_envio "22. o buffer volta a 520 B por leitura" \
  "static const size_t TAMANHO_JSON_DO_LOTE = tamanho_do_lote(LEITURAS_POR_LOTE_NO_ESP32);" \
  "static const size_t TAMANHO_JSON_DO_LOTE = LEITURAS_POR_LOTE_NO_ESP32 * 520;"

echo "$((total - falhas))/$total como esperado"
[ $falhas -eq 0 ]
