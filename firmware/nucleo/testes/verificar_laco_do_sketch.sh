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

echo "$((total - falhas))/$total como esperado"
[ $falhas -eq 0 ]
