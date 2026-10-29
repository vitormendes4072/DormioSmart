-- =====================================================================
-- 008_perfil_como_fonte_de_verdade.sql — PERFIL-01 (saída A), LGPD-04
--
-- Promove `public.profiles` de estrutura herdada a FONTE DE VERDADE do
-- perfil do usuário: é dela que o aplicativo passa a ler nome e idade, e é
-- nela que a tela de correção passa a escrever.
--
-- O raciocínio completo — inclusive a parte que não é código — está em
-- `docs/DECISAO-FONTE-DO-PERFIL.md`. O resumo necessário para ler este
-- arquivo:
--
--   * `profiles.nome`  -> fonte de verdade. Único lugar lido pelo aplicativo.
--   * `profiles.idade` -> finalidade declarada (aviso de aplicabilidade de
--                         coorte). Opcional, e permanece opcional.
--   * `auth.users.raw_user_meta_data.nome` -> INSUMO DE CRIAÇÃO, e nada mais:
--                         lido uma vez pelo gatilho `handle_new_user` (ou pelo
--                         reparo em `GET /api/me/perfil`) e nunca mais.
--
-- ---------------------------------------------------------------------
-- O QUE ESTA MIGRAÇÃO *NÃO* FAZ, E POR QUE
-- ---------------------------------------------------------------------
--
-- Não cria coluna, não cria policy e não mexe no gatilho do signup. Tudo de
-- que a rota nova precisa **já existia** desde a `001`: as colunas `nome` e
-- `idade`, e as policies `profiles_select_own`, `profiles_insert_own` e
-- `profiles_update_own`. A premissa do `UI-11` ("a policy de update já
-- existe") era verdadeira; o que não existia era alguém lendo a tabela.
--
-- O que falta, e é o que esta migração faz, são as três coisas que só passam
-- a importar quando a tabela deixa de ser inerte:
--
--   1. `updated_at` que se mantém.  Hoje a coluna existe com `default now()`
--      e NADA a atualiza — nenhuma escrita havia. A partir da rota nova ela
--      passaria a mentir: diria "criado e nunca mais tocado" sobre uma linha
--      corrigida hoje. Coluna de data que não acompanha a escrita é pior que
--      coluna ausente, porque parece informação.
--
--   2. Teto de tamanho do nome NO BANCO.  O limite de 120 em
--      `frontend/src/lib/perfil.ts` é decisão de interface, e a validação da
--      rota Flask também não é controle: `authenticated` tem GRANT de UPDATE
--      em `profiles`, e o navegador fala DIRETO com o PostgREST usando a
--      chave `anon` (pública por design). Ou seja, o titular pode gravar na
--      própria linha sem passar pelo Flask — exatamente o raciocínio da `007`
--      sobre a lista de campos de `dispositivos.py`. O dano é autoinfligido e
--      limitado à própria linha (o RLS nunca deixou escrever na alheia), mas
--      "ilimitado" não é um tamanho: um `nome` de megabytes passaria a ser
--      carregado em toda abertura de tela.
--
--   3. Comentários que declaram o papel de cada coluna.  O `DIAG-04` é
--      material de banca e sai do esquema; `comment on` é onde a finalidade
--      declarada de `idade` fica junto do dado, e não só num documento que
--      pode descolar.
--
-- ---------------------------------------------------------------------
-- SOBRE OS DOIS NÚMEROS QUE APARECEM AQUI (§3 das lições)
-- ---------------------------------------------------------------------
--
--   * `200` (teto de `nome` no banco) é **decisão**, não medição. Existe para
--     não ser ilimitado, e é propositalmente MAIOR que o 120 da interface:
--     se fosse igual, qualquer afrouxamento futuro do campo na tela passaria
--     a ser rejeitado pelo banco com erro de constraint, que é a pior forma
--     de descobrir uma divergência. A assimetria é deliberada e está dita.
--   * `150` (teto de `idade`) vem da `001` e NÃO é alterado aqui. Também é
--     decisão, não derivação de nada.
--
-- Contrato de dados: nenhuma mudança. Nada em `docs/DATA-CONTRACT.md` fala de
-- perfil — ele cobre a ingestão.
--
-- Aplicar em: Supabase > SQL Editor. Idempotente.
-- =====================================================================

begin;

-- ---------------------------------------------------------------------
-- 1. `updated_at` que acompanha a escrita
--
--    `security definer` NÃO é necessário aqui e por isso não é usado: o
--    gatilho roda no contexto de quem escreve, e quem escreve é o dono da
--    linha (o RLS já garantiu isso antes de o gatilho disparar). Privilégio
--    que não é preciso não se concede — SEC-06.
-- ---------------------------------------------------------------------
create or replace function public.tocar_updated_at()
returns trigger
language plpgsql
set search_path = ''
as $$
begin
    new.updated_at := now();
    return new;
end;
$$;

comment on function public.tocar_updated_at() is
    'Mantem updated_at na escrita. Sem SECURITY DEFINER de proposito: roda '
    'como o dono da linha, que o RLS ja autorizou. Sem EXECUTE para PUBLIC: '
    'gatilho nao precisa de GRANT para disparar.';

-- NÃO É CERIMÔNIA, E A SUÍTE PROVOU ISSO.
--
-- No PostgreSQL, `create function` concede EXECUTE a `PUBLIC` por padrão. Sem
-- as duas linhas abaixo, criar esta função AMPLIA o que o papel
-- `dormio_ingestao` pode executar — o papel que a `005` existe para manter com
-- EXECUTE em exatamente três funções e nenhum privilégio de tabela.
--
-- Isto não foi previsto: foi o
-- `tests/rls/test_rls_ingestao.py::test_o_papel_executa_exatamente_tres_funcoes`
-- que reprovou na primeira execução desta migração, nomeando a função nova na
-- mensagem. É o teste cujo docstring diz *"enumera o que ele PODE, para que
-- ampliar apareça no diff"* — e foi exatamente assim que apareceu.
--
-- Nenhum papel precisa de EXECUTE aqui: o Postgres confere privilégio de
-- função de gatilho na CRIAÇÃO do gatilho (feita aqui, pelo dono), não a cada
-- disparo. Por isso o `revoke` não quebra o gatilho — e há teste afirmando as
-- duas metades disso.
revoke all on function public.tocar_updated_at() from public;

drop trigger if exists profiles_tocar_updated_at on public.profiles;
create trigger profiles_tocar_updated_at
    before update on public.profiles
    for each row execute function public.tocar_updated_at();

-- ---------------------------------------------------------------------
-- 2. Teto de tamanho do nome
--
--    `not valid` NÃO é usado: a tabela tem uma linha por usuário e os nomes
--    existentes vêm do campo de cadastro, então validar agora é instantâneo e
--    é o que se quer — uma constraint `not valid` deixaria passar o que já
--    está lá, e "o que já está lá" é justamente o que ninguém conferiu.
--
--    `char_length`, não `length`: em texto Unicode `length` conta
--    caracteres do mesmo jeito em Postgres, mas `char_length` é o nome
--    explícito e não se confunde com `octet_length`, que contaria bytes e
--    rejeitaria nomes acentuados mais curtos do que parecem.
-- ---------------------------------------------------------------------
alter table public.profiles
    drop constraint if exists profiles_nome_tamanho;

alter table public.profiles
    add constraint profiles_nome_tamanho
    check (nome is null or char_length(nome) <= 200);

-- ---------------------------------------------------------------------
-- 3. O papel de cada coluna, declarado junto do dado
-- ---------------------------------------------------------------------
comment on table public.profiles is
    'Perfil do usuario. 1:1 com auth.users. FONTE DE VERDADE do nome e da '
    'idade desde o PERFIL-01 (2026-10-17): e daqui que o aplicativo le, e aqui '
    'que a tela de correcao escreve (art. 18, III). A linha e criada no signup '
    'pelo gatilho handle_new_user, e reparada por GET /api/me/perfil se faltar. '
    'Ver docs/DECISAO-FONTE-DO-PERFIL.md.';

comment on column public.profiles.nome is
    'Nome exibido. FONTE DE VERDADE: nenhuma tela le '
    'auth.users.raw_user_meta_data.nome, que e apenas o insumo de criacao. '
    'Teto de 200 e decisao de banco; a interface limita a 120.';

comment on column public.profiles.idade is
    'Idade autodeclarada, OPCIONAL. Finalidade declarada: dizer ao titular se '
    'a idade dele esta dentro ou fora da faixa das coortes de validacao '
    'citadas no trabalho (ver frontend/src/lib/aplicabilidade.ts e a secao 3 '
    'da politica de privacidade). NAO entra em calculo nenhum: nao pondera '
    'metrica, nao estratifica serie, nao alimenta modelo. Usar para calculo e '
    'FINALIDADE NOVA e exige declaracao nova antes (item LGPD-06).';

comment on column public.profiles.updated_at is
    'Mantida pelo gatilho profiles_tocar_updated_at (migracao 008). Antes da '
    '008 esta coluna ficava congelada na criacao, porque nada escrevia na '
    'tabela.';

-- ---------------------------------------------------------------------
-- 4. O gatilho do signup: mesmo corpo, papel declarado
--
--    O CORPO NÃO MUDA. O que muda é o que se afirma sobre ele: ele era "a
--    cópia que ninguém lia" e passa a ser "a semeadura da fonte de verdade".
--    Recriado com `comment on` em vez de só comentário de SQL para que a
--    declaração viaje com o banco, e não só com o repositório.
-- ---------------------------------------------------------------------
comment on function public.handle_new_user() is
    'Semeia public.profiles no signup, a partir de '
    'raw_user_meta_data->>nome. E a UNICA leitura legitima desse metadado '
    '(a outra e o reparo em GET /api/me/perfil, quando a linha falta). '
    'Depois da semeadura o metadado nao e lido por nada, e a primeira '
    'correcao de nome o limpa. Ver docs/DECISAO-FONTE-DO-PERFIL.md secao 3.';

commit;

-- =====================================================================
-- VERIFICAÇÃO (rodar após aplicar; o esperado está ao lado de cada uma)
--
--   -- 1. o gatilho de updated_at existe e está habilitado ('O' = origin)
--   select tgname, tgenabled from pg_trigger
--    where tgrelid = 'public.profiles'::regclass and not tgisinternal;
--   -- esperado: profiles_tocar_updated_at | O
--
--   -- 2. a constraint de tamanho existe
--   select conname, pg_get_constraintdef(oid) from pg_constraint
--    where conrelid = 'public.profiles'::regclass and conname like '%nome%';
--   -- esperado: profiles_nome_tamanho | CHECK ((nome IS NULL OR ...200))
--
--   -- 3. updated_at REALMENTE se move (o teste do gatilho, não da existência
--   --    dele — ver §4 das lições: "este teste já falhou alguma vez?")
--   --    Rode como o dono da tabela, numa linha sua, e desfaça:
--   begin;
--     select id, updated_at as antes from public.profiles limit 1;
--     update public.profiles set nome = nome
--      where id = (select id from public.profiles limit 1);
--     select id, updated_at as depois from public.profiles limit 1;
--   rollback;
--   -- esperado: `depois` > `antes`, mesmo sem mudar valor nenhum
--
--   -- 4. as policies continuam as mesmas (esta migração não mexe nelas)
--   select policyname, cmd from pg_policies
--    where schemaname = 'public' and tablename = 'profiles'
--    order by policyname;
--   -- esperado: 4 linhas — select/insert/update/delete own
-- =====================================================================
