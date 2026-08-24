"""Parâmetros da consulta de leituras (DASH-05, DASH-06)."""
import pytest

from consulta import (
    LIMITE_MAXIMO,
    LIMITE_PADRAO,
    ler_parametros,
    validar_instante,
    validar_limite,
    validar_uuid,
)

UUID = "8f14e45f-ceea-467a-9f3d-a1b2c3d4e5f6"


class TestValidarUuid:
    def test_aceita_uuid_e_normaliza_para_minusculas(self):
        assert validar_uuid(UUID.upper()) == UUID

    def test_ignora_espacos_em_volta(self):
        assert validar_uuid(f"  {UUID}  ") == UUID

    @pytest.mark.parametrize(
        "valor",
        ["", "abc", UUID[:-1], UUID + "0", "8f14e45f_ceea_467a_9f3d_a1b2c3d4e5f6", None, 42],
    )
    def test_recusa_o_que_nao_e_uuid(self, valor):
        assert validar_uuid(valor) is None

    def test_recusa_injecao_de_filtro(self):
        # PostgREST interpreta operadores no valor. Nada além de uuid passa.
        assert validar_uuid(f"{UUID},status.eq.Movimento") is None


class TestValidarInstante:
    def test_aceita_iso_com_fuso(self):
        assert validar_instante("2026-08-23T01:00:00+00:00") is not None

    def test_aceita_sufixo_z(self):
        # `fromisoformat` só entende "Z" a partir do 3.11; normalizamos antes
        # para não depender da versão do interpretador do deploy.
        assert validar_instante("2026-08-23T01:00:00Z") is not None

    def test_aceita_data_sem_hora(self):
        assert validar_instante("2026-08-23") is not None

    @pytest.mark.parametrize("valor", ["ontem", "23/08/2026", "", "   ", None, 0])
    def test_recusa_o_que_nao_e_instante(self, valor):
        assert validar_instante(valor) is None


class TestValidarLimite:
    def test_ausente_usa_o_padrao(self):
        assert validar_limite(None) == LIMITE_PADRAO

    def test_respeita_o_valor_pedido(self):
        assert validar_limite("480") == 480

    def test_grampeia_no_teto_em_vez_de_recusar(self):
        # Pedir demais não é erro do usuário — é só mais do que servimos.
        assert validar_limite("999999") == LIMITE_MAXIMO

    @pytest.mark.parametrize("valor", ["0", "-1", "20.5", "muitos", ""])
    def test_recusa_o_que_nao_e_inteiro_positivo(self, valor):
        assert validar_limite(valor) is None


class TestLerParametros:
    def test_sem_nada_devolve_o_comportamento_antigo(self):
        parametros, erro = ler_parametros({})
        assert erro is None
        assert parametros == {
            "device_id": None,
            "desde": None,
            "ate": None,
            "limite": LIMITE_PADRAO,
        }

    def test_string_vazia_e_tratada_como_ausente(self):
        # `?device=` acontece quando o cliente monta a query com valor nulo.
        parametros, erro = ler_parametros({"device": "", "desde": "", "limite": ""})
        assert erro is None
        assert parametros["device_id"] is None
        assert parametros["limite"] == LIMITE_PADRAO

    def test_recorta_por_dispositivo(self):
        parametros, erro = ler_parametros({"device": UUID})
        assert erro is None
        assert parametros["device_id"] == UUID

    def test_device_malformado_e_erro_e_nao_lista_vazia(self):
        parametros, erro = ler_parametros({"device": "nao-e-uuid"})
        assert parametros is None
        assert "device" in erro

    def test_janela_completa(self):
        parametros, erro = ler_parametros(
            {"desde": "2026-08-22T00:00:00Z", "ate": "2026-08-23T00:00:00Z"}
        )
        assert erro is None
        assert parametros["desde"] < parametros["ate"]

    def test_janela_invertida_e_erro(self):
        # Devolver vazio faria o usuário achar que não há dado no período.
        _, erro = ler_parametros(
            {"desde": "2026-08-23T00:00:00Z", "ate": "2026-08-22T00:00:00Z"}
        )
        assert erro is not None

    def test_instante_malformado_diz_qual_parametro(self):
        _, erro = ler_parametros({"ate": "amanha"})
        assert "ate" in erro
