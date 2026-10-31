#!/bin/sh
# verificar_fila_por_mutacao.sh -- quem testa os testes da fila na flash (FW-08).
#
# Sabota a fila de proposito, um erro plausivel por vez, e exige que
# `testes_fila_flash` ACUSE. Um teste que nunca viu o defeito que diz pegar e
# uma afirmacao, nao uma verificacao (§1 e §4 de docs/LICOES-APRENDIDAS.md).
#
# Cada sabotador e um defeito que custaria dado de verdade numa noite: lixo
# aceito como medida, registro pendente apagado, hora inventada, ordem trocada.

set -u

AQUI=$(cd "$(dirname "$0")" && pwd)
NUCLEO=$(cd "$AQUI/.." && pwd)
CXX=${CXX:-g++}
BANDEIRAS="-std=c++11 -w -O2 -fno-exceptions -fno-rtti"
FONTES="epoca.cpp payload.cpp filtro.cpp caracteristicas.cpp fifo_mpu.cpp reamostragem.cpp cadeia_c2.cpp lote.cpp registro_flash.cpp fila_flash.cpp"

falhas=0
total=0

rodar() { # rodar ARQUIVO DE PARA -> define ACUSOU (sim|nao|erro)
  arquivo=$1
  de=$2
  para=$3
  ACUSOU=erro

  W=$(mktemp -d)
  cp "$NUCLEO"/*.cpp "$NUCLEO"/*.h "$W"/ 2>/dev/null
  mkdir -p "$W/testes"
  cp "$AQUI/testes_fila_flash.cpp" "$W/testes/"

  if [ -n "$de" ]; then
    # O trecho tem de casar EXATAMENTE UMA VEZ: sabotador que nao casa nao
    # sabota nada, e o alvo "passa" -- parece ponto cego e e sabotador morto.
    n=$(DE="$de" python3 -c '
import os, sys
print(open(sys.argv[1]).read().replace("\r\n", "\n").count(os.environ["DE"]))
' "$W/$arquivo")
    if [ "$n" != "1" ]; then
      echo "SABOTADOR QUEBRADO (casou $n vezes em $arquivo)"
      rm -rf "$W"
      return
    fi
    DE="$de" PARA="$para" python3 -c '
import os, sys
p = sys.argv[1]
s = open(p).read().replace("\r\n", "\n")
open(p, "w").write(s.replace(os.environ["DE"], os.environ["PARA"]))
' "$W/$arquivo"
  fi

  fontes=""
  for f in $FONTES; do fontes="$fontes $W/$f"; done
  if ! $CXX $BANDEIRAS -I"$W" "$W/testes/testes_fila_flash.cpp" $fontes -o "$W/t" 2>/dev/null; then
    echo "NAO COMPILA"
    rm -rf "$W"
    return
  fi

  if "$W/t" >"$W/o" 2>&1; then ACUSOU=nao; else ACUSOU=sim; fi
  f=$(grep -oE '[0-9]+ falhas' "$W/o" | head -1)
  echo "acusou: $ACUSOU (${f:-?})"
  rm -rf "$W"
}

esperar() { # esperar ROTULO ARQUIVO DE PARA
  rotulo=$1
  total=$((total + 1))
  printf '  %-52s ' "$rotulo"
  rodar "$2" "$3" "$4"
  if [ "$ACUSOU" != "sim" ]; then
    echo "      ^^ ESPERADO: a suite da fila acusa"
    falhas=$((falhas + 1))
  fi
}

echo
echo "VERIFICACAO POR MUTACAO DA FILA NA FLASH (FW-08)"
echo "================================================"
echo
echo "Controle -- a arvore intacta NAO pode ser acusada:"
total=$((total + 1))
printf '  %-52s ' "0. sem sabotagem"
rodar fila_flash.cpp "" ""
if [ "$ACUSOU" != "nao" ]; then
  echo "      ^^ a arvore limpa foi acusada. Nada abaixo significa nada."
  falhas=$((falhas + 1))
fi

echo
echo "Sabotadores -- a suite da fila tem de acusar:"

esperar "1. CRC para antes do vetor" registro_flash.cpp \
  "static const uint32_t BYTES_COBERTOS_PELO_CRC = 62;" \
  "static const uint32_t BYTES_COBERTOS_PELO_CRC = 44;"

esperar "2. entregue pela metade conta como entregue" registro_flash.h \
  "  bool foi_entregue() const { return entregue == ENTREGUE_CONFIRMADO; }" \
  "  bool foi_entregue() const { return entregue != ENTREGUE_PENDENTE; }"

esperar "3. apaga setor com pendente" fila_flash.cpp \
  "        if (setor_tem_pendente(cabeca_, &ok)) {" \
  "        if (false && setor_tem_pendente(cabeca_, &ok)) {"

esperar "4. programa por cima do slot sujo" fila_flash.cpp \
  "    if (slot_em_branco(cabeca_, &ok)) break;" \
  "    break;"

esperar "5. monotonico enviado como hora de parede" registro_flash.cpp \
  "  if (r.instante_e_parede()) {" \
  "  if (true) {"

esperar "6. sessao nao muda no reset" fila_flash.cpp \
  "  sessao_ = static_cast<uint16_t>(achou ? maior_sessao + 1u : 1u);" \
  "  sessao_ = static_cast<uint16_t>(achou ? maior_sessao : 1u);"

esperar "7. cauda procurada do slot 0, nao da cabeca" fila_flash.cpp \
  "  uint32_t s = cabeca_;" \
  "  uint32_t s = 0;"

esperar "8. sem releitura depois de programar" fila_flash.cpp \
  "      ler_slot(slot, &lido, &ok) != SLOT_VALIDO || lido.seq != r.seq) {" \
  "      false) {"

esperar "9. o ms arredonda para cima" registro_flash.cpp \
  "      i.segundos = static_cast<uint32_t>(unix_ms / 1000);" \
  "      i.segundos = static_cast<uint32_t>((unix_ms + 999) / 1000);"

esperar "10. vetor gravado sem a bandeira" fila_flash.cpp \
  "  if (vetor) r.bandeiras |= REGISTRO_TEM_FEATURES;" \
  "  (void)0;"

echo
echo "-----------------------------------------"
echo "$((total - falhas))/$total como esperado"
[ $falhas -eq 0 ]
