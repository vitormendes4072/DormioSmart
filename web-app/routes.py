from datetime import datetime, timezone

from flask import g, jsonify, request

import dispositivos
from auth import require_auth
from database import db
from device_auth import gerar_token, hash_token
from device_auth import extrair_token, hash_token
from validacao import validar_leitura

# Versao do contrato que este backend implementa (docs/DATA-CONTRACT.md).
CONTRATO_DE_DADOS = "1.2.0"

def init_routes(app):
    """Rotas da API.

    O Flask serve APENAS `/api/*` e `/health` (UI-09). As páginas são do SPA
    React, entregues como arquivos estáticos — ver `vercel.json` e
    `docs/DEPLOY.md`. As antigas rotas Jinja `/` e `/dashboard` foram
    removidas: desde o UI-08 elas eram inalcançáveis em produção, mas ainda
    respondiam em execução local, mostrando uma interface obsoleta que não
    existe mais no produto.
    """
    @app.route('/health')
    def health():
        """Health check (WEB-04).

        200 quando o app responde E o banco esta alcancavel; 503 quando o app
        esta de pe mas o banco nao — a distincao importa para um monitor de
        uptime saber se o problema e a aplicacao ou a fonte de dados.

        Sem autenticacao de proposito: um health check que exige credencial e
        inutil para monitoramento externo. Por isso a resposta nao revela nada
        alem de "ok"/"indisponivel" — nunca URL, chave ou erro de driver.
        """
        banco_ok, motivo = db.verificar_conexao()
        corpo = {
            "status": "ok" if banco_ok else "degradado",
            "banco": "ok" if banco_ok else (motivo or "indisponivel"),
            "contrato_de_dados": CONTRATO_DE_DADOS,
        }
        return jsonify(corpo), (200 if banco_ok else 503)

    @app.route('/api/sleep-history')
    @require_auth
    def get_history():
        """Leituras do usuário autenticado (AUTH-03).

        A consulta usa o JWT de quem pediu, então o RLS aplica a política por
        dono no banco. Continua devolvendo lista sempre — [] em qualquer
        falha, nunca 500 (FIX-01/FIX-08).
        """
        return jsonify(db.get_leituras_do_usuario(g.jwt, g.usuario_id))

    # --- Dispositivos do usuário (AUTH-05) ---
    #
    # Todas usam o cliente montado com o JWT de quem pediu: o RLS decide a
    # posse. O `user_id` vem sempre de `g.usuario_id`, nunca do corpo ou da URL.

    def _cliente_do_usuario():
        """Cliente com o JWT da requisição, ou None se indisponível."""
        return db.cliente_do_usuario(g.jwt)

    @app.route('/api/devices')
    @require_auth
    def listar_devices():
        client = _cliente_do_usuario()
        if client is None:
            return jsonify({"error": "fonte de dados indisponivel"}), 503

        lista = dispositivos.listar(client, g.usuario_id)
        if lista is None:
            return jsonify({"error": "fonte de dados indisponivel"}), 503
        return jsonify(lista)

    @app.route('/api/devices', methods=['POST'])
    @require_auth
    def criar_device():
        corpo = request.get_json(silent=True) or {}
        nome, erro = dispositivos.validar_nome(corpo.get("nome"))
        if erro:
            return jsonify({"error": erro}), 400

        client = _cliente_do_usuario()
        if client is None:
            return jsonify({"error": "fonte de dados indisponivel"}), 503

        token = gerar_token()
        device = dispositivos.criar(client, g.usuario_id, nome, hash_token(token))
        if device is None:
            return jsonify({"error": "nao foi possivel parear o dispositivo"}), 503

        # ÚNICA vez que o token em claro sai daqui. Não é recuperável depois:
        # o banco só tem o hash.
        return jsonify({"device": device, "token": token}), 201

    @app.route('/api/devices/<device_id>', methods=['PATCH'])
    @require_auth
    def renomear_device(device_id):
        corpo = request.get_json(silent=True) or {}
        if "nome" not in corpo:
            return jsonify({"error": "campo nome ausente"}), 400

        nome, erro = dispositivos.validar_nome(corpo.get("nome"))
        if erro:
            return jsonify({"error": erro}), 400

        client = _cliente_do_usuario()
        if client is None:
            return jsonify({"error": "fonte de dados indisponivel"}), 503

        device = dispositivos.renomear(client, g.usuario_id, device_id, nome)
        if device is None:
            # Inexistente e "de outra pessoa" respondem igual: distinguir
            # permitiria descobrir ids de dispositivos alheios.
            return jsonify({"error": "dispositivo nao encontrado"}), 404
        return jsonify(device)

    @app.route('/api/devices/<device_id>/revogar', methods=['POST'])
    @require_auth
    def revogar_device(device_id):
        client = _cliente_do_usuario()
        if client is None:
            return jsonify({"error": "fonte de dados indisponivel"}), 503

        agora = datetime.now(timezone.utc).isoformat()
        device = dispositivos.revogar(client, g.usuario_id, device_id, agora)
        if device is None:
            return jsonify({"error": "dispositivo nao encontrado"}), 404
        return jsonify(device)

    @app.route('/api/data', methods=['POST'])
    def receive_data():
        try:
            # --- AUTENTICAÇÃO DO DISPOSITIVO (SEC-02) ---
            # Antes de olhar o corpo: quem não se identifica não gasta nosso
            # tempo de parsing nem entra no banco.
            token = extrair_token(request.headers)
            if token is None:
                return jsonify({"error": "X-Device-Token ausente"}), 401

            device = db.get_device_by_token_hash(hash_token(token))
            if device is None:
                # Ausente, revogado ou desconhecido: a mesma resposta para os
                # três. Não informamos qual é o caso — isso só ajudaria quem
                # estivesse sondando tokens.
                return jsonify({"error": "device nao autorizado"}), 401

            content = request.json

            # --- VALIDAÇÃO DE ENTRADA (SEC-03) ---
            # Autenticado não é o mesmo que confiável: token roubado, sensor
            # solto ou firmware antigo não podem contaminar a base.
            content, erro = validar_leitura(content)
            if erro:
                return jsonify({"error": erro}), 400

            # --- O TRADUTOR ---
            # Aqui convertemos o "dialeto" do ESP32 (chaves curtas)
            # para o "idioma" do Supabase (nomes das colunas)
            payload = {
                "accel_x": content.get("ax"),
                "accel_y": content.get("ay"),
                "accel_z": content.get("az"),
                "gyro_x":  content.get("gx"),
                "gyro_y":  content.get("gy"),
                "gyro_z":  content.get("gz"),
                "temp":    content.get("t"),
                "movimento_total": content.get("total"),
                "status":  content.get("status"),
                # Carimbo do dono, resolvido pelo token — nunca vem do corpo
                # da requisição. O device não escolhe de quem é o dado.
                "user_id":   device["user_id"],
                "device_id": device["id"],
            }
            
            # Persiste e confirma: só responde 201 se o dado foi realmente
            # gravado. Se nada persistiu (fonte indisponível), responde 503 em
            # vez de mentir sucesso e enganar o firmware (FIX-02).
            result = db.insert_sleep_data(payload)
            if not result or not getattr(result, "data", None):
                return jsonify({"error": "dados nao persistidos (fonte indisponivel)"}), 503

            db.touch_device(device["id"])
            return jsonify({"status": "success"}), 201
        except Exception as e:
            return jsonify({"error": str(e)}), 400