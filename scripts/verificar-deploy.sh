#!/usr/bin/env bash
#
# verificar-deploy.sh — confere se o deploy do commit certo está no ar.
#
#   ./scripts/verificar-deploy.sh            # verifica o HEAD de main
#   ./scripts/verificar-deploy.sh <sha>      # verifica um commit específico
#   ./scripts/verificar-deploy.sh <sha> <url>
#
# POR QUE ESTE SCRIPT EXISTE
#
# Testar a produção logo depois do `git push` testa o deploy ANTERIOR: a Vercel
# leva algumas dezenas de segundos para construir e trocar. Isso já produziu um
# diagnóstico falso — `/dormio-labs.svg` respondeu 404 e o `<title>` veio com o
# nome antigo, e os dois "defeitos" eram só a versão velha ainda respondendo.
#
# A correção não é "esperar um pouco": é **esperar o commit certo**. O script
# só começa a testar depois de confirmar, pela API do GitHub, que existe um
# deploy de produção bem-sucedido apontando para o SHA esperado.
#
# Requer: gh (autenticado) e curl.

set -uo pipefail

REPO="vitormendes4072/DormioSmart"
BASE="${2:-https://dormio-smart.vercel.app}"
SHA="${1:-$(git rev-parse main 2>/dev/null)}"
TENTATIVAS=30          # 30 x 10s = 5 min de teto
INTERVALO=10

if [ -z "$SHA" ]; then
  echo "Não consegui determinar o commit. Passe o SHA como argumento." >&2
  exit 2
fi

curto="${SHA:0:8}"
echo "Commit esperado: $curto"
echo "Destino:         $BASE"
echo

# ── 1. Esperar o deploy DESTE commit ficar pronto ─────────────────────────
echo "Aguardando o deploy de produção deste commit..."
pronto=0
for i in $(seq 1 "$TENTATIVAS"); do
  id=$(gh api "repos/$REPO/deployments?environment=Production&per_page=10" \
        --jq "[.[] | select(.ref | startswith(\"$curto\"))][0].id" 2>/dev/null)

  if [ -n "$id" ] && [ "$id" != "null" ]; then
    estado=$(gh api "repos/$REPO/deployments/$id/statuses" --jq '.[0].state' 2>/dev/null)
    printf "  [%02d/%02d] deploy %s: %s\n" "$i" "$TENTATIVAS" "$id" "${estado:-sem status}"
    case "$estado" in
      success)  pronto=1; break ;;
      failure|error)
        echo
        echo "✗ O deploy deste commit FALHOU. Veja os logs no painel da Vercel." >&2
        exit 1 ;;
    esac
  else
    printf "  [%02d/%02d] ainda não há deploy de produção para %s\n" "$i" "$TENTATIVAS" "$curto"
  fi
  sleep "$INTERVALO"
done

if [ "$pronto" -ne 1 ]; then
  echo
  echo "✗ Tempo esgotado esperando o deploy de $curto." >&2
  echo "  A produção pode estar servindo uma versão anterior — NÃO confie num teste agora." >&2
  exit 1
fi

echo "✓ Deploy de $curto está no ar. Verificando os endpoints."
echo

# ── 2. Verificações ───────────────────────────────────────────────────────
falhas=0

checar() {  # checar <descrição> <esperado> <curl args...>
  local desc="$1" esperado="$2"; shift 2
  local obtido
  obtido=$(curl -s -o /dev/null -w "%{http_code}" --max-time 30 "$@")
  if [ "$obtido" = "$esperado" ]; then
    printf "  ✓ %-34s %s\n" "$desc" "$obtido"
  else
    printf "  ✗ %-34s %s (esperado %s)\n" "$desc" "$obtido" "$esperado"
    falhas=$((falhas + 1))
  fi
}

checar "landing pública"        200 "$BASE/"
checar "rota do SPA"            200 "$BASE/configuracoes"
checar "health check"           200 "$BASE/health"
checar "logo servida"           200 "$BASE/dormio-labs.svg"

# O mais importante: escrita sem token tem de ser recusada.
# 201 aqui significa que a API aceita e GRAVA dado de qualquer origem.
checar "ingestão sem token"     401 -X POST \
       -H "Content-Type: application/json" -d '{}' "$BASE/api/data"

checar "leitura sem sessão"     401 "$BASE/api/sleep-history"

# O bundle referenciado pelo HTML precisa existir de fato — se as rotas de
# estáticos quebrarem, a página carrega em branco com 200 mesmo assim.
asset=$(curl -s --max-time 30 "$BASE/" | grep -o '/assets/[^"]*\.js' | head -1)
if [ -n "$asset" ]; then
  checar "bundle referenciado no HTML" 200 "$BASE$asset"
else
  printf "  ✗ %-34s não encontrei /assets/*.js no HTML\n" "bundle referenciado no HTML"
  falhas=$((falhas + 1))
fi

echo
if [ "$falhas" -eq 0 ]; then
  echo "✓ Tudo certo — $curto está no ar e íntegro."
  exit 0
fi
echo "✗ $falhas verificação(ões) falharam." >&2
exit 1
