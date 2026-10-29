// nucleo_amalgama.cpp -- traz o nucleo para dentro do build do sketch.
//
// A IDE do Arduino so compila os arquivos que estao na pasta do sketch (e em
// `src/`). O nucleo mora em `firmware/nucleo/`, fora dela, de proposito: ele e
// compartilhado com o `sketch.ino` e e compilado e testado no host com g++,
// onde nao existe Arduino nenhum.
//
// Os CABECALHOS o sketch alcanca por caminho relativo. Os .cpp, nao -- eles
// simplesmente nao entram na lista de compilacao. Este arquivo resolve isso
// sendo a unica unidade de traducao que os inclui.
//
// A alternativa seria duplicar o nucleo dentro de cada sketch, e ai as duas
// copias divergiriam na primeira correcao -- que e exatamente como o
// `sketch.ino` e o `envio-continuo.ino` acabaram com criterios de movimento
// diferentes antes do FW-06.

#include "../nucleo/epoca.cpp"
#include "../nucleo/payload.cpp"
