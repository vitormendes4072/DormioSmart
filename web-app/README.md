# API — Smart Dormio

Serviço Flask que recebe as leituras do dispositivo, valida, persiste no Supabase e as
devolve ao aplicativo — cada usuário vendo apenas as próprias.

> **Este serviço não serve páginas.** Ele responde apenas `/api/*` e `/health`. A interface
> é o SPA React em [`../frontend/`](../frontend), entregue como arquivos estáticos. O
> roteamento entre os dois está no `vercel.json` e documentado em
> [`../docs/DEPLOY.md`](../docs/DEPLOY.md).

---

## Dois caminhos, credenciais diferentes

```
ESP32 ──POST /api/data────────▶ Flask ──service_role──▶ Supabase
        X-Device-Token                                      ▲
                                                            │ RLS
App ────GET /api/sleep-history─▶ Flask ──JWT do usuário─────┘
        Authorization: Bearer
```

A separação é deliberada:

- **Ingestão** não tem sessão de usuário, então o RLS não se aplica. O backend usa a
  `service_role` e autentica o **dispositivo** por token.
- **Leitura** tem sessão. O backend repassa o JWT do usuário ao Supabase, e quem filtra é o
  **RLS no banco** — não um `if` em Python que alguém pode esquecer numa consulta futura.

---

## Endpoints

| Método | Rota | Autenticação | Resposta |
|---|---|---|---|
| `POST` | `/api/data` | `X-Device-Token` | `201` · `400` payload inválido · `401` token · `503` não persistiu |
| `GET` | `/api/sleep-history` | `Bearer <JWT>` | `200` com as leituras do usuário · `401` |
| `GET` | `/api/devices` | `Bearer <JWT>` | `200` · `503` |
| `POST` | `/api/devices` | `Bearer <JWT>` | `201` com o token **exibido uma única vez** |
| `PATCH` | `/api/devices/<id>` | `Bearer <JWT>` | `200` · `404` |
| `POST` | `/api/devices/<id>/revogar` | `Bearer <JWT>` | `200` · `404` |
| `GET` | `/health` | nenhuma | `200` saudável · `503` banco indisponível |

O contrato do dado que trafega está em [`../docs/DATA-CONTRACT.md`](../docs/DATA-CONTRACT.md).

---

## Rodando localmente

```bash
cd web-app
pip install -r requirements.txt
cp .env.example .env      # e preencha os três valores
python app.py             # http://127.0.0.1:5000
```

Sem o `.env` o serviço sobe, mas não conecta: `/health` responde **503** dizendo
`"credenciais ausentes"`, e a leitura devolve lista vazia em vez de quebrar.

Para gerar leituras sem hardware, com o servidor no ar:

```bash
python fake_sensor.py
```

### Variáveis de ambiente

| | |
|---|---|
| `SUPABASE_URL` | URL do projeto |
| `SUPABASE_INGESTAO_KEY` | chave da ingestão — papel `dormio_ingestao`, **privilégio mínimo** |
| `SUPABASE_SERVICE_ROLE_KEY` | *fallback* — ignora RLS, acesso total. Só até a de cima existir |
| `SUPABASE_ANON_KEY` | chave publicável — valida o JWT e monta o cliente do usuário |

---

## Rotação da chave de ingestão

O caminho de ingestão (`POST /api/data`) usa o papel `dormio_ingestao`, criado
pela migração `005`. Ele tem `EXECUTE` em três funções e **nenhum privilégio de
tabela**: se a chave vazar, o pior caso é inserir leitura em nome de um
dispositivo cujo token o atacante já tenha. Não há leitura de dado de usuário.

A chave não sai do painel do Supabase — o painel só emite para `anon` e
`service_role`. É um JWT assinado com o **JWT secret do projeto**, carregando
`{"role": "dormio_ingestao"}`; o PostgREST faz `SET ROLE` a partir dessa claim.

### Emitir (ou rotacionar)

```bash
# 1. Supabase > Settings > API > JWT Settings > JWT Secret
export SUPABASE_JWT_SECRET='...'

# 2. Emitir. O segredo vai por variável de ambiente, nunca por argumento:
#    argumento fica no histórico do shell e na lista de processos.
python scripts/emitir_chave_de_ingestao.py --anos 1

# 3. Copiar a linha SUPABASE_INGESTAO_KEY=... para:
#    · web-app/.env            (local)
#    · Vercel > Settings > Environment Variables  (produção)

# 4. Redeploy, e conferir:
python web-app/teste_conexao.py     # deve dizer "papel dormio_ingestao"
curl -s https://SEU-APP/health      # deve responder 200
```

### Se a chave vazou

1. **Não precisa rotacionar o JWT secret do projeto** — isso invalidaria
   também todas as sessões de usuário. Em vez disso:
2. `revoke dormio_ingestao from authenticator;` no SQL Editor. O token vazado
   para de funcionar na hora, porque o PostgREST não consegue mais assumir o
   papel. **A ingestão para junto** — é uma parada controlada, e é o que se
   quer: melhor o ESP32 acumular no buffer (`HW-05`) do que aceitar escrita de
   terceiro.
3. Emitir chave nova com `--anos` curto, configurar, e
   `grant dormio_ingestao to authenticator;` de volta.
4. Auditar o que foi inserido na janela:
   `select device_id, count(*), min(created_at), max(created_at) from sleep_data
    where created_at > '<data do vazamento>' group by device_id;`
   Leitura fabricada aparece como volume anômalo por dispositivo — o dado
   plantado é identificável porque o atacante não controla `created_at`.
5. Revogar os tokens dos dispositivos cujos hashes ele possa ter obtido
   (`POST /api/devices/<id>/revogar`) e parear de novo.

Se o que vazou foi a `service_role`, aí sim é rotação no painel do Supabase e
revisão de tudo: aquela chave ignora o RLS.

---

## Banco de dados

As migrações ficam em [`migrations/`](migrations) e são aplicadas manualmente no SQL Editor
do Supabase, em ordem numérica. O `README` da pasta explica a ordem e o que conferir depois
de cada uma.

---

## Testes

```bash
python -m pytest tests/ -v
```

**O Supabase é sempre mockado** — nenhum teste depende de credencial ou de rede, e a suíte
roda no CI a cada push.

Vale saber de uma limitação que já custou um bug em produção: os testes mockam
`get_client()`, então a linha que cria o cliente nunca executa neles. Um `print` com emoji
ali dentro derrubava a API inteira em console Windows, com 70 testes passando. Por isso há
testes que leem o próprio código-fonte (`test_resiliencia.py`) e falham se um `print`
reaparecer ou se uma mensagem de log ganhar caractere fora de ASCII.

---

## Estrutura

```plaintext
web-app/
├── app.py               # entrypoint; expõe `app` para o Vercel importar
├── routes.py            # rotas da API
├── auth.py              # require_auth — valida o JWT do usuário
├── device_auth.py       # token de dispositivo: geração e hash SHA-256
├── dispositivos.py      # operações de devices sob o RLS do usuário
├── validacao.py         # validação da leitura antes de persistir
├── database.py          # camada Supabase
├── fake_sensor.py       # simulador de leituras
├── migrations/          # SQL versionado
└── tests/               # pytest
```
