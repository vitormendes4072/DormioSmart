#!/usr/bin/env bash
#
# sincronizar-secrets.sh — propaga o secrets.h para as pastas dos sketches
#
# ── POR QUE ISTO PRECISA EXISTIR ────────────────────────────────────────
#
# O Arduino IDE 1.8.x COPIA a pasta do sketch para um diretório temporário
# antes de compilar (é o `arduino_build_NNNNNN` que aparece no log). Arquivo
# que está fora dessa pasta não vai junto, então `#include "../secrets.h"`
# não funciona: o `..` do temporário não é o `..` do projeto.
#
# Ou seja, cada sketch precisa da SUA cópia de `secrets.h`. A duplicação é
# imposta pela ferramenta, não é escolha. O que dá para fazer é impedir que
# as cópias divirjam em silêncio — que foi o que aconteceu em 2026-08-24,
# quando a senha do Wi-Fi foi corrigida numa cópia só.
#
# ── A REGRA ─────────────────────────────────────────────────────────────
#
#   firmware/secrets.h  é o CANÔNICO.
#   firmware/<sketch>/secrets.h  são cópias, descartáveis.
#
# Edite o canônico e rode este script. Se você editou uma cópia por engano
# (fácil: é a que está aberta na IDE), o script detecta e oferece promovê-la
# em vez de sobrescrever seu trabalho.
#
# ── USO ─────────────────────────────────────────────────────────────────
#
#   ./firmware/sincronizar-secrets.sh              # canônico -> cópias
#   ./firmware/sincronizar-secrets.sh --de <pasta> # cópia -> canônico -> demais
#   ./firmware/sincronizar-secrets.sh --conferir   # só relata, não escreve
#
# Nenhum valor de credencial é impresso, em nenhum modo. O script compara
# resumos criptográficos — o terminal pode estar sendo gravado.

set -euo pipefail

AQUI="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CANONICO="$AQUI/secrets.h"
EXEMPLO="$AQUI/secrets.example.h"

modo="propagar"
origem=""

while [ $# -gt 0 ]; do
  case "$1" in
    --conferir) modo="conferir"; shift ;;
    --de)
      modo="promover"
      origem="${2:-}"
      [ -n "$origem" ] || { echo "erro: --de exige o nome da pasta do sketch"; exit 2; }
      shift 2 ;;
    -h|--help) sed -n '2,30p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "erro: opção desconhecida: $1"; exit 2 ;;
  esac
done

# --- Descobre os destinos: toda subpasta de firmware/ que tem um .ino -----
destinos=()
for ino in "$AQUI"/*/*.ino; do
  [ -e "$ino" ] || continue
  destinos+=("$(dirname "$ino")")
done

if [ ${#destinos[@]} -eq 0 ]; then
  echo "Nenhuma pasta de sketch encontrada em $AQUI. Nada a fazer."
  exit 0
fi

resumo() { sha256sum "$1" | cut -c1-12; }
curto()  { basename "$(dirname "$1")"; }

# --- Salvaguarda: destino não pode ser rastreável pelo git ---------------
# Um secrets.h versionado é credencial no histórico para sempre. Conferir
# antes de escrever custa nada e o erro seria irreversível.
for d in "${destinos[@]}"; do
  alvo="$d/secrets.h"
  if ! git -C "$AQUI/.." check-ignore -q "$alvo" 2>/dev/null; then
    echo "ABORTADO: $alvo NÃO está coberto pelo .gitignore."
    echo "          Escrever ali arriscaria versionar credencial."
    exit 1
  fi
done

# --- Modo promover: uma cópia vira o canônico ----------------------------
if [ "$modo" = "promover" ]; then
  fonte="$AQUI/$origem/secrets.h"
  [ -f "$fonte" ] || { echo "erro: não existe $fonte"; exit 1; }
  cp "$fonte" "$CANONICO"
  echo "Promovido: $origem/secrets.h -> firmware/secrets.h (canônico)"
  modo="propagar"
fi

# --- O canônico precisa existir e estar preenchido -----------------------
if [ ! -f "$CANONICO" ]; then
  echo "Não existe $CANONICO."
  echo "Copie o modelo e preencha:"
  echo "    cp firmware/secrets.example.h firmware/secrets.h"
  [ -f "$EXEMPLO" ] || echo "  (atenção: $EXEMPLO também não existe)"
  exit 1
fi

if grep -q "cole-aqui-o-token-do-dispositivo" "$CANONICO"; then
  echo "AVISO: firmware/secrets.h ainda tem o DEVICE_TOKEN do modelo."
  echo "       A API vai responder 401 até você colar o token real."
fi

# --- Detecta cópia mais nova que o canônico ------------------------------
# É o caso que motivou o script: a pessoa edita a cópia aberta na IDE, e
# propagar cegamente apagaria essa edição.
mais_novos=()
for d in "${destinos[@]}"; do
  alvo="$d/secrets.h"
  if [ -f "$alvo" ] && [ "$alvo" -nt "$CANONICO" ] &&
     [ "$(resumo "$alvo")" != "$(resumo "$CANONICO")" ]; then
    mais_novos+=("$(basename "$d")")
  fi
done

if [ ${#mais_novos[@]} -gt 0 ] && [ "$modo" = "propagar" ]; then
  echo "ABORTADO: estas cópias são MAIS NOVAS que o canônico e diferem dele:"
  for n in "${mais_novos[@]}"; do echo "    firmware/$n/secrets.h"; done
  echo
  echo "Propagar agora apagaria essa edição. Se ela é a boa, promova-a:"
  echo "    ./firmware/sincronizar-secrets.sh --de ${mais_novos[0]}"
  echo
  echo "Se o canônico é o certo, encoste-o no tempo e rode de novo:"
  echo "    touch firmware/secrets.h && ./firmware/sincronizar-secrets.sh"
  exit 1
fi

# --- Conferir: relata sem escrever ---------------------------------------
if [ "$modo" = "conferir" ]; then
  echo "canônico  firmware/secrets.h  [$(resumo "$CANONICO")]"
  divergentes=0
  for d in "${destinos[@]}"; do
    alvo="$d/secrets.h"
    if [ ! -f "$alvo" ]; then
      echo "  AUSENTE   firmware/$(basename "$d")/secrets.h"
      divergentes=$((divergentes + 1))
    elif [ "$(resumo "$alvo")" = "$(resumo "$CANONICO")" ]; then
      echo "  ok        firmware/$(basename "$d")/secrets.h"
    else
      echo "  DIVERGE   firmware/$(basename "$d")/secrets.h  [$(resumo "$alvo")]"
      divergentes=$((divergentes + 1))
    fi
  done
  [ "$divergentes" -eq 0 ] && echo "Tudo sincronizado." || echo "$divergentes fora de sincronia."
  exit $([ "$divergentes" -eq 0 ] && echo 0 || echo 1)
fi

# --- Propagar ------------------------------------------------------------
echo "canônico  firmware/secrets.h  [$(resumo "$CANONICO")]"
for d in "${destinos[@]}"; do
  cp "$CANONICO" "$d/secrets.h"
  echo "  gravado   firmware/$(basename "$d")/secrets.h"
done

# --- Confere o que acabou de ser escrito ---------------------------------
for d in "${destinos[@]}"; do
  if [ "$(resumo "$d/secrets.h")" != "$(resumo "$CANONICO")" ]; then
    echo "ERRO: firmware/$(basename "$d")/secrets.h não bate depois da cópia."
    exit 1
  fi
done

echo "${#destinos[@]} cópia(s) sincronizada(s)."
