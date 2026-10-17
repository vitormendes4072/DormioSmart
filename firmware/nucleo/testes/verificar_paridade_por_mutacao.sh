#!/bin/sh
# verificar_paridade_por_mutacao.sh -- quem testa o teste de paridade.
#
# ╔══════════════════════════════════════════════════════════════════════╗
# ║ POR QUE ISTO EXISTE                                                  ║
# ╚══════════════════════════════════════════════════════════════════════╝
#
# `make dourado` passa. Isso NAO prova que ele verificaria paridade -- prova
# que ele nao reclamou. Um alvo que lesse zeros e os comparasse com zeros
# tambem passaria, e o `DATA-07c` ja gastou uma entrada inteira de diario
# descobrindo que o instrumento do lado Python era desse tipo: ele gravava a
# propria referencia e conferia que o arquivo existia.
#
# Este script faz com o alvo C++ o que
# `ml/testes/verificar_vetor_dourado_por_mutacao.py` faz com o lado Python:
# SABOTA o codigo de producao, uma mudanca por vez, numa copia da arvore em
# /tmp, e exige que `bin/testes_dourado` ACUSE cada sabotagem.
#
# Em shell, e nao em Python, por um motivo bobo e suficiente: o que precisa
# ser orquestrado aqui e `cp`, `sed` e `g++`. O verificador do Python precisa
# de Python porque ele importa e roda pytest.
#
# ── COMO LER A SAIDA ──────────────────────────────────────────────────
#
#   DETECTADO   o alvo acusou. E o resultado desejado para um SABOTADOR.
#   passou      o alvo nao acusou. Desejado so para um PONTO CEGO declarado.
#
# Um sabotador que passa e um defeito do instrumento. Um ponto cego que passa
# a ser DETECTADO e boa noticia -- e exige atualizar o registro aqui, senao a
# documentacao fica mentindo por excesso de modestia.
#
# Uso:  sh testes/verificar_paridade_por_mutacao.sh
# Saida: 0 se todos os sabotadores foram detectados e os pontos cegos
#        continuam cegos; 1 caso contrario.

set -u

AQUI=$(cd "$(dirname "$0")" && pwd)
NUCLEO=$(cd "$AQUI/.." && pwd)
DOURADO="$NUCLEO/../../ml/testes/vetor_dourado.json"
CXX=${CXX:-g++}
# `-w`: os avisos nao interessam aqui, e um sabotador pode legitimamente
# produzir um. O que interessa e se o ALVO acusa.
BANDEIRAS="-std=c++11 -w -O2 -fno-exceptions -fno-rtti"

falhas=0
total=0

if [ ! -f "$DOURADO" ]; then
  echo "ERRO: $DOURADO nao existe. Rode a suite do ml/ primeiro."
  exit 1
fi

# rodar ARQUIVO DE PARA  -> imprime o resultado
# Com DE vazio, roda sem sabotagem (o controle).
rodar() {
  arquivo=$1
  de=$2
  para=$3

  W=$(mktemp -d)
  cp "$NUCLEO"/*.cpp "$NUCLEO"/*.h "$W"/ 2>/dev/null
  mkdir -p "$W/testes"
  cp "$AQUI/leitor_json.h" "$AQUI/leitor_json.cpp" "$AQUI/testes_dourado.cpp" "$W/testes/"

  if [ -n "$de" ]; then
    # ⚠️ O trecho tem de casar EXATAMENTE UMA VEZ.
    #
    # Isto nao e paranoia: e a licao que o verificador do Python aprendeu e
    # escreveu em letras maiusculas ("SABOTADOR QUEBRADO: o codigo mudou
    # debaixo do sabotador -- conserte o sabotador, nao a suite"). Um
    # sabotador que nao casa nao sabota nada, e o alvo "passa" -- que lido
    # sem cuidado parece um ponto cego e e, na verdade, um sabotador morto.
    n=$(grep -c -F "$de" "$W/$arquivo" 2>/dev/null || echo 0)
    if [ "$n" != "1" ]; then
      echo "SABOTADOR QUEBRADO (casou $n vezes em $arquivo)"
      falhas=$((falhas + 1))
      rm -rf "$W"
      return
    fi
    # `python3` para a substituicao, e nao `sed`: os trechos tem `[`, `]`,
    # `/` e `*`, que em `sed` exigiriam escape e já causaram uma substituicao
    # silenciosamente vazia durante o desenvolvimento deste script.
    DE="$de" PARA="$para" python3 -c '
import os, sys
p = sys.argv[1]
s = open(p).read()
open(p, "w").write(s.replace(os.environ["DE"], os.environ["PARA"]))
' "$W/$arquivo"
  fi

  if ! $CXX $BANDEIRAS -I"$W" "$W/testes/testes_dourado.cpp" \
       "$W/epoca.cpp" "$W/payload.cpp" "$W/filtro.cpp" \
       "$W/caracteristicas.cpp" "$W/testes/leitor_json.cpp" \
       -o "$W/b" 2>/dev/null; then
    echo "NAO COMPILA"
    falhas=$((falhas + 1))
    rm -rf "$W"
    return
  fi

  if "$W/b" "$DOURADO" >"$W/o" 2>&1; then
    resultado=passou
  else
    resultado=DETECTADO
  fi
  conta=$(grep -oE '[0-9]+ falhas' "$W/o" | head -1)
  angulo=$(grep 'g (angulo, grau)' "$W/o" | head -1 | awk '{print $4}')
  echo "$resultado | $conta | ang(g)=$angulo"
  rm -rf "$W"
  ULTIMO=$resultado
}

esperar() { # esperar ROTULO ESPERADO ARQUIVO DE PARA
  rotulo=$1
  esperado=$2
  total=$((total + 1))
  printf '  %-46s ' "$rotulo"
  rodar "$3" "$4" "$5"
  if [ "${ULTIMO:-}" != "$esperado" ]; then
    echo "      ^^ ESPERADO: $esperado"
    falhas=$((falhas + 1))
  fi
}

echo
echo "VERIFICACAO POR MUTACAO DO ALVO DE PARIDADE (DATA-07b)"
echo "======================================================"
echo
echo "Controle -- a arvore intacta tem de PASSAR:"
total=$((total + 1))
printf '  %-46s ' "0. sem sabotagem"
rodar caracteristicas.cpp "" ""
if [ "${ULTIMO:-}" != "passou" ]; then
  echo "      ^^ a arvore limpa NAO passa. Nada abaixo significa nada."
  falhas=$((falhas + 1))
fi

echo
echo "SABOTADORES -- cada um tem de ser DETECTADO:"

esperar "1. filtro sem regime permanente" DETECTADO filtro.cpp \
  "double x1 = v0, x2 = v0, y1 = v0, y2 = v0;" \
  "double x1 = 0, x2 = 0, y1 = 0, y2 = 0;"

esperar "2. filtro causal, so a passagem de ida" DETECTADO filtro.cpp \
  "  passagem(v, n, c, -1);" \
  "  (void)0;"

esperar "3. corte do filtro 2% fora" DETECTADO filtro.cpp \
  "const double k = tan(PI * static_cast<double>(corte_hz) / static_cast<double>(fs));" \
  "const double k = tan(PI * static_cast<double>(corte_hz) / static_cast<double>(fs) * 1.02);"

esperar "4. coeficientes em float32" DETECTADO filtro.h \
  "  double b0, b1, b2, a1, a2;" \
  "  float b0, b1, b2, a1, a2;"

esperar "5. zcr dividido por n em vez de n-1" DETECTADO caracteristicas.cpp \
  "f.zcr = static_cast<double>(cruzamentos) / (dn - 1.0);" \
  "f.zcr = static_cast<double>(cruzamentos) / dn;"

esperar "6. zcr contra zero, nao contra a media" DETECTADO caracteristicas.cpp \
  "const double media_mags = soma_mags / dn;" \
  "const double media_mags = 0.0;"

esperar "7. desvio amostral em vez de populacional" DETECTADO caracteristicas.cpp \
  "const double variancia = soma_enmo2 / dn - media_enmo * media_enmo;" \
  "const double variancia = (soma_enmo2 - dn*media_enmo*media_enmo)/(dn-1.0);"

esperar "8. ENMO com |x| em vez de max(x,0)" DETECTADO caracteristicas.cpp \
  "if (e < 0.0) e = 0.0;" \
  "if (e < 0.0) e = -e;"

esperar "9. p_frac com limiar em m/s2 (unidade)" DETECTADO caracteristicas.cpp \
  "const double limiar = static_cast<double>(LIMIAR_P_FRAC_G);" \
  "const double limiar = 1.2;"

esperar "10. g com vies de 1% num eixo" DETECTADO caracteristicas.cpp \
  "const double gmx = soma_g[0] / dn;" \
  "const double gmx = soma_g[0] / dn * 1.01;"

esperar "11. epoca truncada deixa de ser recusada" DETECTADO caracteristicas.cpp \
  "if (n_ < AMOSTRAS_MINIMAS_PARA_PARIDADE) return false;" \
  "if (n_ < 2u) return false;"

echo
echo "PONTOS CEGOS DECLARADOS -- estes DEVEM passar. Ver as notas abaixo."

esperar "C1. p_frac com >= em vez de >" passou caracteristicas.cpp \
  "if (mag_din > limiar) acima++;" \
  "if (mag_din >= limiar) acima++;"

esperar "C2. g normalizado ANTES de promediar" passou caracteristicas.cpp \
  "      soma_g[k] += g;" \
  "      soma_g[k] += g / sqrt(1e-24 + (double)bruto_[0][i]*bruto_[0][i] + (double)bruto_[1][i]*bruto_[1][i] + (double)bruto_[2][i]*bruto_[2][i]);"

esperar "C3. g com vies de 0,01% num eixo" passou caracteristicas.cpp \
  "const double gmx = soma_g[0] / dn;" \
  "const double gmx = soma_g[0] / dn * 1.0001;"

cat <<'NOTAS'

AS NOTAS DOS PONTOS CEGOS
-------------------------

C1 -- `p_frac` com `>=` em vez de `>`.
  Ja era conhecido e esta registrado do lado do Python
  (`p_frac_limiar_inclusivo` em verificar_vetor_dourado_por_mutacao.py). A
  diferenca so aparece se alguma amostra cair EXATAMENTE no limiar, o que em
  ponto flutuante sobre sinal continuo tem medida zero. Nenhum dado de teste
  sintetico exercita isso.
  MITIGACAO: o `>` foi copiado por LEITURA da secao 2.6 do contrato ("fracao
  de amostras com ||a - g|| ACIMA do limiar"), com a nota em
  caracteristicas.cpp apontando para esta linha. Nao e teste, e procedencia.

C2 -- `g` normalizado antes de promediar (media de direcoes em vez de direcao
  da media).
  ⚠️ ESTE E NOVO, descoberto por este script, e e ESTRUTURAL -- nao se fecha
  estendendo o dourado. Medido:

    amplitude   piso de borda   sabotagem    (graus)
      0,02 g       0,0213        0,0004
      0,10 g       0,0943        0,0105
      0,20 g       0,1857        0,0400
      0,40 g       0,3683        0,1406
      0,60 g       0,5507        0,2793
      1,20 g       1,0963        0,8184

  A sabotagem so cruzaria a tolerancia de 0,25 grau com amplitude ~0,6 g --
  mas nessa amplitude o PISO DE BORDA LEGITIMO ja vale 0,55 grau, o dobro.
  Em toda a faixa medida o piso e ~2x a sabotagem, e os dois escalam juntos
  porque sao governados pela MESMA grandeza: a variacao de ||g_filtrado|| ao
  longo da epoca. Entao nao existe amplitude em que a regua angular separe
  "estimador trocado" de "residuo de borda", e acrescentar um caso de
  movimento grande ao dourado PIORARIA a situacao -- faria o piso estourar a
  tolerancia e reprovar firmware correto.

  Por que o lado Python DETECTA e o C++ nao: o Python compara byte a byte com
  o arquivo gravado, uma regua de igualdade exata. Entre duas implementacoes
  so existe regua de TOLERANCIA, e uma tolerancia derivada de um piso fisico
  nao pode ser mais fina que esse piso. A assimetria e inerente a fronteira,
  nao um defeito corrigivel deste alvo.

  MITIGACAO: a ordem esta escrita e justificada em caracteristicas.cpp
  ("promediar e normalizar DEPOIS"), apontando o sabotador do Python que a
  prende do outro lado. E o lado Python continua detectando -- o que significa
  que a definicao esta presa, so nao por aqui.

C3 -- `g` com vies multiplicativo de 0,01% num eixo.
  Nao e cegueira: e a tolerancia fazendo o que foi derivada para fazer. 1e-4
  de vies move `g` em 0,0014 grau, e a tolerancia de 0,25 grau existe porque
  o estudo do buffer mostrou que a menor decisao a jusante e a fronteira de
  1 grau. Uma divergencia de 0,0014 grau nao muda decisao nenhuma. O
  sabotador 10 mostra onde a sensibilidade comeca: 1% de vies (0,29 grau) e
  detectado. O limiar de deteccao fica em ~0,8% de vies.

NOTAS
echo "------------------------------------------"
echo "$total casos, $falhas em desacordo com o esperado"
[ "$falhas" -eq 0 ] || exit 1
exit 0
