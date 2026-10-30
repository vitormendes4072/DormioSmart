"""O vetor de características chega ao banco (DATA-07b (d), migração 010).

O que só um Postgres de verdade responde, e um mock não:

  1. As duas funções de gravação EXTRAEM os campos novos. Antes da 010 elas
     ignoravam qualquer chave que não conheciam — um `f` válido entrava com 201
     e sumia. É o modo de falha que esta migração existe para fechar, e é por
     isso que o teste confere a coluna, não o retorno.
  2. A gravação antiga (sem `f`) continua funcionando: é o backend que está em
     produção hoje, e a 010 entra no banco ANTES do release.
  3. "Tudo ou nada": um vetor pela metade é recusado pelo próprio banco.
  4. As colunas novas herdam o RLS da tabela: a Ana não lê o vetor do Bruno.

Os payloads são montados por `validacao.colunas_de_features`, a mesma função que
a rota usa — se o nome de uma coluna divergir entre o Python e a migração, é
aqui que aparece.
"""
import json

from validacao import COLUNAS_DE_FEATURES, colunas_de_features

PAPEL = "dormio_ingestao"
HASH_ANA = "hash-ana-1"

_F = [0.000123, 0.0021, 0.0876, 0.0244, 0.4171, 0.0125]
_G = [0.6, 0.0, 0.8]


def _payload(movimento, com_features=True):
    """O dicionário que `_gravar_leitura` entrega à função do banco."""
    leitura = {"movimento_total": movimento, "status": "Repouso",
               "epoca_segundos": 30, "metodo_agregacao": "pico-da-magnitude"}
    origem = {"f": _F, "g": _G, "fs": 32} if com_features else {}
    leitura.update(colunas_de_features(origem))
    return json.dumps(leitura)


def _colunas(sessao, leitura_id):
    sessao.cursor.execute("set local role postgres")
    sessao.cursor.execute(
        f"select {', '.join(COLUNAS_DE_FEATURES)} from public.sleep_data where id = %s",
        (leitura_id,),
    )
    return dict(zip(COLUNAS_DE_FEATURES, sessao.cursor.fetchone()))


def test_caminho_do_token_grava_o_vetor_com_nome(como, cenario):
    with como(cenario["ana"], papel=PAPEL) as ingestao:
        novo = ingestao.executar("select public.registrar_leitura(%s, %s::jsonb)",
                                 (HASH_ANA, _payload(7.1)))[0][0]
        assert novo is not None
        colunas = _colunas(ingestao, novo)
    assert colunas["enmo_media"] == _F[0] and colunas["p_frac"] == _F[5]
    assert (colunas["g_x"], colunas["g_y"], colunas["g_z"]) == tuple(_G)
    assert colunas["fs_features"] == 32.0


def test_caminho_da_sessao_grava_o_vetor(como, cenario):
    with como(cenario["ana"]) as ana:
        novo = ana.executar("select public.registrar_leitura_da_sessao(%s, %s::jsonb)",
                            (cenario["device_ana"], _payload(7.2)))[0][0]
        assert novo is not None
        colunas = _colunas(ana, novo)
    assert colunas["mag_din_media"] == _F[3] and colunas["zcr"] == _F[4]


def test_gravacao_sem_vetor_continua_funcionando(como, cenario):
    """O backend de hoje, em produção, não manda nenhuma das dez chaves."""
    with como(cenario["ana"], papel=PAPEL) as ingestao:
        novo = ingestao.executar(
            "select public.registrar_leitura(%s, %s::jsonb)",
            (HASH_ANA, '{"movimento_total": 7.3, "status": "Repouso"}'),
        )[0][0]
        assert novo is not None
        colunas = _colunas(ingestao, novo)
    assert all(v is None for v in colunas.values())


def test_vetor_pela_metade_e_recusado_pelo_banco(como, cenario):
    meio = json.dumps({"movimento_total": 7.4, "enmo_media": 0.001, "g_x": 0.6})
    with como(cenario["ana"], papel=PAPEL) as ingestao:
        erro = ingestao.negado("select public.registrar_leitura(%s, %s::jsonb)",
                               (HASH_ANA, meio))
    assert "sleep_data_features_tudo_ou_nada" in str(erro)


def test_ana_nao_le_o_vetor_do_bruno(como, cenario):
    with como(cenario["bruno"]) as bruno:
        novo = bruno.executar("select public.registrar_leitura_da_sessao(%s, %s::jsonb)",
                              (cenario["device_bruno"], _payload(7.5)))[0][0]
        assert novo is not None
        bruno.executar("select 1")
        bruno._conexao.commit()
    try:
        with como(cenario["ana"]) as ana:
            vistas = ana.executar("select enmo_media from public.sleep_data where id = %s",
                                  (novo,))
        assert vistas == [], "o RLS por dono nao cobre as colunas novas"
    finally:
        with como(cenario["bruno"]) as bruno:
            bruno.cursor.execute("set local role postgres")
            bruno.executar("delete from public.sleep_data where id = %s", (novo,))
            bruno._conexao.commit()


def test_as_duas_funcoes_extraem_os_campos_novos(catalogo):
    """Estrutural: é o que o diagnóstico de produção também confere — coluna
    criada com função antiga é exatamente o descarte silencioso."""
    linhas = catalogo(
        """
        select p.proname, pg_get_functiondef(p.oid) like '%%->> ''fs_features''%%'
          from pg_proc p join pg_namespace n on n.oid = p.pronamespace
         where n.nspname = 'public'
           and p.proname in ('registrar_leitura', 'registrar_leitura_da_sessao')
         order by 1
        """
    )
    assert linhas == [("registrar_leitura", True), ("registrar_leitura_da_sessao", True)]


def test_anon_continua_sem_executar_a_gravacao(catalogo):
    """`create or replace` preserva o ACL da 009; se um dia a 010 virasse
    `drop` + `create`, a função voltaria a nascer com o padrão."""
    linhas = catalogo(
        """
        select has_function_privilege('anon', 'public.registrar_leitura(text,jsonb)', 'execute'),
               has_function_privilege('anon', 'public.registrar_leitura_da_sessao(uuid,jsonb)',
                                      'execute')
        """
    )
    assert linhas == [(False, False)]
