# DIAG-04 — Modelo de dados, sequência autenticada e privilégio

> **Item do backlog:** `DIAG-04` ("diagrama de sequência do fluxo autenticado + modelo ER
> com `devices` e `profiles`"), ampliado para cobrir também RLS e privilégio mínimo —
> o backlog foi levantado antes de `SEC-06`/`SEC-07` fecharem. É também a parte pendente
> do `DOC-05`.
> **Onde entra no TCC:** capítulo de Desenvolvimento, seção de persistência e segurança
> (figuras A e B) e seção de autenticação (figura C). A figura B é o que sustenta a
> seção de conformidade com a LGPD.
> **Estado do código:** verificado em `2026-09-29`, após as migrações `001` a `007`.
> A migração `002` (backfill do dono) **não foi executada no Supabase** — item `DATA-03`.

Convenções de leitura: ver `DIAG-01`.

---

## A — Modelo entidade-relacionamento

```mermaid
erDiagram
    AUTH_USERS ||--|| PROFILES : "1:1 via handle_new_user()"
    AUTH_USERS ||--o{ DEVICES : "on delete cascade"
    AUTH_USERS ||--o{ SLEEP_DATA : "on delete cascade"
    DEVICES ||--|| DEVICE_TOKENS : "1:1 · on delete cascade"
    DEVICES ||--o{ SLEEP_DATA : "on delete set null"

    AUTH_USERS {
        uuid id PK "gerida pelo Supabase"
        text email
    }
    PROFILES {
        uuid id PK,FK "= auth.users.id"
        text nome
        integer idade "check 0..149"
        timestamptz created_at
        timestamptz updated_at
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
    end

    subgraph TABS["TABELAS (RLS habilitado em todas)"]
        T1["profiles<br/>select/insert/update/delete own"]
        T2["devices<br/>select/insert/update/delete own"]
        T3["sleep_data<br/>select own · delete own<br/>SEM policy de insert"]
        T4["device_tokens<br/>RLS + NENHUM GRANT<br/>inalcancavel pelo cliente"]
    end

    ANON -->|"apenas auth: signUp, signIn"| AUTHD
    AUTHD -->|"GRANT EXECUTE"| F3
    AUTHD -->|"GRANT EXECUTE"| F4
    AUTHD -->|"GRANT EXECUTE"| F5
    AUTHD -->|"GRANT EXECUTE"| F6
    AUTHD -->|"select/update/delete filtrados pelo RLS"| T1
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

**Verificação, não afirmação.** O que o diagrama diz sobre RLS é coberto por 105 testes
contra um PostgreSQL real (`web-app/tests/rls/`), sem *mock*, incluindo invariantes de
catálogo (tabela nova sem RLS, `using (true)`, policy para `anon`). A suíte foi verificada
por mutação: 18 sabotadores introduzidos, todos detectados
(`tests/rls/verificar_por_mutacao.py`).

**O caso de borda honesto do `apagar_minha_conta()`:** `auth.users` pertence ao Supabase, e
o `GRANT DELETE` nela pode não existir no projeto. Quando não existe, os dados de sono,
dispositivos e perfil são apagados e a rota responde `conta_de_acesso_removida: false` com
aviso. Isso é pendência de conformidade registrada em log como `WARNING`, não sucesso
silencioso. **A tela que exerce esse direito ainda não existe** (`UI-10`): hoje só há a
rota `DELETE /api/me`.

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
```

**O pareamento, que antecede tudo isso:** `POST /api/devices` gera um token aleatório,
guarda apenas o SHA-256 em `device_tokens` via `parear_dispositivo()` e devolve o token em
claro **uma única vez**. Não há caminho de recuperação — perdido o token, repareia-se o
dispositivo. A revogação (`POST /api/devices/<id>/revogar`) é *soft delete*:
`devices.revoked_at` é preenchido e as funções deixam de resolver aquele token.
