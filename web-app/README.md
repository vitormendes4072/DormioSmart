# API — Dormio Smart

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
| `SUPABASE_SERVICE_ROLE_KEY` | chave secreta — ignora RLS, **só no servidor** |
| `SUPABASE_ANON_KEY` | chave publicável — valida o JWT e monta o cliente do usuário |

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
