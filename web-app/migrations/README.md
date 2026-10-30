# Migrações do banco

Scripts SQL versionados, aplicados **em ordem numérica** no Supabase
(`SQL Editor` → colar → `Run`). Todos são idempotentes: reaplicar não quebra.

| # | Arquivo | Item | O que faz |
|---|---|---|---|
| 001 | `001_multiusuario.sql` | SEC-04 | `profiles`, `devices`, `user_id`/`device_id` em `sleep_data`, políticas RLS por dono, trigger de criação de perfil |
| 002 | `002_backfill_dono_dos_dados.sql` | DATA-03 | Associa as leituras órfãs (anteriores ao 001) a uma conta. **Requer edição** — troque o e-mail antes de rodar. Desnecessária se o diagnóstico contar 0 leituras sem dono (o caso da produção em 28/10). |
| 003 | `003_padroniza_nome_do_dispositivo.sql` | — | Nome padrão do dispositivo `Dormio Smart` → `Smart Dormio`. Não afeta quem deu nome próprio. |
| 004 | `004_tipo_de_dispositivo_e_agregacao.sql` | DATA-05 | `devices.tipo` (`travesseiro`/`celular`), `captured_at` e campos de agregação em `sleep_data`, índice por dispositivo. |
| 005 | `005_papel_de_ingestao_minimo.sql` | SEC-06 | Papel `dormio_ingestao` e as funções de ingestão. A chave do papel é emitida à parte — ver `scripts/emitir_chave_de_ingestao.py`. |
| 006 | `006_direito_de_eliminacao.sql` | SEC-07 | Policies de `delete` para as próprias linhas, `apagar_minha_conta()`. **Leia o cabeçalho**: a parte de `auth.users` pode não funcionar no seu projeto (na produção funcionou). |
| 007 | `007_credencial_fora_da_tabela_exposta.sql` | SEC-08 | Move `devices.token_hash` para `public.device_tokens`. **Quebra o código anterior ao release** (que lê `devices.token_hash`): aplicar **junto com o release**, nunca antes. |
| 008 | `008_perfil_como_fonte_de_verdade.sql` | PERFIL-01 | `profiles` como fonte de verdade: gatilho de `updated_at`, teto de tamanho do nome, papel de cada coluna declarado. |
| 009 | `009_privilegios_padrao_do_supabase.sql` | SEC-12 | Revoga **nominalmente** o que os privilégios padrão do Supabase dão a `anon`/`authenticated` em funções, e muda o padrão para funções futuras. Pode rodar antes ou depois da 007. |
| 010 | `010_vetor_de_caracteristicas.sql` | DATA-07b | O vetor de características: dez colunas nomeadas em `sleep_data`, restrição tudo-ou-nada, e as duas funções de gravação recriadas para extraí-las. **Aplicar ANTES do release do backend da v2.7.0** (`DATA-07f`): na ordem inversa, `f` validado seria descartado com `201`. Não quebra o backend anterior. ✅ Aplicada na produção em 30/10, antes do release (diagnóstico com 4 de 4 marcas). |

## Quais estão aplicadas no banco

Nada registra quais migrações rodaram — são aplicadas à mão. Para saber, rode
**`DIAGNOSTICO-migracoes-aplicadas.sql`** no SQL Editor: só lê, e devolve uma
linha por migração (`aplicada` true/false, o que falta). A consulta é conferida
no CI por `tests/migracoes/verificar_migracoes.py`, migração a migração, na
ordem numérica e na ordem real da produção.

**Estado da produção em 2026-10-29:** **todas aplicadas** — 001, 003, 004, 005, 006,
008, 009 e, depois do release (PR #5), 007; a 002 desnecessária. O diagnóstico deu
`aplicada = true` nas oito migrações de esquema.

## A armadilha dos privilégios padrão do Supabase

No Supabase, todo objeto que o `postgres` cria em `public` nasce com privilégio
**nominal** para `anon` e `authenticated` (ALL em tabela, EXECUTE em função).
`revoke ... from public` **não** alcança isso. Toda migração que crie função ou
tabela que o cliente não deve alcançar precisa revogar **pelo nome**:
`revoke ... from anon, authenticated`. Desde a 009, função nova não recebe mais o
grant nominal — mas o Postgres ainda dá EXECUTE a `PUBLIC`, então o
`revoke all on function ... from public` de cada migração continua necessário.

## Antes de aplicar

O `001` **altera o comportamento visível do app**: com o RLS por dono ativo, as
linhas existentes de `sleep_data` ficam sem `user_id` e deixam de aparecer para
qualquer usuário autenticado. Isso é esperado — o backfill é o item **DATA-03**.

O caminho de ingestão (`POST /api/data`) não é afetado: o backend usa
`service_role`, que ignora RLS por definição.

## Depois de aplicar

Rodar o bloco de VERIFICAÇÃO no rodapé do próprio script. Esperado:

- `rowsecurity = true` em `profiles`, `devices` e `sleep_data`
- 3 políticas em `profiles`, 4 em `devices`, 1 em `sleep_data`

O teste que realmente importa (usuário A não lê linha do usuário B) **existe
desde o SEC-05**: `web-app/tests/rls/` aplica estas migrações num Postgres
descartável e tenta de fato alcançar dado alheio. Rode depois de escrever
migração nova — e rode `tests/rls/verificar_por_mutacao.py` depois de qualquer
mudança de esquema, que é o que confere se a suíte ainda acusa.

## Ordem de execução com os itens de código

```
001  →  (criar uma conta)  →  002  →  AUTH-03
```

O **002 tem que rodar antes do AUTH-03**. Hoje a leitura usa `service_role`, que
ignora RLS, então tudo aparece no dashboard. No momento em que o AUTH-03 passar a
ler com o JWT do usuário, toda linha sem dono desaparece.
