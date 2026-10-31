// nucleo_amalgama.cpp -- traz o nucleo para dentro do build do `sketch.ino`.
//
// Mesmo motivo do `envio-continuo/nucleo_amalgama.cpp`: a IDE do Arduino so
// compila o que esta na pasta do sketch, e o nucleo mora em `nucleo/`, onde e
// testado no host. Esta e a unica unidade de traducao que inclui os .cpp dele.
// Se um .cpp novo entrar no nucleo e o sketch passar a usa-lo, ele tem de
// entrar aqui -- senao o link falha na IDE (o `make sintaxe` nao linka).

#include "nucleo/cadeia_c2.cpp"
#include "nucleo/caracteristicas.cpp"
#include "nucleo/envio_da_fila.cpp"
#include "nucleo/epoca.cpp"
#include "nucleo/epoca_c2.cpp"
#include "nucleo/fifo_mpu.cpp"
#include "nucleo/fila_flash.cpp"
#include "nucleo/filtro.cpp"
#include "nucleo/lote.cpp"
#include "nucleo/payload.cpp"
#include "nucleo/reamostragem.cpp"
#include "nucleo/registro_flash.cpp"
