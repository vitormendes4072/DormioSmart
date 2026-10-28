// Definicoes dos objetos globais dos stubs, e o `setup`/`loop` que o .ino
// declara. Nada aqui roda: o alvo e so compilar.
#include "Arduino.h"
#include "WiFi.h"
#include "esp_sleep.h"

SerialStub Serial;
WireStub Wire;
WiFiStub WiFi;
EspStub ESP;
