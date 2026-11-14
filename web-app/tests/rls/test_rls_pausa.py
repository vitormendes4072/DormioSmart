"""API-07: posse, descarte e retomada no PostgreSQL real."""
import psycopg2
import pytest


def test_so_titular_altera_e_aparelhos_comecam_habilitados(como, cenario):
    proprio, alheio = cenario["device_ana"], cenario["device_bruno"]
    with como(cenario["ana"]) as ana:
        assert ana.executar("select receber_leituras from devices where id = %s", (proprio,)) == [(True,)]
        for receber in (False, False, True):
            assert ana.executar(
                "update devices set receber_leituras = %s where id = %s returning receber_leituras",
                (receber, proprio),
            ) == [(receber,)]
        assert ana.contar_afetadas(
            "update devices set receber_leituras = false where id = %s", (alheio,),
        ) == 0


@pytest.mark.parametrize("por_token", [False, True], ids=["sessao", "token"])
def test_pausa_descarta_retomada_preserva_credencial_e_revogacao_prevalece(
    como, cenario, por_token,
):
    from test_rls_ingestao import HASH_ANA

    device = cenario["device_ana"]
    sql = (
        "select registrar_leitura(%s, %s::jsonb)" if por_token
        else "select registrar_leitura_da_sessao(%s::uuid, %s::jsonb)"
    )
    credencial = HASH_ANA if por_token else device
    with como(cenario["ana"]) as ana:
        def estado(receber):
            ana.executar("set local role authenticated")
            ana.executar("update devices set receber_leituras = %s where id = %s", (receber, device))
            if por_token:
                ana.executar("set local role dormio_ingestao")

        estado(False)
        ana.executar("savepoint leitura_pausada")
        with pytest.raises(psycopg2.Error) as pausa:
            ana.executar(sql, (credencial, '{"movimento_total": 6.543}'))
        assert pausa.value.pgcode == "PT409"
        assert pausa.value.diag.message_primary == "aparelho_pausado"
        ana.executar("rollback to savepoint leitura_pausada")
        estado(True)
        assert ana.executar(sql, (credencial, '{"movimento_total": 6.544}'))[0][0]
        ana.executar("set local role authenticated")
        assert ana.executar(
            "select movimento_total from sleep_data where device_id = %s and movimento_total in (6.543, 6.544)",
            (device,),
        ) == [(6.544,)]
        ana.executar("update devices set receber_leituras = false, revoked_at = now() where id = %s", (device,))
        estado(True)
        assert ana.executar(sql, (credencial, '{"movimento_total": 6.545}')) == [(None,)]
