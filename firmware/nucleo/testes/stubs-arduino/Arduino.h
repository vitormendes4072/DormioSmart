// Stubs minimos do Arduino, SO para verificacao de sintaxe no host.
//
// ── POR QUE ISTO EXISTE ────────────────────────────────────────────────
//
// Nao ha arduino-cli nem platformio neste ambiente, entao os .ino nao podem
// ser compilados de verdade aqui. Mas a alternativa -- nao checar nada --
// ja custou caro: ate 2026-09-22 o `envio-continuo.ino` tinha DUAS strings
// com quebra de linha literal no meio (`"...NAO ENVIADO` + nova linha + `"`).
// Isso e erro de sintaxe em C++: o arquivo versionado NUNCA compilou, em
// nenhuma maquina, e ninguem percebeu porque ninguem tentou compilar.
//
// Estes stubs nao simulam o hardware e nao pretendem: eles existem para o
// `g++ -fsyntax-only` conseguir abrir o .ino e reclamar de erro de sintaxe,
// de tipo e de argumento de printf. A logica de verdade e testada no nucleo,
// que nao depende disto.
//
// O que ESTA verificacao pega: string quebrada, ponto-e-virgula faltando,
// tipo errado, funcao inexistente, formato de printf incompativel.
// O que ela NAO pega: comportamento em placa. Para isso, gravar.

#ifndef STUB_ARDUINO_H
#define STUB_ARDUINO_H

#include <math.h>
#include <stdarg.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

#include <string>

// `String` do Arduino aceita numero com casas decimais -- `String(x, 2)` --,
// que `std::string` nao aceita. Sem esta classe, o stub rejeitaria codigo que
// compila na placa, e a verificacao passaria a dar falso alarme.
class String {
 public:
  String() {}
  String(const char *s) : s_(s ? s : "") {}
  String(const std::string &s) : s_(s) {}
  String(float v, int casas = 2) { formatar("%.*f", casas, (double)v); }
  String(double v, int casas = 2) { formatar("%.*f", casas, v); }
  String(int v) { s_ = paraTexto("%d", v); }
  String(long v) { s_ = paraTexto("%ld", v); }
  String(unsigned v) { s_ = paraTexto("%u", v); }
  String(unsigned long v) { s_ = paraTexto("%lu", v); }

  String &operator+=(const String &o) { s_ += o.s_; return *this; }
  String &operator+=(const char *o) { s_ += o; return *this; }
  const char *c_str() const { return s_.c_str(); }
  friend String operator+(const String &a, const String &b) { return String(a.s_ + b.s_); }
  friend String operator+(const char *a, const String &b) { return String(std::string(a) + b.s_); }
  friend String operator+(const String &a, const char *b) { return String(a.s_ + b); }

 private:
  void formatar(const char *f, int casas, double v) {
    char b[64];
    snprintf(b, sizeof(b), f, casas, v);
    s_ = b;
  }
  template <typename T>
  static std::string paraTexto(const char *f, T v) {
    char b[64];
    snprintf(b, sizeof(b), f, v);
    return b;
  }
  std::string s_;
};

inline uint32_t millis() { return 0; }
inline void configTime(long, int, const char *, const char * = 0, const char * = 0) {}
inline void delay(uint32_t) {}
inline void pinMode(int, int) {}
inline int digitalRead(int) { return 0; }

#define INPUT 0
#define HIGH 1
#define LOW 0

class SerialStub {
 public:
  void begin(unsigned long) {}
  void println() {}
  void println(const char *) {}
  void println(const String &) {}
  void println(int) {}
  void print(const char *) {}
  void print(const String &) {}
  void print(int) {}
  void flush() {}
  operator bool() const { return true; }

  // `__attribute__((format))` e o que faz o compilador conferir os %-
  // especificadores contra os argumentos. Num printf de diagnostico com
  // `unsigned long` e `%u` trocados o ESP32 imprime lixo silenciosamente.
  __attribute__((format(printf, 2, 3))) void printf(const char *, ...) {}

  template <typename T>
  void println(const T &) {}
  template <typename T>
  void print(const T &) {}
};
extern SerialStub Serial;

// O core do ESP32 puxa estes pelo proprio Arduino.h; o stub faz o mesmo para
// o sketch.ino nao precisar de include que ele nao tem na placa.
#include "esp_sleep.h"

class WireStub {
 public:
  void begin(int, int) {}
};
extern WireStub Wire;

#endif  // STUB_ARDUINO_H
