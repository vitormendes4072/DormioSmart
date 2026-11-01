"""A mesma época, reenviada, não vira duas linhas (DATA-08, migração 011).

O que só um Postgres de verdade responde, e um mock não:

  1. Reenviar a mesma leitura (mesmo dispositivo, `captured_at`, `epoca_segundos`)
     grava UMA linha, pelos dois caminhos e entre eles.
  2. O reenvio devolve o id da linha que já existe, e não nulo. Nulo faria o
     backend responder 503 ("não persistiu") e o firmware reenviar para sempre
     — o teste confere o id, não só a contagem.
  3. O que a 011 declara que NÃO deduplica continua gravando: outra época no
     mesmo instante, e leitura sem `captured_at`.
"""
import json

PAPEL = "dormio_ingestao"
HASH_ANA = "hash-ana-1"
INSTANTE = "2026-10-31T03:00:00+00:00"


def _payload(instante=INSTANTE, epoca=30, movimento=9.8):
    leitura = {"movimento_total": movimento, "status": "Repouso",
               "epoca_segundos": epoca, "metodo_agregacao": "pico-da-magnitude"}
    if instante is not None:
        leitura["captured_at"] = instante
    return json.dumps(leitura)


def _linhas(sessao, device_id, instante=INSTANTE):
    sessao.cursor.execute("set local role postgres")
    if instante is None:
        sessao.cursor.execute(
            "select count(*) from public.sleep_data where device_id = %s and captured_at is null",
            (device_id,))
    else:
        sessao.cursor.execute(
            "select count(*) from public.sleep_data where device_id = %s and captured_at = %s",
            (device_id, instante))
    return sessao.cursor.fetchone()[0]


def test_reenvio_pelo_token_grava_uma_linha_e_devolve_o_mesmo_id(como, cenario):
    with como(cenario["ana"], papel=PAPEL) as ingestao:
        primeiro = ingestao.executar("select public.registrar_leitura(%s, %s::jsonb)",
                                     (HASH_ANA, _payload()))[0][0]
        segundo = ingestao.executar("select public.registrar_leitura(%s, %s::jsonb)",
                                    (HASH_ANA, _payload()))[0][0]
        assert primeiro is not None
        assert segundo == primeiro, "o reenvio tem de devolver o id que ja existe, nao nulo"
        assert _linhas(ingestao, cenario["device_ana"]) == 1


def test_reenvio_pela_sessao_grava_uma_linha_e_devolve_o_mesmo_id(como, cenario):
    with como(cenario["ana"]) as ana:
        primeiro = ana.executar("select public.registrar_leitura_da_sessao(%s, %s::jsonb)",
                                (cenario["device_ana"], _payload()))[0][0]
        segundo = ana.executar("select public.registrar_leitura_da_sessao(%s, %s::jsonb)",
                               (cenario["device_ana"], _payload()))[0][0]
        assert primeiro is not None and segundo == primeiro
        assert _linhas(ana, cenario["device_ana"]) == 1


def test_a_mesma_epoca_pelos_dois_caminhos_e_uma_linha(como, cenario):
    """O celular e o dispositivo não podem gravar a mesma época duas vezes."""
    with como(cenario["ana"], papel=PAPEL) as ingestao:
        pelo_token = ingestao.executar("select public.registrar_leitura(%s, %s::jsonb)",
                                       (HASH_ANA, _payload()))[0][0]
        ingestao.cursor.execute("set local role authenticated")
        ingestao.cursor.execute(
            "select set_config('request.jwt.claims', %s, true)",
            (json.dumps({"sub": cenario["ana"], "role": "authenticated"}),))
        pela_sessao = ingestao.executar(
            "select public.registrar_leitura_da_sessao(%s, %s::jsonb)",
            (cenario["device_ana"], _payload()))[0][0]
        assert pela_sessao == pelo_token
        assert _linhas(ingestao, cenario["device_ana"]) == 1


def test_outra_epoca_no_mesmo_instante_continua_gravando(como, cenario):
    with como(cenario["ana"], papel=PAPEL) as ingestao:
        de_30 = ingestao.executar("select public.registrar_leitura(%s, %s::jsonb)",
                                  (HASH_ANA, _payload(epoca=30)))[0][0]
        de_60 = ingestao.executar("select public.registrar_leitura(%s, %s::jsonb)",
                                  (HASH_ANA, _payload(epoca=60)))[0][0]
        assert de_30 is not None and de_60 is not None and de_30 != de_60
        assert _linhas(ingestao, cenario["device_ana"]) == 2


def test_leitura_sem_instante_nao_e_deduplicada(como, cenario):
    """Declarado na 011: sem `captured_at` não há como saber que é a mesma."""
    with como(cenario["ana"], papel=PAPEL) as ingestao:
        # O cenário já traz leituras sem instante: mede o ACRÉSCIMO.
        antes = _linhas(ingestao, cenario["device_ana"], instante=None)
        ingestao.cursor.execute("set local role %s" % PAPEL)
        a = ingestao.executar("select public.registrar_leitura(%s, %s::jsonb)",
                              (HASH_ANA, _payload(instante=None)))[0][0]
        b = ingestao.executar("select public.registrar_leitura(%s, %s::jsonb)",
                              (HASH_ANA, _payload(instante=None)))[0][0]
        assert a is not None and b is not None and a != b
        assert _linhas(ingestao, cenario["device_ana"], instante=None) == antes + 2


def test_o_indice_e_as_funcoes_existem(catalogo):
    """Estrutural: é o que o diagnóstico de produção também confere."""
    assert catalogo("select indexname from pg_indexes "
                    "where indexname = 'sleep_data_epoca_unica'") == [("sleep_data_epoca_unica",)]
    linhas = catalogo(
        """
        select p.proname,
               pg_get_functiondef(p.oid) like '%%on conflict (device_id, captured_at, epoca_segundos)%%'
          from pg_proc p join pg_namespace n on n.oid = p.pronamespace
         where n.nspname = 'public'
           and p.proname in ('registrar_leitura', 'registrar_leitura_da_sessao')
         order by 1
        """
    )
    assert linhas == [("registrar_leitura", True), ("registrar_leitura_da_sessao", True)]
