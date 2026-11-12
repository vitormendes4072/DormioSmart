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
troca "$W/stubs/Arduino.h" "  uint8_t requestFrom(uint8_t, size_t) { return 0; }" \
  "  uint8_t requestFrom(uint8_t, size_t) { gancho_i2c(); return 0; }"
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

echo "$((total - falhas))/$total como esperado"
[ $falhas -eq 0 ]
