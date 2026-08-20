# Migrações do banco

Scripts SQL versionados, aplicados **em ordem numérica** no Supabase
(`SQL Editor` → colar → `Run`). Todos são idempotentes: reaplicar não quebra.

| # | Arquivo | Item | O que faz |
|---|---|---|---|
| 001 | `001_multiusuario.sql` | SEC-04 | `profiles`, `devices`, `user_id`/`device_id` em `sleep_data`, políticas RLS por dono, trigger de criação de perfil |

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

O teste que realmente importa (usuário A não lê linha do usuário B) só é
possível com dois usuários reais e vem no **AUTH-03**, junto do repasse de JWT.
