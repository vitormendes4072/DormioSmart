#!/usr/bin/env python3
"""Verificação por mutação da suíte de RLS (SEC-05).

── POR QUE ISTO EXISTE ──────────────────────────────────────────────────

Uma suíte de segurança que nunca falhou não provou nada. É perfeitamente
possível escrever 90 testes de RLS que passam num banco sem RLS — basta um
GRANT faltando, uma fixture vazia, uma claim mal montada. O resultado é o pior
possível: o relatório verde que se queria ver, sem a garantia que ele afirma.

Este script sabota o esquema de propósito, de um jeito por vez, e confere que a
suíte ACUSA cada sabotagem. Um sabotador que passe despercebido é uma regressão
da suíte — e vem antes de qualquer outro trabalho.

Rodar depois de TODA mudança de esquema (migração nova, policy nova, GRANT
novo). O custo é de segundos.

── USO ──────────────────────────────────────────────────────────────────

    export DORMIO_RLS_DATABASE_URL="postgresql://postgres@127.0.0.1:5433/postgres"
    python tests/rls/verificar_por_mutacao.py

    # um só, para investigar
    python tests/rls/verificar_por_mutacao.py --apenas rls_desligado

A sabotagem é aplicada acrescentando SQL ao fim de `pos_migracao.sql`
numa CÓPIA da árvore, em /tmp. O repositório não é tocado.
"""
import argparse
import pathlib
import shutil
import subprocess
import sys
import tempfile

AQUI = pathlib.Path(__file__).resolve().parent
WEB_APP = AQUI.parent.parent
ARQUIVO_ALVO = pathlib.Path("tests/rls/pos_migracao.sql")

# ---------------------------------------------------------------------
# Os sabotadores.
#
# `minimo` é quantos testes devem cair, no mínimo. Não é o número exato de
# propósito: acrescentar teste novo aumentaria a contagem e faria este script
# falhar por motivo errado. O que importa é que NÃO seja zero — e, onde a
# sabotagem é específica, que o teste NOMEADO em `exige` esteja entre os que
# caem, para que a suíte não acuse por acidente.
# ---------------------------------------------------------------------
SABOTADORES = {
    # --- SEC-05: o RLS por dono ---
    "rls_desligado": dict(
        descricao="RLS desligado em sleep_data",
        sql="alter table public.sleep_data disable row level security;",
        minimo=10,
        exige="test_anon_nao_le_nada",
    ),
    "policy_permissiva": dict(
        descricao="policy using(true) em sleep_data",
        sql="create policy sd_tudo on public.sleep_data for select to authenticated using (true);",
        minimo=5,
        exige="test_nenhuma_policy_tem_qualificador_permissivo",
    ),
    "update_sem_with_check": dict(
        descricao="devices_update_own sem with check",
        sql="""
            drop policy devices_update_own on public.devices;
            create policy devices_update_own on public.devices for update
                to authenticated using (user_id = (select auth.uid()));
        """,
        minimo=1,
        exige="test_policies_de_update_tem_with_check",
    ),
    "policy_para_anon": dict(
        descricao="policy de select para anon em profiles",
        sql="create policy prof_anon on public.profiles for select to anon using (true);",
        minimo=3,
        exige="test_anon_nao_le_nada",
    ),
    "insert_liberado": dict(
        descricao="insert liberado em sleep_data para authenticated",
        sql="""
            create policy sd_insert on public.sleep_data for insert
                to authenticated with check (user_id = (select auth.uid()));
        """,
        minimo=2,
        exige="test_ana_nao_fabrica_leitura_nem_no_proprio_nome",
    ),
    # --- PERFIL-01: o caminho de escrita que a rota de perfil usa ---
    #
    # `profiles` deixou de ser tabela inerte: `PATCH /api/me/perfil` escreve
    # nela por `upsert`, isto é, `insert ... on conflict do update`. Esse
    # comando passa por DUAS policies, e os dois sabotadores abaixo afrouxam
    # uma de cada vez — porque supor que basta uma barreira é precisamente o
    # erro que eles existem para pegar.
    # Este sabotador ACHOU DOIS DEFEITOS no primeiro uso, e os dois estão
    # registrados onde aconteceram:
    #
    #   1. `test_ana_nao_cria_profile_para_o_bruno` barrava pela chave
    #      estrangeira, não pela policy — corrigido, e virou
    #      `test_ana_nao_cria_profile_para_quem_ainda_nao_tem` (§4 das lições).
    #   2. O `exige` que este sabotador tinha ao nascer apontava para
    #      `test_ana_nao_faz_upsert_no_perfil_do_bruno`, que **não pode**
    #      detectá-lo: ali a linha da vítima existe, então o comando cai no
    #      ramo de UPDATE e a policy de update barra — a de insert escancarada
    #      passa despercebida. Dois barramentos em série fazem cada um
    #      invisível a partir do outro, e é por isso que o teste que o `exige`
    #      nomeia é o da vítima SEM perfil, onde não há segundo barramento.
    "perfil_insert_permissivo": dict(
        descricao="profiles_insert_own com with check (true)",
        sql="""
            drop policy profiles_insert_own on public.profiles;
            create policy profiles_insert_own on public.profiles for insert
                to authenticated with check (true);
        """,
        minimo=1,
        exige="test_ana_nao_cria_profile_para_quem_ainda_nao_tem",
    ),
    # E este mostrou outra coisa que a documentação diz e ninguém havia
    # conferido no artefato (§5): no PostgreSQL, policy de UPDATE **sem**
    # `with check` usa o `using` também como verificação da linha resultante.
    # Removê-lo, portanto, NÃO abre a transferência de linha para outro dono —
    # o comportamento não muda, e nenhum teste de acesso pode cair. O que
    # detecta é o teste estrutural, e é ele que o `exige` nomeia.
    "perfil_update_sem_with_check": dict(
        descricao="profiles_update_own sem with check",
        sql="""
            drop policy profiles_update_own on public.profiles;
            create policy profiles_update_own on public.profiles for update
                to authenticated using (id = (select auth.uid()));
        """,
        minimo=1,
        exige="test_policies_de_update_tem_with_check",
    ),
    "perfil_sem_teto_de_nome": dict(
        descricao="constraint de tamanho do nome removida (migracao 008)",
        sql="alter table public.profiles drop constraint profiles_nome_tamanho;",
        minimo=1,
        exige="test_nome_gigante_e_recusado_pelo_banco",
    ),
    "perfil_sem_updated_at": dict(
        descricao="gatilho de updated_at removido (migracao 008)",
        sql="drop trigger profiles_tocar_updated_at on public.profiles;",
        minimo=2,
        exige="test_updated_at_se_move_na_escrita",
    ),
    "gatilho_de_updated_at_executavel": dict(
        descricao="EXECUTE em tocar_updated_at devolvido a PUBLIC",
        sql="grant execute on function public.tocar_updated_at() to public;",
        minimo=1,
        exige="test_o_gatilho_de_updated_at_nao_e_executavel_por_ninguem",
    ),
    "tabela_nova_sem_rls": dict(
        descricao="tabela nova com user_id e sem RLS",
        sql="""
            create table public.sessoes_de_captacao (
                id bigserial primary key,
                user_id uuid references auth.users(id),
                inicio timestamptz
            );
            grant select, insert, update, delete
                on public.sessoes_de_captacao to anon, authenticated;
        """,
        minimo=1,
        exige="test_toda_tabela_de_dado_pessoal_tem_rls",
    ),
    "definer_sem_search_path": dict(
        descricao="handle_new_user sem search_path fixo",
        sql="""
            create or replace function public.handle_new_user()
            returns trigger language plpgsql security definer as $SAB$
            begin
                insert into public.profiles (id, nome)
                values (new.id, new.raw_user_meta_data ->> 'nome')
                on conflict (id) do nothing;
                return new;
            end; $SAB$;
        """,
        minimo=1,
        exige="test_trigger_de_criacao_de_perfil_esta_blindado",
    ),
    "grants_retirados": dict(
        descricao='GRANTs retirados de authenticated (simula "tudo quebrado")',
        sql="""
            revoke all on public.profiles, public.devices, public.sleep_data
                from authenticated;
        """,
        minimo=15,
        # O caminho feliz é o que tem de cair aqui. Se a suíte passasse com o
        # banco inacessível, ela não valeria nada — é o sabotador mais
        # importante da lista.
        exige="test_ana_le_apenas_o_proprio_profile",
    ),
    # --- SEC-06: o privilégio da ingestão ---
    "ingestao_com_select": dict(
        descricao="papel de ingestao ganha select em sleep_data",
        sql="grant select on public.sleep_data to dormio_ingestao;",
        minimo=2,
        exige="test_o_papel_nao_tem_privilegio_de_tabela",
    ),
    "ingestao_com_bypassrls": dict(
        descricao="papel de ingestao ganha BYPASSRLS",
        sql="alter role dormio_ingestao bypassrls;",
        minimo=1,
        exige="test_o_papel_existe_e_nao_ignora_o_rls",
    ),
    "ingestao_alcanca_a_sessao": dict(
        descricao="papel de ingestao ganha a funcao do caminho por sessao",
        sql="""
            grant execute on function public.registrar_leitura_da_sessao(uuid, jsonb)
                to dormio_ingestao;
        """,
        minimo=1,
        exige="test_o_papel_nao_grava_pelo_caminho_da_sessao",
    ),
    "anon_alcanca_a_ingestao": dict(
        descricao="anon ganha execute em registrar_leitura",
        sql="grant execute on function public.registrar_leitura(text, jsonb) to anon;",
        minimo=1,
        exige="test_anon_nao_executa_funcao_de_ingestao",
    ),
    "gravacao_aceita_o_dono_do_json": dict(
        descricao="registrar_leitura passa a aceitar user_id do JSON",
        sql="""
            create or replace function public.registrar_leitura(
                p_token_hash text, p_leitura jsonb
            ) returns uuid language plpgsql volatile security definer
            set search_path = '' as $SAB$
            declare v_device uuid; v_dono uuid; v_id uuid;
            begin
                select d.id, d.user_id into v_device, v_dono
                  from public.device_tokens t
                  join public.devices d on d.id = t.device_id
                 where t.token_hash = p_token_hash and d.revoked_at is null limit 1;
                if v_device is null then return null; end if;
                insert into public.sleep_data (movimento_total, user_id, device_id)
                values (
                    (p_leitura ->> 'movimento_total')::double precision,
                    -- A sabotagem: o JSON escolhe o dono.
                    coalesce((p_leitura ->> 'user_id')::uuid, v_dono),
                    v_device
                ) returning id into v_id;
                return v_id;
            end; $SAB$;
        """,
        minimo=1,
        exige="test_a_ingestao_nao_escolhe_o_dono_pelo_json",
    ),
    # --- SEC-07: o direito de eliminação, e o que ele não pode abrir ---
    "delete_permissivo_em_sleep_data": dict(
        descricao="sleep_data_delete_own com using(true)",
        sql="""
            drop policy sleep_data_delete_own on public.sleep_data;
            create policy sleep_data_delete_own on public.sleep_data
                for delete to authenticated using (true);
        """,
        minimo=2,
        exige="test_o_delete_em_massa_da_ana_nao_alcanca_o_bruno",
    ),
    "exclusao_de_conta_com_parametro": dict(
        descricao="apagar_minha_conta ganha parametro de usuario",
        sql="""
            drop function if exists public.apagar_minha_conta();
            create or replace function public.apagar_minha_conta(p_user_id uuid default null)
            returns jsonb language plpgsql volatile security definer
            set search_path = '' as $SAB$
            declare v_dono uuid := coalesce(p_user_id, auth.uid());
            begin
                if v_dono is null then return null; end if;
                delete from public.sleep_data where user_id = v_dono;
                delete from public.devices where user_id = v_dono;
                delete from public.profiles where id = v_dono;
                return jsonb_build_object('conta_de_acesso_removida', false);
            end; $SAB$;
            grant execute on function public.apagar_minha_conta(uuid) to authenticated;
        """,
        minimo=1,
        exige="test_a_funcao_nao_tem_parametro_de_usuario",
    ),
    "anon_alcanca_a_exclusao": dict(
        descricao="anon ganha execute em apagar_minha_conta",
        sql="grant execute on function public.apagar_minha_conta() to anon;",
        minimo=1,
        exige="test_anon_nao_alcanca_a_funcao",
    ),
    # SEC-12 (28/10). Os dois abaixo cobrem o que nenhum sabotador alcançava:
    # o PADRÃO de privilégio, que decide como nasce o objeto da próxima
    # migração. O primeiro desfaz a parte 4 da 009; o segundo desfaz a
    # reprodução do Supabase na base de teste — que é como, até 28/10, os
    # testes de `anon` passavam no vazio.
    "padrao_de_funcao_volta_a_anon": dict(
        descricao="funcao nova volta a nascer executavel por anon",
        sql="alter default privileges in schema public grant execute on functions to anon;",
        minimo=1,
        exige="test_funcao_nova_nao_nasce_executavel_por_anon",
    ),
    "base_sem_padrao_de_tabela_do_supabase": dict(
        descricao="a base de teste deixa de dar a anon o privilegio padrao em tabela nova",
        sql="alter default privileges in schema public revoke all on tables from anon;",
        minimo=1,
        exige="test_a_base_reproduz_os_padroes_do_supabase_para_tabela",
    ),
    "update_liberado_em_sleep_data": dict(
        descricao="sleep_data ganha policy de update (reescrever medicao)",
        sql="""
            create policy sd_update on public.sleep_data for update to authenticated
                using (user_id = (select auth.uid()))
                with check (user_id = (select auth.uid()));
        """,
        minimo=2,
        exige="test_o_direito_de_apagar_nao_virou_direito_de_reescrever",
    ),
    # --- SEC-08: a credencial fora da tabela exposta ---
    "credencial_de_volta_em_devices": dict(
        descricao="token_hash recriada como coluna de devices",
        sql="alter table public.devices add column token_hash text;",
        minimo=1,
        exige="test_devices_nao_tem_mais_token_hash",
    ),
    "cliente_alcanca_as_credenciais": dict(
        descricao="authenticated ganha select em device_tokens",
        sql="grant select on public.device_tokens to authenticated;",
        minimo=1,
        exige="test_nem_anon_nem_authenticated_tem_privilegio_na_tabela",
    ),
    "credenciais_sem_rls": dict(
        descricao="device_tokens perde o RLS (a segunda camada)",
        sql="alter table public.device_tokens disable row level security;",
        minimo=1,
        exige="test_a_tabela_tem_rls_ligado_mesmo_sem_grant",
    ),
    "pareamento_escolhe_o_dono": dict(
        descricao="parear_dispositivo ganha parametro de usuario",
        sql="""
            create or replace function public.parear_dispositivo(
                p_nome text, p_tipo text, p_token_hash text, p_user_id uuid default null
            ) returns table (
                id uuid, nome text, tipo text,
                created_at timestamptz, last_seen_at timestamptz, revoked_at timestamptz
            ) language plpgsql volatile security definer set search_path = '' as $SAB$
            declare v_dono uuid := coalesce(p_user_id, auth.uid()); v_device uuid;
            begin
                if v_dono is null then return; end if;
                insert into public.devices (user_id, nome, tipo)
                values (v_dono, p_nome, coalesce(p_tipo, 'travesseiro'))
                returning devices.id into v_device;
                insert into public.device_tokens (device_id, token_hash)
                values (v_device, p_token_hash);
                return query select d.id, d.nome, d.tipo, d.created_at,
                                    d.last_seen_at, d.revoked_at
                               from public.devices d where d.id = v_device;
            end; $SAB$;
            grant execute on function
                public.parear_dispositivo(text, text, text, uuid) to authenticated;
        """,
        minimo=1,
        exige="test_o_pareamento_nao_aceita_escolher_o_dono",
    ),
    "insert_direto_em_devices_de_volta": dict(
        descricao="devices_insert_own recriada (dispositivo sem credencial)",
        sql="""
            create policy devices_insert_own on public.devices for insert
                to authenticated with check (user_id = (select auth.uid()));
        """,
        minimo=1,
        exige="test_nao_da_para_criar_dispositivo_sem_credencial",
    ),
    "revogacao_ignorada_na_juncao": dict(
        descricao="resolver_dispositivo esquece o revoked_at na juncao",
        sql="""
            create or replace function public.resolver_dispositivo(p_token_hash text)
            returns table (id uuid, user_id uuid) language sql stable security definer
            set search_path = '' as $SAB$
                select d.id, d.user_id
                  from public.device_tokens t
                  join public.devices d on d.id = t.device_id
                 where t.token_hash = p_token_hash
                 limit 1
            $SAB$;
        """,
        minimo=1,
        exige="test_revogar_o_dispositivo_invalida_o_token",
    ),
    "credencial_sem_cascade": dict(
        descricao="device_tokens sem cascade (credencial orfa apos exclusao)",
        sql="""
            alter table public.device_tokens
                drop constraint device_tokens_device_id_fkey;
            alter table public.device_tokens
                add constraint device_tokens_device_id_fkey
                foreign key (device_id) references public.devices(id);
        """,
        minimo=1,
        exige="test_apagar_o_dispositivo_apaga_a_credencial",
    ),
    "definer_da_005_sem_search_path": dict(
        descricao="resolver_dispositivo sem search_path fixo",
        sql="""
            create or replace function public.resolver_dispositivo(p_token_hash text)
            returns table (id uuid, user_id uuid) language sql stable security definer
            as $SAB$
                select d.id, d.user_id
                  from public.device_tokens t
                  join public.devices d on d.id = t.device_id
                 where t.token_hash = p_token_hash and d.revoked_at is null
                 limit 1
            $SAB$;
        """,
        minimo=1,
        exige="test_toda_funcao_definer_tem_search_path_fixo",
    ),

    # --- LGPD-02 (05/11): retenção por inatividade, migração 013 ---
    "expurgo_ignora_a_sessao": dict(
        descricao="o expurgo ignora a refreshed_at, que e o que a renovacao grava (LGPD-09)",
        sql="""
            do $SAB$ begin
                execute replace(pg_get_functiondef('public.expurgar_contas_inativas()'::regprocedure),
                                'to_timestamp(extract(epoch from se.refreshed_at))', 'null::timestamptz');
            end $SAB$;
        """,
        minimo=1,
        exige="test_um_sinal_dentro_de_12_meses_mantem_a_conta",
    ),
    "expurgo_ignora_leituras": dict(
        descricao="expurgo considera so criacao e login, nao a ultima leitura",
        sql="""
            create or replace function public.expurgar_contas_inativas()
            returns jsonb language plpgsql volatile security invoker set search_path = ''
            as $SAB$
            declare r record; n bigint := 0;
            begin
                for r in select u.id from auth.users u
                          where greatest(u.created_at, u.last_sign_in_at)
                                < now() - interval '12 months'
                loop
                    perform public._eliminar_titular(r.id);
                    n := n + 1;
                end loop;
                return jsonb_build_object('contas_expurgadas', n, 'leituras_apagadas', 0,
                                          'dispositivos_apagados', 0, 'contas_de_acesso_removidas', 0);
            end;
            $SAB$;
        """,
        minimo=1,
        exige="test_um_sinal_dentro_de_12_meses_mantem_a_conta",
    ),
    "expurgo_executavel_por_usuario": dict(
        descricao="authenticated ganha execute no expurgo",
        sql="grant execute on function public.expurgar_contas_inativas() to authenticated;",
        minimo=1,
        exige="test_nenhum_papel_de_fora_executa_as_funcoes_novas",
    ),
    "eliminacao_esquece_dispositivos": dict(
        descricao="_eliminar_titular deixa os dispositivos do titular",
        sql="""
            create or replace function public._eliminar_titular(p_titular uuid)
            returns jsonb language plpgsql volatile security invoker set search_path = ''
            as $SAB$
            declare v_l bigint; v_p bigint;
            begin
                if p_titular is null then return null; end if;
                delete from public.sleep_data where user_id = p_titular;
                get diagnostics v_l = row_count;
                delete from public.profiles where id = p_titular;
                get diagnostics v_p = row_count;
                return jsonb_build_object('leituras_apagadas', v_l, 'dispositivos_apagados', 0,
                                          'perfil_apagado', v_p > 0, 'conta_de_acesso_removida', false);
            end;
            $SAB$;
        """,
        minimo=2,
        exige="test_ana_apaga_a_propria_conta_por_completo",
    ),
    "leituras_sem_cascata": dict(
        descricao="a chave de sleep_data.user_id volta a ser sem cascata, como na producao antes da 015",
        sql="""
            alter table public.sleep_data drop constraint sleep_data_user_id_fkey;
            alter table public.sleep_data add constraint sleep_data_user_id_fkey
                foreign key (user_id) references auth.users(id);
        """,
        minimo=3,
        exige="test_apagar_o_usuario_direto_leva_as_leituras",
    ),
    # --- SEC-18 (10/11): a validacao dentro do banco (migracao 016) ---------
    "faixa_das_features_some": dict(
        descricao="a restricao de faixa das features sai",
        sql="alter table public.sleep_data drop constraint sleep_data_faixa_features;",
        minimo=1,
        exige="test_um_passo_alem_da_borda_e_recusado",
    ),
    "faixa_mais_estreita_que_o_flask": dict(
        descricao="enmo_max no banco vai so ate 15 g (o Flask aceita 16): leitura valida falharia",
        sql="""
            alter table public.sleep_data drop constraint sleep_data_faixa_features;
            alter table public.sleep_data add constraint sleep_data_faixa_features check (
                enmo_max is null or enmo_max between 0 and 15);
        """,
        minimo=1,
        exige="test_a_borda_do_flask_passa_no_banco",
    ),
    "estado_livre_de_novo": dict(
        descricao="a restricao de estado sai",
        sql="alter table public.sleep_data drop constraint sleep_data_estado_valido;",
        minimo=1,
        exige="test_estado_e_metodo_so_os_do_flask",
    ),
    "futuro_aceito": dict(
        descricao="a gravacao por sessao tolera 100 anos no futuro em vez de 5 minutos",
        sql="""
            do $SAB$ begin
                execute replace(pg_get_functiondef('public.registrar_leitura_da_sessao(uuid,jsonb)'::regprocedure),
                                '5 minutes', '100 years');
            end $SAB$;
        """,
        minimo=1,
        exige="test_captura_no_futuro_e_recusada",
    ),
    "pareamento_sem_teto": dict(
        descricao="parear_dispositivo deixa de contar os dispositivos ativos",
        sql="""
            do $SAB$ begin
                execute replace(pg_get_functiondef('public.parear_dispositivo(text,text,text)'::regprocedure),
                                '>= 10 then', '>= 100000 then');
            end $SAB$;
        """,
        minimo=1,
        exige="test_o_teto_e_de_10_dispositivos_ativos",
    ),
    "pareamento_aceita_qualquer_hash": dict(
        descricao="parear_dispositivo deixa de conferir o formato do hash",
        sql="""
            do $SAB$ begin
                execute replace(pg_get_functiondef('public.parear_dispositivo(text,text,text)'::regprocedure),
                                '^[0-9a-f]{64}$', '.*');
            end $SAB$;
        """,
        minimo=1,
        exige="test_pareamento_recusa_hash_fora_do_formato",
    ),
    "revogacao_desfeita": dict(
        descricao="o gatilho que torna a revogacao definitiva sai",
        sql="drop trigger devices_revogacao_definitiva on public.devices;",
        minimo=1,
        exige="test_o_titular_nao_desfaz_a_revogacao",
    ),
    "nome_sem_teto": dict(
        descricao="a restricao de tamanho do nome do dispositivo sai",
        sql="alter table public.devices drop constraint devices_nome_tamanho;",
        minimo=1,
        exige="test_o_titular_nao_renomeia_para_mais_de_60",
    ),
    # --- LGPD-12 (10/11): o consentimento destacado (migracao 017) ----------
    "sessao_grava_sem_consentimento": dict(
        descricao="registrar_leitura_da_sessao deixa de exigir o consentimento",
        sql="""
            do $SAB$ begin
                execute replace(pg_get_functiondef('public.registrar_leitura_da_sessao(uuid,jsonb)'::regprocedure),
                                'if not exists (select 1 from public.profiles p', 'if false and not exists (select 1 from public.profiles p');
            end $SAB$;
        """,
        minimo=1,
        exige="test_sem_consentimento_a_gravacao_pela_sessao_e_recusada",
    ),
    "pareia_sem_consentimento": dict(
        descricao="parear_dispositivo deixa de exigir o consentimento",
        sql="""
            do $SAB$ begin
                execute replace(pg_get_functiondef('public.parear_dispositivo(text,text,text)'::regprocedure),
                                'if not exists (select 1 from public.profiles p', 'if false and not exists (select 1 from public.profiles p');
            end $SAB$;
        """,
        minimo=1,
        exige="test_sem_consentimento_o_pareamento_e_recusado",
    ),
    "qualquer_versao_serve": dict(
        descricao="a trava aceita qualquer versao registrada, inclusive a antiga",
        sql="""
            do $SAB$ begin
                execute replace(pg_get_functiondef('public.registrar_leitura_da_sessao(uuid,jsonb)'::regprocedure),
                                'and p.consentimento_saude_versao = public.versao_do_consentimento()',
                                'and p.consentimento_saude_versao is not null');
            end $SAB$;
        """,
        minimo=1,
        exige="test_versao_antiga_conta_como_sem_consentimento",
    ),
    "consentimento_escrito_direto": dict(
        descricao="o gatilho que obriga a passar pela funcao sai",
        sql="drop trigger profiles_consentimento_so_pela_funcao on public.profiles;",
        minimo=2,
        exige="test_o_titular_nao_escreve_o_consentimento_direto",
    ),
    "consente_qualquer_versao": dict(
        descricao="consentir_dado_de_saude deixa de conferir a versao",
        sql="""
            do $SAB$ begin
                execute replace(pg_get_functiondef('public.consentir_dado_de_saude(text)'::regprocedure),
                                'if p_versao is distinct from', 'if false and p_versao is distinct from');
            end $SAB$;
        """,
        minimo=1,
        exige="test_consentir_com_versao_errada_e_recusado",
    ),
    # --- CAL-03 (11/11): a calibracao da gravidade (migracao 018) ----------
    "calibracao_sem_regua": dict(
        descricao="a restricao de g_norma e calibrada sai",
        sql="alter table public.sleep_data drop constraint sleep_data_calibracao_valida;",
        minimo=1,
        exige="test_um_passo_alem_da_borda_e_recusado",
    ),
    "calibracao_mais_estreita_que_o_flask": dict(
        descricao="g_norma no banco so ate 7 g (o Flask aceita 8): leitura valida falharia",
        sql="""
            alter table public.sleep_data drop constraint sleep_data_calibracao_valida;
            alter table public.sleep_data add constraint sleep_data_calibracao_valida check (
                g_norma is null or g_norma between 0 and 7);
        """,
        minimo=1,
        exige="test_a_borda_do_flask_passa",
    ),
    "sessao_descarta_gn": dict(
        descricao="registrar_leitura_da_sessao grava nulo em g_norma",
        sql="""
            do $SAB$ begin
                execute replace(pg_get_functiondef('public.registrar_leitura_da_sessao(uuid,jsonb)'::regprocedure),
                                '(p_leitura ->> ''g_norma'')::double precision', 'null::double precision');
            end $SAB$;
        """,
        minimo=1,
        exige="test_a_sessao_grava_gn_e_a_marca",
    ),
    "token_descarta_a_marca": dict(
        descricao="registrar_leitura (token) grava nulo em calibrada",
        sql="""
            do $SAB$ begin
                execute replace(pg_get_functiondef('public.registrar_leitura(text,jsonb)'::regprocedure),
                                '(p_leitura ->> ''calibrada'')::boolean', 'null::boolean');
            end $SAB$;
        """,
        minimo=1,
        exige="test_o_token_grava_gn_e_a_marca",
    ),
}


def rodar(nome, sabotador, url):
    """Aplica um sabotador numa cópia da árvore e devolve (ok, resumo)."""
    with tempfile.TemporaryDirectory(prefix=f"mut-{nome}-") as temporario:
        arvore = pathlib.Path(temporario) / "web-app"
        shutil.copytree(
            WEB_APP,
            arvore,
            ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache", "*.pyc"),
        )

        alvo = arvore / ARQUIVO_ALVO
        with alvo.open("a", encoding="utf-8") as arquivo:
            arquivo.write(f"\n-- SABOTAGEM: {sabotador['descricao']}\n")
            arquivo.write(sabotador["sql"] + "\n")

        processo = subprocess.run(
            [sys.executable, "-m", "pytest", "tests/rls", "-q", "--no-header", "-p", "no:cacheprovider"],
            cwd=arvore,
            env={**__import__("os").environ, "DORMIO_RLS_DATABASE_URL": url,
                 "PYTHONIOENCODING": "utf-8"},
            capture_output=True,
            encoding="utf-8",
            errors="replace",
        )
        saida = processo.stdout + processo.stderr

        caidos = [
            linha.split("::")[-1].split()[0]
            for linha in saida.splitlines()
            if linha.startswith("FAILED")
        ]

        # SABOTADOR QUEBRADO vs. SABOTAGEM NAO DETECTADA — a distincao custou
        # um diagnostico errado. Quando o SQL do sabotador nao aplica (o caso
        # real: ele referenciava `devices.token_hash`, que a migration 007
        # removeu), o setup do esquema falha e o pytest emite ERROR, nao FAILED.
        # Contando so FAILED, o script dizia "a suite nao acusa" — e mandava
        # consertar a suite, quando o defeito era no proprio sabotador.
        erros_de_setup = [
            linha for linha in saida.splitlines()
            if linha.startswith("ERROR") or "error at setup of" in linha.lower()
        ]
        if erros_de_setup and not caidos:
            return False, (
                "SABOTADOR QUEBRADO: o SQL nao aplicou, o esquema nao subiu. "
                "Conserte o sabotador, nao a suite. Primeira linha: "
                + erros_de_setup[0][:160]
            )

        if not caidos:
            return False, "NENHUM teste caiu — a suite nao acusa esta sabotagem"
        if len(caidos) < sabotador["minimo"]:
            return False, (
                f"caíram {len(caidos)}, esperado >= {sabotador['minimo']}: "
                + ", ".join(caidos[:6])
            )
        exigido = sabotador.get("exige")
        if exigido and not any(exigido in c for c in caidos):
            return False, (
                f"{len(caidos)} testes caíram, mas `{exigido}` NAO estava entre "
                "eles — a suite pode estar acusando por acidente"
            )
        return True, f"{len(caidos)} testes caíram"


def principal():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    analisador = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    analisador.add_argument("--apenas", help="roda um sabotador só, pelo nome")
    argumentos = analisador.parse_args()

    import os

    url = os.environ.get("DORMIO_RLS_DATABASE_URL", "").strip()
    if not url:
        print(
            "ERRO: DORMIO_RLS_DATABASE_URL nao definida.\n"
            "      Ver web-app/tests/rls/README.md.",
            file=sys.stderr,
        )
        return 2

    escolhidos = SABOTADORES
    if argumentos.apenas:
        if argumentos.apenas not in SABOTADORES:
            print(
                f"ERRO: sabotador '{argumentos.apenas}' nao existe. Opcoes:\n  "
                + "\n  ".join(SABOTADORES),
                file=sys.stderr,
            )
            return 2
        escolhidos = {argumentos.apenas: SABOTADORES[argumentos.apenas]}

    # Confere primeiro que a suíte passa SEM sabotagem. Sem isso, um "todos os
    # sabotadores detectados" poderia significar apenas que tudo está quebrado.
    print("Referencia (sem sabotagem): ", end="", flush=True)
    # Filho e pai combinam UTF-8 (DOCS-WIN-01). Sem isto, no Windows, o filho
    # escrevia numa página de código e o pai decodificava noutra: a primeira
    # saída com acento derrubava o verificador com UnicodeDecodeError, e o
    # `stdout` virava None.
    processo = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/rls", "-q", "--no-header", "-p", "no:cacheprovider"],
        cwd=WEB_APP,
        env={**os.environ, "DORMIO_RLS_DATABASE_URL": url,
             "PYTHONIOENCODING": "utf-8"},
        capture_output=True,
        encoding="utf-8",
        errors="replace",
    )
    if processo.returncode != 0:
        print("FALHOU")
        print(
            "\nA suite nao passa nem sem sabotagem. Conserte isso primeiro — "
            "senao os sabotadores nao dizem nada.\n"
        )
        print(processo.stdout[-3000:])
        return 1
    print("passa\n")

    falhas = []
    for nome, sabotador in escolhidos.items():
        print(f"  {nome:34s} ", end="", flush=True)
        ok, resumo = rodar(nome, sabotador, url)
        print(("[detectado] " if ok else "[NAO DETECTADO] ") + resumo)
        if not ok:
            falhas.append((nome, sabotador["descricao"], resumo))

    print()
    if falhas:
        print(f"REGRESSAO: {len(falhas)} de {len(escolhidos)} sabotagens passaram "
              "sem ser detectadas:\n")
        for nome, descricao, resumo in falhas:
            print(f"  · {nome}: {descricao}\n    {resumo}")
        print(
            "\nIsto vem antes de qualquer outro trabalho: a suite esta "
            "afirmando uma garantia que nao verifica."
        )
        return 1

    print(f"OK: {len(escolhidos)} de {len(escolhidos)} sabotagens detectadas.")
    return 0


if __name__ == "__main__":
    raise SystemExit(principal())
