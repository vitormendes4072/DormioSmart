# DIAG-04 — Modelo de dados, sequência autenticada e privilégio

> **Item do backlog:** `DIAG-04` ("diagrama de sequência do fluxo autenticado + modelo ER
> com `devices` e `profiles`"), ampliado para cobrir também RLS e privilégio mínimo —
> o backlog foi levantado antes de `SEC-06`/`SEC-07` fecharem. É também a parte pendente
> do `DOC-05`.
> **Onde entra no TCC:** capítulo de Desenvolvimento, seção de persistência e segurança
> (figuras A e B) e seção de autenticação (figura C). A figura B é o que sustenta a
> seção de conformidade com a LGPD.
> **Estado do código:** verificado em `2026-09-29` e **revisado em `2026-10-17`**, após
> as migrações `001` a `008`.
> **Migrações escritas e NÃO executadas no Supabase:** a `002` (backfill do dono, item
> `DATA-03`) e a **`008`** (`PERFIL-01`). Os dois diagramas abaixo descrevem o esquema
> **com a `008` aplicada** — ver a nota ao fim da figura A para o que muda enquanto ela
> não rodar.

> ✏️ **O que o `PERFIL-01` mudou aqui, e por que este diagrama era o motivo de decidir
> antes.** O item dizia: *"decidir antes do `DIAG-04`: o modelo ER é material de banca, e
> um diagrama que mostra `profiles` com `nome` e `idade` documenta como projeto uma
> tabela cujas colunas nada lê."* Era isso. O ER de 29/09 desenhava `profiles.nome` e
> `profiles.idade` como se fossem dado do sistema; `nome` era cópia escrita uma vez pelo
> gatilho do signup e lida por nada, e `idade` estava vazia para todos os titulares. O
> diagrama não estava errado sobre o **esquema** e estava errado sobre o **projeto** — e
> a diferença só aparece para quem pergunta "quem lê esta coluna?", que é exatamente o
> que uma banca pergunta. Agora as duas colunas são lidas, e a figura A diz por quem.

Convenções de leitura: ver `DIAG-01`.

---

## A — Modelo entidade-relacionamento

```mermaid
erDiagram
    AUTH_USERS ||--|| PROFILES : "1:1 · semeada por handle_new_user()"
    AUTH_USERS ||--o{ DEVICES : "on delete cascade"
    AUTH_USERS ||--o{ SLEEP_DATA : "on delete cascade"
    DEVICES ||--|| DEVICE_TOKENS : "1:1 · on delete cascade"
    DEVICES ||--o{ SLEEP_DATA : "on delete set null"

    AUTH_USERS {
        uuid id PK "gerida pelo Supabase"
        text email "CREDENCIAL · troca por link de confirmacao"
        jsonb raw_user_meta_data "nome: INSUMO DE CRIACAO · lido 1x, nunca exibido"
    }
    PROFILES {
        uuid id PK,FK "= auth.users.id"
        text nome "FONTE DE VERDADE do nome exibido · check <= 200 (008)"
        integer idade "OPCIONAL · check 0..149 · finalidade: aplicabilidade de coorte"
        timestamptz created_at
        timestamptz updated_at "mantida por gatilho desde a 008"
    }
    DEVICES {
        uuid id PK
        uuid user_id FK "not null"
        text nome "default Dormio Smart"
        text tipo "check travesseiro|celular"
        timestamptz revoked_at "revogacao = soft delete"
        timestamptz last_seen_at
        timestamptz created_at
    }
    DEVICE_TOKENS {
        uuid device_id PK,FK
        text token_hash UK "SHA-256 hex · NUNCA o token em claro"
        timestamptz created_at
    }
    SLEEP_DATA {
        bigserial id PK
        uuid user_id FK "anulavel ate o DATA-03"
        uuid device_id FK "anulavel"
        double accel_x_y_z "m/s2"
        double gyro_x_y_z "rad/s · nao alimenta decisao"
        double temp "C · so MPU6050"
        double movimento_total "magnitude |a|"
        text status "movimento|repouso — limiar do firmware"
        timestamptz captured_at "MEDICAO · nulo = nao informado"
        timestamptz created_at "RECEBIMENTO"
        integer epoca_segundos "nulo = amostra instantanea"
        text metodo_agregacao "obrigatorio se epoca_segundos"
        integer amostras
    }
```

**A decisão que o ER esconde se não for dita:** `token_hash` **saiu** de `devices` na
migração `007` e virou a tabela `device_tokens`. A razão é que `devices` é exposta ao
PostgREST, e `GRANT` de tabela no PostgreSQL alcança **toda** coluna — não existe revogar
uma coluna de um grant de tabela. Com a credencial em outra tabela, sem `GRANT` nenhum
para `anon`/`authenticated`, ela não é alcançável pelo cliente.

**O que ainda é anulável e por quê:** `sleep_data.user_id` e `device_id` nasceram
anuláveis porque as linhas coletadas antes da migração `001` não têm dono. O backfill
está escrito (`migrations/002_backfill_dono_dos_dados.sql`) e **não foi rodado** —
enquanto isso, o painel de uma conta nova nasce vazio (`DATA-03`).

**A decisão que o ER esconde se não for dita, nº 2: o nome existe em dois lugares, e só
um deles é lido.** `profiles.nome` é a fonte de verdade; `raw_user_meta_data.nome` é o
**insumo de criação** — o valor digitado no cadastro, lido uma vez pelo gatilho
`handle_new_user` para semear a linha de `profiles`, e depois disso lido por **nada**. A
duplicidade não é resolvida por sincronização: é resolvida por **leitor único** e
**destino único por campo** (nome e idade pela rota `/api/me/perfil`; e-mail pelo Auth,
porque é credencial). Um diagrama que mostrasse os dois campos de nome sem dizer qual
manda documentaria uma ambiguidade que o sistema não tem. O raciocínio inteiro está em
`docs/DECISAO-FONTE-DO-PERFIL.md`, e a regra do leitor único é catraca verificada em
`frontend/src/fonteDoNomeDoPerfil.test.ts`.

**A linha que falta no diagrama, e é de processo:** `profiles` pode **não ter linha** para
um usuário existente. Não é hipótese — `migrations/DIAGNOSTICO-perfil-nao-criado.sql`
existe porque já aconteceu (o gatilho não existia no projeto). Enquanto a tabela era
inerte isso era invisível; com ela canônica, `GET /api/me/perfil` **repara** a ausência,
semeando pelo metadado. Por isso o ER mostra a relação como `1:1` e o texto diz que ela é
*semeada*: o esquema garante no máximo uma linha, não que ela exista.

> ⚠️ **Enquanto a migração `008` não for aplicada:** o `check` de 200 em `nome` e o
> gatilho de `updated_at` **não existem no banco**, e `profiles.updated_at` continua
> congelado no instante da criação. A rota de perfil funciona sem a `008` — ela grava
> `nome` e `idade` pelas policies que existem desde a `001`. O que falta é o teto do
> caminho que não passa pelo Flask (o navegador fala direto com o PostgREST) e a
> honestidade da coluna de data.

---

## B — Quem alcança o quê, e com qual privilégio

O eixo do diagrama é: **nenhum caminho de escrita recebe o dono como parâmetro**.

```mermaid
flowchart TB
    subgraph PAPEIS["PAPEIS"]
        ANON["anon<br/>navegador nao autenticado"]
        AUTHD["authenticated<br/>JWT do usuario · auth.uid()"]
        ING["dormio_ingestao<br/>nologin noinherit<br/>sem BYPASSRLS, sem CREATEROLE<br/>NENHUM privilegio de tabela"]
        SRV["service_role<br/>(APOSENTADA da ingestao na v2.4.0)"]
    end

    subgraph FUNCS["FUNCOES security definer (search_path = '')"]
        F1["resolver_dispositivo(token_hash)<br/>-> (id, user_id) · nao devolve o hash"]
        F2["registrar_leitura(token_hash, jsonb)<br/>dono derivado do token, aqui dentro"]
        F3["registrar_leitura_da_sessao(device_id, jsonb)<br/>dono = auth.uid() · confere posse"]
        F4["parear_dispositivo(nome, tipo, token_hash)"]
        F5["apagar_minha_conta()<br/>sem parametro de usuario"]
        F6["sanidade()"]
        F7["tocar_updated_at()<br/>gatilho da 008 · SEM security definer<br/>SEM execute para papel algum"]
    end

    subgraph TABS["TABELAS (RLS habilitado em todas)"]
        T1["profiles<br/>select/insert/update/delete own<br/>FONTE DE VERDADE do perfil"]
        T2["devices<br/>select/insert/update/delete own"]
        T3["sleep_data<br/>select own · delete own<br/>SEM policy de insert"]
        T4["device_tokens<br/>RLS + NENHUM GRANT<br/>inalcancavel pelo cliente"]
    end

    ANON -->|"apenas auth: signUp, signIn"| AUTHD
    AUTHD -->|"GRANT EXECUTE"| F3
    AUTHD -->|"GRANT EXECUTE"| F4
    AUTHD -->|"GRANT EXECUTE"| F5
    AUTHD -->|"GRANT EXECUTE"| F6
    AUTHD -->|"select/insert/update/delete filtrados pelo RLS<br/>o upsert da rota de perfil passa por aqui"| T1
    T1 -.->|"before update"| F7
    AUTHD --> T2
    AUTHD --> T3
    ING -->|"GRANT EXECUTE — e so"| F1
    ING --> F2
    ING --> F6

    F2 --> T3
    F2 -->|"atualiza last_seen_at na mesma chamada"| T2
    F3 --> T3
    F1 --> T4
    F2 --> T4
    F4 --> T2
    F4 --> T4
    F5 --> T1
    F5 --> T2
    F5 --> T3
    F5 -.->|"delete em auth.users — depende de GRANT<br/>que pode nao existir no projeto"| T5["auth.users"]

    SRV -.->|"fallback de compatibilidade em database.py<br/>ate SUPABASE_INGESTAO_KEY ser emitida"| F2

    classDef futuro stroke-dasharray: 6 4;
    class SRV futuro;
```

**Verificação, não afirmação.** O que o diagrama diz sobre RLS é coberto por **146 testes**
contra um PostgreSQL real (`web-app/tests/rls/`), sem *mock*, incluindo invariantes de
catálogo (tabela nova sem RLS, `using (true)`, policy para `anon`). A suíte foi verificada
por mutação: **30 sabotadores** introduzidos, todos detectados
(`tests/rls/verificar_por_mutacao.py`). *(Eram 105 testes e 18 sabotadores em 29/09.)*

**Dois achados de 17/10 que mudam o que esta figura pode afirmar, e os dois vieram da
verificação por mutação, não da leitura:**

1. **`create function` concede `EXECUTE` a `PUBLIC` por padrão no PostgreSQL.** A
   migração `008`, ao criar `tocar_updated_at()`, **ampliava** o que o papel
   `dormio_ingestao` podia executar — o papel que a `005` existe para manter com
   `EXECUTE` em exatamente três funções. Quem acusou foi
   `test_o_papel_executa_exatamente_tres_funcoes`, na primeira execução da migração.
   Daí o `revoke` na `008` e o `F7` do diagrama dizer *"sem execute para papel algum"*:
   gatilho não precisa de `GRANT` para disparar, porque o privilégio é conferido na
   criação do gatilho.
2. **`test_ana_nao_cria_profile_para_o_bruno` barrava pela chave estrangeira, não pela
   policy.** Ele usava um uuid inventado, que não existe em `auth.users`. Passava com
   `profiles_insert_own` escancarada — medido. Corrigido com uma terceira usuária real
   **sem perfil**, que é o único cenário em que a policy de `insert` fica sozinha no
   caminho. E o par de `upsert` mostrou que **dois barramentos em série escondem um ao
   outro**: o teste da vítima *com* perfil não detecta policy de `insert` larga, porque a
   de `update` recusa primeiro.

**O caso de borda honesto do `apagar_minha_conta()`:** `auth.users` pertence ao Supabase, e
o `GRANT DELETE` nela pode não existir no projeto. Quando não existe, os dados de sono,
dispositivos e perfil são apagados e a rota responde `conta_de_acesso_removida: false` com
aviso. Isso é pendência de conformidade registrada em log como `WARNING`, não sucesso
silencioso.

> ✏️ **Correção de 2026-10-17.** Esta linha dizia *"a tela que exerce esse direito ainda
> não existe (`UI-10`): hoje só há a rota `DELETE /api/me`"*. A tela existe desde
> 17/10 — e o componente desde 29/09, sem que nenhum arquivo versionado o importasse,
> que é a história do `UI-10` e a ocorrência 4 do §6 das lições. **Este arquivo era o
> quarto a carregar uma afirmação desatualizada sobre aquela tela** — a entrada de 17/10
> (iii) do diário reporta três (backlog, `LGPD-ELIMINACAO.md` e a política), e esta
> passou. Achada por varredura própria ao fechar o `PERFIL-01`, com os termos *"ainda não
> existe"*, *"não há tela"* e *"existe como rota"* em `docs/`, `*.md`, `frontend/src/` e
> `web-app/`. A mesma varredura achou outras duas, em `CLAUDE.md`.

---

## C — Sequência do fluxo autenticado

Dois caminhos de ingestão e um de leitura. O `user_id` nunca vem do corpo da requisição
em nenhum deles.

```mermaid
sequenceDiagram
    autonumber
    participant ESP as ESP32 (envio-continuo.ino)
    participant CEL as Navegador (Coletar.tsx)
    participant FL as Flask (routes.py)
    participant PG as PostgreSQL (Supabase)

    Note over ESP,PG: CAMINHO 1 — dispositivo em campo, sem sessao
    ESP->>FL: POST /api/data<br/>X-Device-Token: <token de 43 chars>
    FL->>FL: identificar_caminho() -> "token"
    FL->>FL: hash_token() = SHA-256 do token
    FL->>PG: resolver_dispositivo(token_hash)
    PG-->>FL: (device_id, user_id) ou vazio se revogado
    alt token ausente, desconhecido ou revogado
        FL-->>ESP: 401 — a mesma resposta para os tres casos
    end
    FL->>FL: validar_leitura() + validar_captacao() — SEC-03
    alt payload invalido
        FL-->>ESP: 400 — recusa deterministica, sai da fila do firmware
    end
    FL->>PG: registrar_leitura(token_hash, payload SEM user_id)
    PG->>PG: resolve o dono do token, insere em sleep_data,<br/>atualiza devices.last_seen_at
    PG-->>FL: id da linha, ou nulo
    alt nada persistiu
        FL-->>ESP: 503 — a epoca CONTINUA no buffer (FIX-02)
    else
        FL-->>ESP: 201 — confirmar_entrega() no buffer
    end

    Note over CEL,PG: CAMINHO 2 — celular, com sessao
    CEL->>FL: POST /api/data<br/>Authorization: Bearer <JWT> + device_id no corpo
    FL->>PG: validar_token_de_usuario(JWT)
    PG-->>FL: user_id
    FL->>PG: buscar_do_dono(user_id, device_id)
    alt inexistente, revogado ou de outra pessoa
        FL-->>CEL: 404 — mesma resposta para os tres, para nao vazar ids
    end
    FL->>PG: registrar_leitura_da_sessao(device_id, payload)<br/>pelo cliente do USUARIO, nao por chave privilegiada
    PG->>PG: dono = auth.uid(), confere posse, insere
    PG-->>FL: id da linha
    FL-->>CEL: 201

    Note over CEL,PG: CAMINHO 3 — leitura pelo painel

    CEL->>FL: GET /api/sleep-history?device_id&desde&ate&limite<br/>Authorization: Bearer <JWT>
    FL->>FL: ler_parametros() — valida uuid, instante, limite (teto 2000)
    FL->>PG: select em sleep_data com o JWT do usuario
    PG->>PG: RLS filtra por auth.uid() — nao e codigo Python que filtra
    PG-->>FL: linhas do dono, mais recentes primeiro
    FL-->>CEL: 200 + JSON

    Note over CEL,PG: CAMINHO 4 — perfil (PERFIL-01) · nome e idade
    CEL->>FL: GET /api/me/perfil<br/>Authorization: Bearer <JWT>
    FL->>PG: select nome, idade em profiles, pelo JWT do usuario
    alt nao ha linha · gatilho ausente, ver DIAGNOSTICO-perfil-nao-criado.sql
        FL->>FL: le nome de raw_user_meta_data — UNICA leitura, e so aqui
        FL->>PG: upsert do perfil, semeado · log WARNING
        FL-->>CEL: 200 + perfil_criado_agora: true
    else leitura falhou — nao e o mesmo que "nao ha linha"
        FL-->>CEL: 503 — nao repara por cima de banco fora do ar
    else a linha existe
        PG-->>FL: nome, idade, updated_at
        FL-->>CEL: 200 + perfil_criado_agora: false
    end

    CEL->>FL: PATCH /api/me/perfil<br/>{nome?, idade?} — SO o que mudou
    FL->>FL: valida tipo, faixa e tamanho · campo desconhecido (id, user_id) = 400
    FL->>PG: upsert em profiles pelo JWT<br/>id = auth.uid() nas policies de insert E de update
    PG->>PG: gatilho tocar_updated_at (008)
    PG-->>FL: a linha COMO FICOU
    alt nada persistiu
        FL-->>CEL: 503 — nao responde 200 sem escrita confirmada (FIX-02)
    else
        FL-->>CEL: 200 + a linha do banco, nao o que foi pedido
    end
    CEL->>CEL: limpa o residuo: updateUser({data:{nome:null}})<br/>DEPOIS do PATCH · falha NAO desfaz a correcao
```

**Por que o caminho 4 tem um `GET` que escreve, dito aqui porque é o que mais surpreende
quem lê o diagrama:** `profiles` pode não ter linha para um usuário que existe, e isso já
aconteceu neste projeto. Com a tabela canônica, linha ausente deixou de ser detalhe de
esquema e passou a ser nome em branco na tela de quem digitou o nome no cadastro. O
reparo é **idempotente**, que é a propriedade que de fato importa num `GET`.

**E por que a limpeza do resíduo está no navegador, e não no Flask:** `updateUser` age
sobre a **sessão** de quem chama, e o cliente do Flask só autentica o PostgREST. Fazer
isso no servidor exigiria a API de administração — papel privilegiado, recusado pelo
`SEC-06`. O navegador é o único lugar onde essa escrita acontece com a credencial do
próprio titular.

**O pareamento, que antecede tudo isso:** `POST /api/devices` gera um token aleatório,
guarda apenas o SHA-256 em `device_tokens` via `parear_dispositivo()` e devolve o token em
claro **uma única vez**. Não há caminho de recuperação — perdido o token, repareia-se o
dispositivo. A revogação (`POST /api/devices/<id>/revogar`) é *soft delete*:
`devices.revoked_at` é preenchido e as funções deixam de resolver aquele token.
