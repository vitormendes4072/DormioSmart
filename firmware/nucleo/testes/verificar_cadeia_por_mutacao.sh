#!/bin/sh
# verificar_cadeia_por_mutacao.sh -- quem testa os testes da cadeia C2 (FW-07).
#
# Sabota a cadeia de proposito, um erro plausivel por vez, e exige que a
# suite ACUSE. Um teste que nunca viu o defeito que diz pegar e uma
# afirmacao, nao uma verificacao (§1 e §4 de docs/LICOES-APRENDIDAS.md).
#
# Diferente do `verificar_paridade_por_mutacao.sh`, aqui ha DOIS alvos, e o
# script diz qual acusou:
#
#   dourado  -- `testes_cadeia_c2` contra ml/testes/vetor_dourado_cadeia_c2.json:
#               linha do tempo, janela e grade contra a referencia Python.
#   unidade  -- `testes_c2`: transbordo, faixa de taxa, lote e buffer, que o
#               dourado nao exercita (ele so tem registros limpos).
#
# Cada sabotador declara qual dos dois TEM de acusar. Acusar pelo outro conta
# como falha do verificador: e sinal de que a defesa nao esta onde se pensa.

set -u

AQUI=$(cd "$(dirname "$0")" && pwd)
NUCLEO=$(cd "$AQUI/.." && pwd)
DOURADO="$NUCLEO/../../ml/testes/vetor_dourado_cadeia_c2.json"
CXX=${CXX:-g++}
BANDEIRAS="-std=c++11 -w -O2 -fno-exceptions -fno-rtti"
FONTES="epoca.cpp payload.cpp filtro.cpp caracteristicas.cpp fifo_mpu.cpp reamostragem.cpp cadeia_c2.cpp lote.cpp"

falhas=0
total=0

if [ ! -f "$DOURADO" ]; then
  echo "ERRO: $DOURADO nao existe. Rode a suite do ml/ primeiro."
  exit 1
fi

rodar() { # rodar ARQUIVO DE PARA -> define ACUSOU (nenhum|dourado|unidade|ambos)
  arquivo=$1
  de=$2
  para=$3
  ACUSOU=erro

  W=$(mktemp -d)
  cp "$NUCLEO"/*.cpp "$NUCLEO"/*.h "$W"/ 2>/dev/null
  mkdir -p "$W/testes"
  cp "$AQUI/leitor_json.h" "$AQUI/leitor_json.cpp" "$AQUI/testes_c2.cpp" \
     "$AQUI/testes_cadeia_c2.cpp" "$W/testes/"

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
  if ! $CXX $BANDEIRAS -I"$W" "$W/testes/testes_cadeia_c2.cpp" $fontes \
       "$W/testes/leitor_json.cpp" -o "$W/d" 2>/dev/null ||
     ! $CXX $BANDEIRAS -I"$W" "$W/testes/testes_c2.cpp" $fontes -o "$W/u" 2>/dev/null; then
    echo "NAO COMPILA"
    rm -rf "$W"
    return
  fi

  d=nao; u=nao
  "$W/d" "$DOURADO" >"$W/od" 2>&1 || d=sim
  "$W/u" >"$W/ou" 2>&1 || u=sim
  if [ $d = sim ] && [ $u = sim ]; then ACUSOU=ambos
  elif [ $d = sim ]; then ACUSOU=dourado
  elif [ $u = sim ]; then ACUSOU=unidade
  else ACUSOU=nenhum
  fi
  fd=$(grep -oE '[0-9]+ falhas' "$W/od" | head -1)
  fu=$(grep -oE '[0-9]+ falhas' "$W/ou" | head -1)
  echo "acusou: $ACUSOU (dourado: ${fd:-?} | unidade: ${fu:-?})"
  rm -rf "$W"
}

esperar() { # esperar ROTULO QUEM ARQUIVO DE PARA ; QUEM = dourado|unidade
  rotulo=$1
  quem=$2
  total=$((total + 1))
  printf '  %-50s ' "$rotulo"
  rodar "$3" "$4" "$5"
  case "$ACUSOU" in
    ambos) ok=1 ;;
    "$quem") ok=1 ;;
    *) ok=0 ;;
  esac
  if [ $ok = 0 ]; then
    echo "      ^^ ESPERADO: acusado pelo alvo '$quem'"
    falhas=$((falhas + 1))
  fi
}

echo
echo "VERIFICACAO POR MUTACAO DA CADEIA C2 (FW-07)"
echo "============================================"
echo
echo "Controle -- a arvore intacta NAO pode ser acusada:"
total=$((total + 1))
printf '  %-50s ' "0. sem sabotagem"
rodar cadeia_c2.cpp "" ""
if [ "$ACUSOU" != "nenhum" ]; then
  echo "      ^^ a arvore limpa foi acusada. Nada abaixo significa nada."
  falhas=$((falhas + 1))
fi

echo
echo "Sabotadores da CADEIA -- o dourado tem de acusar:"

esperar "1. taxa nominal no lugar da medida" dourado cadeia_c2.cpp \
  "  const double b = e.linha.b_s;" \
  "  const double b = 0.02;"

esperar "2. sem anti-aliasing" dourado cadeia_c2.cpp \
  "    filtrar_antialiasing(trabalho_, n_janela, static_cast<float>(fs));" \
  "    (void)fs;"

esperar "3. as duas secoes com o mesmo Q" dourado reamostragem.cpp \
  "coeficientes_secao(fs, CORTE_ANTIALIASING_HZ, Q_SECAO_2);" \
  "coeficientes_secao(fs, CORTE_ANTIALIASING_HZ, Q_SECAO_1);"

esperar "4. anti-aliasing causal (sem a volta da secao 1)" dourado reamostragem.cpp \
  "  passagem_biquad(v, n, s1, true);" \
  "  (void)0;"

esperar "5. grade sem o meio passo" dourado cadeia_c2.cpp \
  "const double x0 = (e0 - a) / b - 0.5 - static_cast<double>(k_ini);" \
  "const double x0 = (e0 - a) / b - static_cast<double>(k_ini);"

esperar "6. sem margem antes da epoca" dourado cadeia_c2.cpp \
  "  const double jan_ini = e0 - MARGEM_S;" \
  "  const double jan_ini = e0;"

esperar "7. grade deslocada uma amostra" dourado reamostragem.cpp \
  "    const double x = x0 + static_cast<double>(j) * dx;" \
  "    const double x = x0 + static_cast<double>(j + 1) * dx;"

esperar "8. FIFO lida como little-endian" dourado fifo_mpu.cpp \
  "destino[i].x = static_cast<int16_t>(static_cast<uint16_t>((p[0] << 8) | p[1]));" \
  "destino[i].x = static_cast<int16_t>(static_cast<uint16_t>((p[1] << 8) | p[0]));"

esperar "9. regressao com todas as drenagens, nao so as da janela" dourado cadeia_c2.cpp \
  "    if (t < sel_ini || t > sel_fim) continue;" \
  "    (void)sel_ini;"

esperar "10. escala de +-16 g (2048 LSB/g) no lugar de +-8 g" dourado fifo_mpu.h \
  "const float LSB_POR_G = 4096.0f;" \
  "const float LSB_POR_G = 2048.0f;"

echo
echo "Sabotadores das RECUSAS e do LOTE -- a suite de unidade tem de acusar:"

esperar "11. transbordo na janela deixa de recusar" unidade cadeia_c2.cpp \
  "    if (r.transbordou) {" \
  "    if (false) {"

esperar "12. taxa fora da faixa deixa de recusar" unidade cadeia_c2.cpp \
  "  if (!(fs >= TAXA_MINIMA_FRAC * nominal && fs <= TAXA_MAXIMA_FRAC * nominal)) {" \
  "  if (false) {"

esperar "13. lote confirma tambem os pendentes" unidade lote.cpp \
  "  d.confirmar = enviadas - pendentes;" \
  "  d.confirmar = enviadas;"

esperar "14. lote aceita pendente no meio da lista" unidade lote.cpp \
  "      (pendentes > 0 && menor_pendente != enviadas - pendentes)) {" \
  "      false) {"

esperar "15. buffer confirma depois de degradar" unidade buffer.h \
  "    if (geracao_do_lote != geracao_) return 0;" \
  "    (void)geracao_do_lote;"

esperar "16. FIFO no teto deixa de ser transbordo" unidade fifo_mpu.cpp \
  "  if (fifo_count >= FIFO_CAPACIDADE_BYTES) return LEITURA_TRANSBORDOU;" \
  "  (void)0;"

echo
echo "Sabotadores do PAYLOAD com o vetor (DATA-07b) -- a suite de unidade tem de acusar:"

# As duas condicoes juntas: nivel 0 E 30 s. Cada uma sozinha ja recusa a
# epoca degradada do teste, entao sabotar so uma nao seria cegueira, seria
# redundancia -- e o sabotador nao provaria nada.
DEGRADADA_DE=$(printf '  const bool incluir = features != 0 && e.nivel == 0 &&\n                       e.duracao_s == DURACAO_EPOCA_BASE_S &&')
DEGRADADA_PARA=$(printf '  const bool incluir = features != 0 &&')
esperar "17. epoca degradada leva f" unidade payload.cpp \
  "$DEGRADADA_DE" "$DEGRADADA_PARA"

esperar "18. vetor fora da faixa vai mesmo assim" unidade payload.cpp \
  "                       features_no_contrato(*features, fs_hz);" \
  "                       true;"

esperar "19. f com 4 casas decimais (perde 1e-4 g)" unidade payload.cpp \
  "%.9g,%.9g,%.9g,%.9g,%.9g,%.9g]" \
  "%.4f,%.9g,%.9g,%.9g,%.9g,%.9g]"

echo
echo "-----------------------------------------"
echo "$((total - falhas))/$total como esperado"
[ $falhas -eq 0 ]
