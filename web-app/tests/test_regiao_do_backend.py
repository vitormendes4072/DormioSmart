"""O backend roda na região do banco (INFRA-05).

Até 11/11 as funções da Vercel rodavam em `iad1` (Washington), o padrão nunca
mudado, e o banco do Supabase fica em `sa-east-1` (São Paulo). Cada chamada ao
banco cruzava o continente: o envio de uma noite (930 épocas) levou 4 min 48 s
em 38 requisições, a 0,15–0,40 s por gravação — das quais o banco gastava
0,43 ms (`pg_stat_statements`). Diário, 11/11.

A região do banco não está no repositório (é configuração do painel do
Supabase); está aqui, como constante, e mudar o projeto de região é mudar as
duas linhas juntas.
"""
import json
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]

#: Região do projeto no Supabase (painel: Project Settings → General), 11/11.
REGIAO_DO_BANCO = "sa-east-1"

#: A região da Vercel mais perto de cada região do Supabase em uso.
VERCEL_PERTO_DO_BANCO = {"sa-east-1": "gru1"}


def test_as_funcoes_rodam_na_regiao_do_banco():
    config = json.loads((RAIZ / "vercel.json").read_text(encoding="utf-8"))
    # Sem a chave, a Vercel usa `iad1` — o que causou o INFRA-05.
    assert config.get("regions") == [VERCEL_PERTO_DO_BANCO[REGIAO_DO_BANCO]], (
        "as funções da Vercel precisam rodar perto do banco "
        f"({REGIAO_DO_BANCO}); ver INFRA-05 no backlog"
    )
