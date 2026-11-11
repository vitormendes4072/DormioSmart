# O nucleo do firmware dentro do app (APP-02).
#
# Compila as fontes de `firmware/nucleo/` DIRETO do repositorio, sem copia: o
# app e a placa rodam o mesmo arquivo, e uma correcao no nucleo chega aos
# dois. A lista e a do `FONTES` do Makefile do nucleo, que o CI testa no host
# com g++ (inclusive `make celular` e `make mutacao-coletor`).
cmake_minimum_required(VERSION 3.22.1)
project(dormio_nucleo CXX)

set(NUCLEO ${CMAKE_CURRENT_SOURCE_DIR}/../../../../../../firmware/nucleo)
if(NOT EXISTS ${NUCLEO}/coletor_celular.cpp)
  message(FATAL_ERROR "firmware/nucleo nao encontrado em ${NUCLEO}")
endif()

set(CMAKE_CXX_STANDARD 11)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

add_library(dormio_nucleo SHARED
  ponte.cpp
  ${NUCLEO}/epoca.cpp
  ${NUCLEO}/payload.cpp
  ${NUCLEO}/filtro.cpp
  ${NUCLEO}/caracteristicas.cpp
  ${NUCLEO}/fifo_mpu.cpp
  ${NUCLEO}/reamostragem.cpp
  ${NUCLEO}/cadeia_c2.cpp
  ${NUCLEO}/lote.cpp
  ${NUCLEO}/registro_flash.cpp
  ${NUCLEO}/fila_flash.cpp
  ${NUCLEO}/epoca_c2.cpp
  ${NUCLEO}/envio_da_fila.cpp
  ${NUCLEO}/coletor_celular.cpp
  ${NUCLEO}/calibracao.cpp
)
target_include_directories(dormio_nucleo PRIVATE ${NUCLEO})
# As mesmas bandeiras do Makefile do nucleo: sem excecao e sem RTTI.
target_compile_options(dormio_nucleo PRIVATE -Wall -Wextra -fno-exceptions -fno-rtti)
# Aparelhos com paginas de 16 KB (o emulador do Android 37 e os aparelhos novos)
# so carregam biblioteca alinhada a 16 KB; o NDK 27 alinha a 4 KB por padrao.
target_link_options(dormio_nucleo PRIVATE "-Wl,-z,max-page-size=16384")
