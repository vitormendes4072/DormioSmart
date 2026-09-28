# Testes de RLS — isolamento entre usuários (SEC-05 / INFRA-01)

O resto de `web-app/tests/` mocka o Supabase. Está certo: aqueles testes
verificam a lógica do Flask, e o mock é o que a isola. Mas a consequência ficou
implícita por tempo demais — **nenhum teste da suíte tocava uma policy**. O
isolamento entre usuários, que é a garantia central do sistema, era uma
afirmação escrita em SQL e conferida a olho uma vez no SQL Editor.

Os testes desta pasta não mockam nada. Eles falam com um Postgres real, com as
migrações reais de `web-app/migrations/` aplicadas, e tentam de fato ler,
escrever, atualizar e apagar dado de outro usuário.

## Rodando

Precisa de um Postgres descartável (qualquer versão ≥ 13) e do `psycopg2`.
**Sem a variável de ambiente, os testes são pulados** — eles não caem para mock
e não tentam se conectar na instância de produção.

```bash
pip install psycopg2-binary

# Docker é o caminho mais curto
docker run --rm -d --name dormio-rls -e POSTGRES_PASSWORD=postgres -p 5433:5432 postgres:16

export DORMIO_RLS_DATABASE_URL="postgresql://postgres:postgres@127.0.0.1:5433/postgres"
cd web-app && pytest tests/rls -v
```

Sem Docker, serve qualquer Postgres local — inclusive um `initdb` num diretório
temporário. O usuário da conexão precisa poder `create role` e
`drop schema cascade`.

### ⚠️ O setup destrói o schema de destino

`drop schema public cascade` roda no começo da sessão de teste. O `conftest.py`
recusa host remoto, e recusa `*.supabase.co` incondicionalmente — mas aponte
para um banco descartável de qualquer forma.

**Nunca aponte para a instância do Supabase do trabalho.** Não é só o risco de
apagar: a suíte cria contas, escreve leitura e revoga dispositivo. Nada disso
deve encostar em dado real.

## Como o Supabase é reproduzido

`esquema_base.sql` recria só os primitivos de que as migrações dependem:
o schema `auth`, `auth.users`, `auth.uid()`, os papéis `anon` /
`authenticated` / `service_role` e os GRANTs que o Supabase aplica em `public`.
Em cima disso, as migrações **001**, **003** e **004** são aplicadas do disco,
sem nenhuma adaptação. As policies sob teste são as do repositório — não há
cópia delas aqui, porque uma cópia envelheceria em silêncio e a suíte passaria
a testar a si mesma.

A **002** fica de fora: ela exige edição manual (o e-mail de destino), atribui
posse de dado e não cria nem altera policy nenhuma.

Três decisões merecem ser explícitas:

**1. O teste fala SQL, não HTTP.** Não porque seja mais fácil, mas porque a
superfície exposta é maior que as rotas do Flask. O frontend usa a chave `anon`,
que é pública por design (está dito em `frontend/src/lib/supabase.ts`) — logo
qualquer pessoa com uma conta tem a chave e um JWT válido, e com os dois chama o
PostgREST com o filtro que quiser, sem passar por rota. `SET ROLE authenticated`
com a claim `sub` no GUC é exatamente o que o PostgREST monta por requisição.
O que a Ana alcança no teste é o que a Ana alcançaria com um `curl`.

**2. Os GRANTs amplos são fidelidade, não conveniência.** No Supabase,
`authenticated` **tem** privilégio de tabela em `public`; o que barra o acesso é
o RLS. Se a suíte rodasse sem GRANT, todo acesso indevido seria negado por falta
de permissão e passaria sem exercitar policy alguma.

**3. Todo caminho negativo tem um caminho feliz ao lado.** Uma suíte de
segurança em que tudo está bloqueado por um erro de setup produz exatamente o
relatório verde que se quer ver. Os testes de caminho feliz (a Ana lê o próprio
dado, cria o próprio dispositivo, edita o próprio perfil) são o que impede isso.

## Estrutura

| Arquivo | O quê |
|---|---|
| `esquema_base.sql` | Primitivos do Supabase + `sleep_data` no estado pré-001 |
| `grants_pos_migracao.sql` | GRANTs nas tabelas criadas pela 001 |
| `conftest.py` | Aplica esquema e migrações, semeia duas contas, monta sessões autenticadas |
| `test_rls_isolamento.py` | O adversarial: A tenta alcançar o dado de B por todo comando, nas três tabelas |
| `test_rls_estrutura.py` | Invariantes do catálogo: RLS ligado, policies esperadas, nada permissivo |

`test_rls_estrutura.py` existe porque os testes de acesso só provam que o que
existe hoje se comporta bem. Eles não pegam uma tabela nova que nasça sem RLS
(não há teste pedindo dado de uma tabela que ninguém escreveu ainda), nem um
`using (true)` acrescentado para depurar — que é indistinguível de RLS
desligado, mas mantém `rowsecurity = true` e o painel do Supabase mostrando a
tabela como protegida.

## No CI

O job `rls` do workflow sobe um serviço Postgres e roda esta pasta a cada push,
**em matriz de versão (14 e 16)**. RLS e privilégio são área onde o Postgres muda
de comportamento entre *majors* — a 15 mudou o dono e os privilégios do schema
`public`, por exemplo — e o harness foi desenvolvido na 14. Rodar nas duas faz a
diferença aparecer no CI, com o diff na mão.

A etapa que importa ali é **"Conferir que os testes de RLS não foram pulados"**.
`pytest.skip` não falha o job: se a variável de ambiente sumisse, se o serviço
não subisse ou se o `psycopg2` deixasse de instalar, esta pasta seria pulada e o
CI ficaria verde — anunciando uma cobertura de segurança que não rodou. Pulo
silencioso é pior que falha, porque ninguém investiga o verde. Os três cenários
foram exercitados à mão antes de a etapa entrar.

## Verificação por mutação

Uma suíte de segurança que nunca falhou não provou nada. O script
`verificar_por_mutacao.py` aplica **25 sabotagens** ao esquema, uma por vez, e
confere que a suíte acusa cada uma — e que o teste que *nomeadamente* deveria
acusá-la esteja entre os que caem, para a suíte não passar por acidente.

```bash
python tests/rls/verificar_por_mutacao.py
python tests/rls/verificar_por_mutacao.py --apenas rls_desligado   # investigar um
```

Rodar depois de **toda** mudança de esquema. Roda no CI, na versão 16.

Duas coisas que o script aprendeu a distinguir, porque confundir manda consertar
o lugar errado:

- **sabotagem não detectada** — a suíte passou, e é regressão dela;
- **sabotador quebrado** — o SQL não aplicou, o esquema não subiu, e o defeito é
  no sabotador. Aconteceu de verdade: dois sabotadores referenciavam
  `devices.token_hash` depois de a migração 007 remover a coluna.

Amostra do que cada sabotagem derruba:

| Sabotagem | Testes que caem |
|---|---|
| `disable row level security` em `sleep_data` | 18 |
| `create policy ... using (true)` em `sleep_data` | 7 |
| `devices_update_own` sem `with check` | 1 |
| Policy de select para `anon` em `profiles` | 4 |
| Tabela nova com `user_id` e sem RLS | 1 |
| `security definer` sem `search_path` fixo | 1–2 |
| Papel de ingestão ganha `select` em `sleep_data` | 3 |
| Papel de ingestão ganha `BYPASSRLS` | 1 |
| `registrar_leitura` aceita o dono pelo JSON | 2 |
| `apagar_minha_conta` ganha parâmetro de usuário | 7 |
| `sleep_data_delete_own` com `using (true)` | 3 |
| `token_hash` recriada como coluna de `devices` | 3 |
| `authenticated` ganha `select` em `device_tokens` | 1 |
| `parear_dispositivo` ganha parâmetro de usuário | 3 |
| `resolver_dispositivo` esquece o `revoked_at` | 2 |
| **GRANTs retirados de `authenticated`** | **32 (todos os caminhos felizes)** |

O último é o mais importante: ele simula "tudo quebrado". Se a suíte passasse
nesse cenário, ela não valeria nada.

Dois furos da própria suíte foram encontrados por este script, e não por
revisão:

1. **Sobrecarga escapava dos testes de assinatura.** Acrescentar
   `parear_dispositivo(text,text,text,uuid)` *sem* remover a versão de três
   argumentos passava batido — o teste olhava só a primeira linha do `pg_proc`.
   E é exatamente assim que um parâmetro de dono entraria na prática: ninguém
   apaga a função boa, acrescenta uma "versão para o admin" ao lado.
2. **Estado vazando entre execuções.** Papel é objeto de *cluster*, não de
   schema, então o `drop schema cascade` do setup não o alcançava e um
   `alter role ... bypassrls` sobrevivia para a execução seguinte.

## O que estes testes NÃO cobrem

- **O GoTrue.** Signup, confirmação de e-mail, expiração e revogação de token
  não estão aqui. Para o RLS, um usuário é um UUID na claim `sub`.
- **O PostgREST em si.** A tradução de querystring para SQL não é testada;
  o que é testado é o SQL que ela produz.
- **O caminho de ingestão.** `POST /api/data` usa `service_role`, que tem
  `BYPASSRLS` — o RLS **não protege nada ali**, de propósito (SEC-02).
  `test_service_role_ignora_o_rls` documenta a assimetria em vez de deixá-la
  implícita. A consequência: se a `service_role` vazar, ou se uma rota montar a
  consulta com ela em vez do JWT do usuário, o isolamento desaparece e nenhum
  teste desta pasta cai. É por isso que `_cliente_do_usuario()` em `routes.py`
  é o ponto mais sensível daquele arquivo.
- **`force row level security`.** As tabelas não têm. Isso significa que o
  DONO delas ignora RLS — no Supabase, o papel `postgres`. Não é exposição para
  usuário do app, mas é a razão de o `conftest.py` nunca exercitar policy pela
  conexão do dono.
