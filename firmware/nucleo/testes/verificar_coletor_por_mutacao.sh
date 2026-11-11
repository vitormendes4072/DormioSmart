#!/bin/sh
# verificar_coletor_por_mutacao.sh -- quem testa os testes do coletor do celular (APP-02).
#
# Sabota o `coletor_celular.cpp` de proposito, um erro plausivel por vez, e
# exige que `testes_coletor_celular` ACUSE. Mesmo formato do
# `verificar_cadeia_por_mutacao.sh` (§1 e §4 de docs/LICOES-APRENDIDAS.md).
#
# Sabotador marcado PONTO_CEGO e o que a suite declaradamente NAO pega, e o
# verificador confere que continua assim: se um dia acusar, o registro de
# ponto cego esta velho.

set -u

AQUI=$(cd "$(dirname "$0")" && pwd)
NUCLEO=$(cd "$AQUI/.." && pwd)
DOURADO="$NUCLEO/../../ml/testes/vetor_dourado_cadeia_c2.json"
CXX=${CXX:-g++}
BANDEIRAS="-std=c++11 -w -O2 -fno-exceptions -fno-rtti"
FONTES="epoca.cpp payload.cpp filtro.cpp caracteristicas.cpp fifo_mpu.cpp reamostragem.cpp cadeia_c2.cpp lote.cpp registro_flash.cpp fila_flash.cpp epoca_c2.cpp envio_da_fila.cpp coletor_celular.cpp"

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
  cp "$NUCLEO"/*.cpp "$NUCLEO"/*.h "$W"/ 2>/dev/null
  mkdir -p "$W/testes"
  cp "$AQUI/leitor_json.h" "$AQUI/leitor_json.cpp" "$AQUI/testes_coletor_celular.cpp" "$W/testes/"
  if [ -n "$de" ]; then
    n=$(DE="$de" python3 -c '
import os, sys
print(open(sys.argv[1]).read().replace("\r\n", "\n").count(os.environ["DE"]))
' "$W/coletor_celular.cpp")
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
' "$W/coletor_celular.cpp"
  fi
  fontes=""
  for f in $FONTES; do fontes="$fontes $W/$f"; done
  if ! $CXX $BANDEIRAS -I"$W" "$W/testes/testes_coletor_celular.cpp" $fontes \
       "$W/testes/leitor_json.cpp" -o "$W/t" 2>/dev/null; then
    echo "NAO COMPILA"
    rm -rf "$W"
    return
  fi
  if "$W/t" "$DOURADO" >"$W/o" 2>&1; then ACUSOU=nao; else ACUSOU=sim; fi
  rm -rf "$W"
}

caso() { # caso NOME ESPERADO(acusa|PONTO_CEGO|limpo) DE PARA
  nome=$1
  esperado=$2
  total=$((total + 1))
  rodar "$3" "$4"
  case "$esperado:$ACUSOU" in
    acusa:sim|PONTO_CEGO:nao|limpo:nao) echo "  ok    $nome ($ACUSOU)" ;;
    *) echo "  FALHA $nome: esperado $esperado, acusou=$ACUSOU"; falhas=$((falhas + 1)) ;;
  esac
}

echo "Mutacao do coletor do celular -- APP-02"
echo "======================================="

caso "sem sabotagem" limpo "" ""

caso "drenagem carimbada no instante da ultima amostra, sem o meio passo" PONTO_CEGO \
  "  const uint64_t t_us = t_ultima_us_ + meio_passo_us;" \
  "  const uint64_t t_us = t_ultima_us_;"

caso "amostra fora de ordem aceita" acusa \
  "  if (tem_amostra_ && t_us <= t_ultima_us_) {" \
  "  if (false) {"

caso "drenagem depois de a amostra nova entrar (carimba o antes do buraco com o depois)" PONTO_CEGO \
  "  if (n_pendentes_ > 0 &&
      (t_us - t_ultima_drenagem_us_ >= INTERVALO_DE_DRENAGEM_US ||
       n_pendentes_ >= CAPACIDADE_DA_DRENAGEM)) {
    drenar();
  }
  AmostraBruta &a = pendentes_[n_pendentes_];
  a.x = g_para_lsb(ax_ms2 / G_PADRAO_MS2);
  a.y = g_para_lsb(ay_ms2 / G_PADRAO_MS2);
  a.z = g_para_lsb(az_ms2 / G_PADRAO_MS2);
  if (n_pendentes_ == 0) t_primeira_pendente_us_ = t_us;
  n_pendentes_++;
  t_ultima_us_ = t_us;" \
  "  const bool drenar_agora = n_pendentes_ > 0 &&
      (t_us - t_ultima_drenagem_us_ >= INTERVALO_DE_DRENAGEM_US ||
       n_pendentes_ >= CAPACIDADE_DA_DRENAGEM - 1);
  AmostraBruta &a = pendentes_[n_pendentes_];
  a.x = g_para_lsb(ax_ms2 / G_PADRAO_MS2);
  a.y = g_para_lsb(ay_ms2 / G_PADRAO_MS2);
  a.z = g_para_lsb(az_ms2 / G_PADRAO_MS2);
  if (n_pendentes_ == 0) t_primeira_pendente_us_ = t_us;
  n_pendentes_++;
  t_ultima_us_ = t_us;
  if (drenar_agora) drenar();"

caso "conversao para g com 9,81 em vez de 9,80665" acusa \
  "  a.x = g_para_lsb(ax_ms2 / G_PADRAO_MS2);" \
  "  a.x = g_para_lsb(ax_ms2 / 9.81f);"

caso "eixo trocado na conversao" acusa \
  "  a.y = g_para_lsb(ay_ms2 / G_PADRAO_MS2);" \
  "  a.y = g_para_lsb(az_ms2 / G_PADRAO_MS2);"

caso "quantizacao trunca em vez de arredondar" acusa \
  "  return static_cast<int16_t>(lroundf(lsb));" \
  "  return static_cast<int16_t>(lsb);"

caso "payload com o vetor cru, sem a ida e volta da fila" acusa \
  "    f_enviada = desquantizar(quantizar(f), static_cast<uint16_t>(AMOSTRAS_NA_GRADE));" \
  "    f_enviada = f;"

caso "ts no inicio da epoca seguinte" acusa \
  "      e, parede_, inicio_da_epoca_c2_ms(origem_us_, info.indice), destino, tamanho, escritos," \
  "      e, parede_, inicio_da_epoca_c2_ms(origem_us_, info.indice + 1), destino, tamanho, escritos,"

caso "temperatura do aparelho ignorada" acusa \
  "  const Epoca e = epoca_da_grade(info.indice, grade_x_, grade_y_, grade_z_, AMOSTRAS_NA_GRADE,
                                 temperatura_c_);" \
  "  const Epoca e = epoca_da_grade(info.indice, grade_x_, grade_y_, grade_z_, AMOSTRAS_NA_GRADE,
                                 25.0f);"

caso "toda recusa contada como de taxa" acusa \
  "    if (r == EPOCA_RECUSADA_TAXA) recusadas_taxa_++;" \
  "    recusadas_taxa_++;"

caso "NaN do sensor vira saturacao" acusa \
  "  if (!(lsb == lsb)) return 0;" \
  "  if (!(lsb == lsb)) return 32767;"

echo ""
echo "$total sabotadores, $falhas falhas do verificador"
[ "$falhas" -eq 0 ]
