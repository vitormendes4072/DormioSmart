from datetime import date
from pathlib import Path

import psycopg2
import pytest

CONSULTA = Path(__file__).resolve().parents[2] / "migrations" / "CONSULTA-onboarding.sql"


def test_o_titular_le_grava_e_limpa_a_meta(como, cenario):
    with como(cenario["ana"]) as ana:
        for meta in (60, 960, None):
            assert ana.contar_afetadas(
                "update public.profiles set meta_diaria_min = %s where id = %s", (meta, cenario["ana"])
            ) == 1
            assert ana.executar(
                "select meta_diaria_min from public.profiles where id = %s", (cenario["ana"],)
            ) == [(meta,)]


def test_outra_conta_nao_le_nem_grava_a_meta(como, cenario):
    with como(cenario["ana"]) as ana:
        assert ana.executar("select meta_diaria_min from public.profiles where id = %s", (cenario["bruno"],)) == []
        assert ana.contar_afetadas(
            "update public.profiles set meta_diaria_min = 480 where id = %s", (cenario["bruno"],)
        ) == 0


@pytest.mark.parametrize("meta", [59, 961])
def test_meta_fora_da_faixa_e_recusada(como, cenario, meta):
    with como(cenario["ana"]) as ana:
        with pytest.raises(psycopg2.errors.CheckViolation):
            ana.contar_afetadas(
                "update public.profiles set meta_diaria_min = %s where id = %s", (meta, cenario["ana"])
            )


def test_consulta_suprime_quatro_contas_e_conta_cobertura_sem_somar_aparelhos(url_do_banco, cenario):
    conexao = psycopg2.connect(url_do_banco)
    try:
        with conexao.cursor() as cur:
            ids = [f"00000000-0000-4000-9000-{i:012d}" for i in range(9)]
            for i, uid in enumerate(ids):
                # Domingo 23:30 no Brasil, já segunda no UTC.
                criacao = "2020-01-06 02:30+00" if i < 5 else "2020-01-13 02:30+00"
                cur.execute("insert into auth.users (id, email, created_at) values (%s, %s, %s)",
                            (uid, f"coorte{i}@exemplo.test", criacao))
            travesseiro, celular = ids[-2:]
            cur.execute("""
                insert into public.devices (id, user_id, nome, tipo)
                values (%s, %s, 'Travesseiro', 'travesseiro'), (%s, %s, 'Celular', 'celular')
            """, (travesseiro, ids[1], celular, ids[1]))

            def gravar(i, atraso, segundos, bancada=False, aparelho=None):
                cur.execute("""
                    insert into public.sleep_data (user_id, device_id, captured_at, epoca_segundos, bancada)
                    select id, %s, created_at + %s::interval + passo * interval '1 second',
                           least(3600, %s - passo), %s
                      from auth.users cross join generate_series(0, %s - 1, 3600) as passo
                     where id = %s
                """, (aparelho, atraso, segundos, bancada, segundos, ids[i]))

            gravar(0, "5 hours", 14_401)
            gravar(1, "168 hours", 14_400, aparelho=travesseiro)
            gravar(1, "168 hours", 14_400, aparelho=celular)
            gravar(2, "1 hour", 17_000, bancada=True)
            gravar(2, "168 hours 1 second", 30)
            gravar(3, "5 hours", 14_400)
            gravar(5, "1 hour", 20_000)
            cur.execute(CONSULTA.read_text(encoding="utf-8"))
            assert [c.name for c in cur.description] == [
                "semana", "contas_criadas", "primeiro_registro_em_7_dias", "contas_com_dia_acima_de_4h"
            ]
            assert cur.fetchall() == [(date(2019, 12, 30), 5, 3, 1)]
    finally:
        conexao.rollback()
        conexao.close()
