#!/bin/sh
# verificar_calibracao_por_mutacao.sh -- quem testa os testes da autocalibracao (CAL-03).
#
# Sabota o `calibracao.cpp` de proposito, um erro plausivel por vez, e exige
# que `testes_calibracao` ACUSE contra o dourado do ml/. Mesmo formato do
# `verificar_coletor_por_mutacao.sh` (§1 e §4 de docs/LICOES-APRENDIDAS.md).

set -u

AQUI=$(cd "$(dirname "$0")" && pwd)
NUCLEO=$(cd "$AQUI/.." && pwd)
DOURADO="$NUCLEO/../../ml/testes/dourado_calibracao.json"
CXX=${CXX:-g++}
BANDEIRAS="-std=c++11 -w -O2 -fno-exceptions -fno-rtti"

falhas=0
total=0

if [ ! -f "$DOURADO" ]; then
  echo "ERRO: $DOURADO nao existe. Rode a suite do ml/ primeiro."
  exit 1
fi

rodar() { # rodar DE PARA -> define ACUSOU (sim|nao|quebrado)
  de=$1
  para=$2
  ACUSOU=quebrado
  W=$(mktemp -d)
  cp "$NUCLEO/calibracao.cpp" "$NUCLEO/calibracao.h" "$W"/
  mkdir -p "$W/testes"
  cp "$AQUI/leitor_json.h" "$AQUI/leitor_json.cpp" "$AQUI/testes_calibracao.cpp" "$W/testes/"
  if [ -n "$de" ]; then
    n=$(DE="$de" python3 -c '
import os, sys
print(open(sys.argv[1]).read().replace("\r\n", "\n").count(os.environ["DE"]))
' "$W/calibracao.cpp")
    if [ "$n" != "1" ]; then
      echo "SABOTADOR QUEBRADO (casou $n vezes)"
      rm -rf "$W"
      return
    fi
    DE="$de" PARA="$para" python3 -c '
import os, sys
p = sys.argv[1]
s = open(p).read().replace("\r\n", "\n")
open(p, "w").write(s.replace(os.environ["DE"], os.environ["PARA"]))
' "$W/calibracao.cpp"
  fi
  if ! $CXX $BANDEIRAS -I"$W" "$W/testes/testes_calibracao.cpp" "$W/calibracao.cpp" \
       "$W/testes/leitor_json.cpp" -o "$W/t" 2>/dev/null; then
    echo "NAO COMPILA"
    rm -rf "$W"
    return
  fi
  if "$W/t" "$DOURADO" >"$W/o" 2>&1; then ACUSOU=nao; else ACUSOU=sim; fi
  rm -rf "$W"
}

caso() { # caso NOME ESPERADO(acusa|limpo) DE PARA
  nome=$1
  esperado=$2
  total=$((total + 1))
  rodar "$3" "$4"
  case "$esperado:$ACUSOU" in
    acusa:sim|limpo:nao) echo "  ok    $nome ($ACUSOU)" ;;
    *) echo "  FALHA $nome: esperado $esperado, acusou=$ACUSOU"; falhas=$((falhas + 1)) ;;
  esac
}

echo "Mutacao da autocalibracao -- CAL-03"
echo "==================================="

caso "sem sabotagem" limpo "" ""
caso "lado minimo de 0,03 g em vez de 0,3 g" acusa \
  "if (p[i][k] > LADO_MINIMO_G) acima = true;" "if (p[i][k] > 0.03) acima = true;"
caso "aceita qualquer erro depois" acusa \
  "  if (c.erro_depois_g > ERRO_MAXIMO_ACEITO_G) return recusar(c);" ""
caso "aceita mesmo se o erro nao caiu" acusa \
  "  if (!(c.erro_depois_g < c.erro_antes_g)) return recusar(c);
  if (c.erro_depois_g > ERRO_MAXIMO_ACEITO_G) return recusar(c);" ""
caso "nunca usa a temperatura" acusa \
  "c.usou_temperatura = (t_max - t_min) >= FAIXA_MINIMA_TEMPERATURA_C;" "c.usou_temperatura = false;"
caso "nunca estima a escala" acusa \
  "const bool completo = c.modos[k] == EIXO_COMPLETO;" "const bool completo = false;"
caso "alvo com a calibracao do meio da iteracao" acusa \
  "aplicar_calibracao(antes, t[i], p[i], cal);" "aplicar_calibracao(c, t[i], p[i], cal);"
caso "sinal da temperatura trocado em aplicar" acusa \
  "c.desvio[k] + c.escala[k] * entrada[k] + c.coef_temp[k] * dt" \
  "c.desvio[k] + c.escala[k] * entrada[k] - c.coef_temp[k] * dt"
caso "uma iteracao so" acusa \
  "it <= ITERACOES_MAXIMAS_CALIBRACAO;" "it <= 1;"
caso "sem minimo de pontos" acusa \
  "n < PONTOS_MINIMOS_CALIBRACAO) return c;" "n < 1) return c;"
caso "desfazer sem dividir pela escala" acusa \
  "(entrada[k] - c.desvio[k] - c.coef_temp[k] * dt) / c.escala[k]" \
  "(entrada[k] - c.desvio[k] - c.coef_temp[k] * dt)"

echo "-----------------------------------"
echo "$((total - falhas))/$total como esperado"
[ "$falhas" -eq 0 ]
