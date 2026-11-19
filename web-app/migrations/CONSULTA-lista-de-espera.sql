-- =====================================================================
-- CONSULTA: a lista de espera do lançamento (UI-14, migração 022)
-- =====================================================================
-- Para o controlador, no SQL Editor do Supabase. A lista NÃO é lida por
-- nenhuma rota do serviço: este arquivo e o Table Editor do painel
-- (Table Editor → lista_de_espera → Export → CSV) são os dois caminhos.
--
-- Finalidade única (política, seção 2.6): o aviso do lançamento e o convite
-- para os primeiros testes. Exportar a lista é tratar dado pessoal: a cópia
-- exportada segue a mesma finalidade e o mesmo prazo, e não deve ser guardada
-- depois do envio.
-- =====================================================================

-- 1. Quantas inscrições há, e de quando a quando (só leitura).
select count(*)                          as inscricoes,
       min(inscrito_em)                  as primeira,
       max(inscrito_em)                  as ultima,
       count(*) filter (where nome is not null) as com_nome
  from public.lista_de_espera;

-- 2. A lista, para o aviso (só leitura). Mais antigas primeiro: quem chegou
--    antes é convidado antes para os primeiros testes.
select email, nome, inscrito_em
  from public.lista_de_espera
 order by inscrito_em;

-- 3. Quantas inscrições por dia (só leitura): para ver o efeito de cada post.
select date_trunc('day', inscrito_em at time zone 'America/Sao_Paulo')::date as dia,
       count(*) as inscricoes
  from public.lista_de_espera
 group by 1
 order by 1;

-- 4. SAIR DA LISTA, a pedido da pessoa (política, seção 2.6). APAGA.
--    Trocar o endereço, rodar SÓ este bloco, e conferir que voltou 1 linha.
-- delete from public.lista_de_espera
--  where email = lower(btrim('endereco@exemplo.com'))
-- returning email, inscrito_em;
