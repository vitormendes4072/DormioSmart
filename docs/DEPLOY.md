# Deploy — Dormio Smart

Produção: **https://dormio-smart.vercel.app** · Deploy automático a partir de `main`.

---

## Arquitetura no Vercel

Um único domínio serve duas coisas, decididas por rota:

```
/api/*     ─┐
/health    ─┴─▶  função serverless Python (Flask)   ← web-app/
tudo o mais ──▶  arquivos estáticos do build React  ← frontend/dist
```

O `vercel.json` faz isso com dois *builders* e uma ordem de rotas que importa:

| Ordem | Regra | Por quê |
|---|---|---|
| 1 | `/api/(.*)` → `web-app/app.py` | a ingestão do dispositivo e a leitura do app |
| 2 | `/health` → `web-app/app.py` | monitoramento externo |
| 3 | `handle: filesystem` | entrega JS, CSS e imagens do build |
| 4 | `/(.*)` → `/index.html` | **fallback do SPA** |

**A regra 4 não é opcional.** Sem ela, abrir `https://.../configuracoes` direto pela URL
devolve 404: quem conhece essa rota é o React Router, no navegador, e não o servidor. O
fallback entrega o `index.html`, e o roteador resolve o caminho depois de carregar.

**A regra 1 vem antes do `filesystem`** de propósito. Se a ordem invertesse, um arquivo
estático chamado `api` capturaria as chamadas da API.

---

## Variáveis de ambiente (Vercel → Settings → Environment Variables)

| Variável | Valor | Vai ao navegador? |
|---|---|---|
| `SUPABASE_URL` | URL do projeto | não |
| `SUPABASE_SERVICE_ROLE_KEY` | *Secret key* (`sb_secret_…`) | **NUNCA** |
| `SUPABASE_ANON_KEY` | *Publishable key* (`sb_publishable_…`) | não |
| `VITE_SUPABASE_URL` | mesma URL | sim |
| `VITE_SUPABASE_ANON_KEY` | mesma *Publishable key* | sim |

Duas coisas fáceis de errar:

**O prefixo `VITE_` embute o valor no bundle.** Qualquer visitante consegue lê-lo no
DevTools. A *Publishable key* pode — é feita para isso, e quem protege as linhas é o RLS.
A *Secret key* ignora o RLS: com prefixo `VITE_`, o banco inteiro fica exposto. O app
recusa a chave errada ao subir, mas essa checagem é a última defesa, não a primeira.

**`SUPABASE_ANON_KEY` no backend é obrigatória desde o AUTH-03.** É com ela que o Flask
valida o JWT e monta o cliente que carrega o token do usuário. Sem ela,
`GET /api/sleep-history` devolve `[]` para todo mundo — falha silenciosa, sem erro na tela.

---

## Verificação após o deploy

Rode contra o preview **antes** de promover para `main`:

```bash
BASE=https://<url-do-preview>.vercel.app

curl -s -o /dev/null -w "health:   %{http_code}\n" "$BASE/health"
curl -s -o /dev/null -w "raiz:     %{http_code}\n" "$BASE/"
curl -s -o /dev/null -w "rota SPA: %{http_code}\n" "$BASE/configuracoes"
curl -s -o /dev/null -w "ingestao: %{http_code}\n" -X POST \
     -H "Content-Type: application/json" -d '{}' "$BASE/api/data"
```

Esperado:

| Checagem | Esperado | Se vier diferente |
|---|---|---|
| `health` | **200** (ou 503 se faltar credencial) | 404 = a rota não chegou ao Flask |
| `raiz` | **200** | 404 = o build estático não subiu |
| `rota SPA` | **200** | 404 = falta o fallback (regra 4) |
| `ingestao` | **401** | 404 = roteamento errado · **201 = o Flask está sem o SEC-02** |

> ⚠️ O último é o mais importante. **201 significa que a API aceita escrita sem token** —
> foi exatamente o estado da produção antes desta release, e qualquer pessoa com a URL
> podia injetar leituras falsas no banco.

---

## Plano B

Se o build duplo falhar no preview, dá para separar as duas coisas: reverter só o
`vercel.json` para a versão antiga (tudo → Flask) e promover o resto. Isso fecha o buraco
de escrita imediatamente e deixa o roteamento do front para uma segunda tentativa.

O custo: a produção volta a servir o dashboard Jinja antigo, que quebra na leitura — ele
chama `/api/sleep-history` sem JWT e agora recebe 401. Feio, mas seguro.
