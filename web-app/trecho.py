"""DATA-16: o trecho de uma sessão — aparelho, início e fim — para excluir ou marcar.

O servidor guarda épocas, e não sessões: a sessão é deduzida no cliente pelas
pausas no envio. Para excluir ou marcar uma, o cliente manda o aparelho e os
dois instantes que desenhou na tela, e o banco age sobre as épocas do titular
nesse intervalo (migração 023, `apagar_trecho` e `marcar_trecho`).

A validação aqui repete a do banco (`_conferir_trecho`) de propósito: o banco é
a última barreira, e esta é a que devolve 400 com o motivo, em vez de um erro
de banco que a rota trataria como indisponibilidade.
"""
from datetime import datetime

from consulta import validar_instante, validar_uuid

#: O mesmo teto da 023. Um início ou fim errado não leva a conta inteira.
JANELA_MAXIMA_H = 48

#: Como na exclusão da conta, a frase no corpo é a barreira contra o pedido
#: repetido por engano (retry, clique duplo): nenhum deles a escreve.
CONFIRMACAO_APAGAR = "APAGAR ESTA SESSAO"


def ler_trecho(corpo):
    """`((device_id, desde, ate), None)` ou `(None, mensagem de erro)`.

    `desde` e `ate` voltam em ISO 8601 com fuso. Instante sem fuso é recusado:
    o banco o leria no fuso da sessão, e o trecho apagado não seria o da tela.
    """
    if not isinstance(corpo, dict):
        return None, "corpo JSON obrigatorio"
    device_id = validar_uuid(corpo.get("device"))
    if not device_id:
        return None, "device invalido"
    desde = validar_instante(corpo.get("desde"))
    ate = validar_instante(corpo.get("ate"))
    if not desde or not ate:
        return None, "'desde' e 'ate' obrigatorios, em ISO 8601"
    inicio, fim = datetime.fromisoformat(desde), datetime.fromisoformat(ate)
    if inicio.utcoffset() is None or fim.utcoffset() is None:
        return None, "'desde' e 'ate' precisam de fuso horario"
    if fim < inicio:
        return None, "'ate' antes de 'desde'"
    if (fim - inicio).total_seconds() > JANELA_MAXIMA_H * 3600:
        return None, f"trecho acima de {JANELA_MAXIMA_H} h"
    return (device_id, desde, ate), None
