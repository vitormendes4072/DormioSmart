from datetime import datetime, timezone

from flask import g, jsonify, request

import dispositivos
from auth import extrair_bearer, require_auth
from database import db
from consulta import ler_parametros
from ingestao import CAMINHO_SESSAO, CAMINHO_TOKEN, extrair_device_id, identificar_caminho
from device_auth import extrair_token, gerar_token, hash_token
from validacao import validar_captacao, validar_leitura

# Versao do contrato que este backend implementa (docs/DATA-CONTRACT.md).
CONTRATO_DE_DADOS = "2.2.0"

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
        """Leituras do usuário autenticado (AUTH-03, DASH-05, DASH-06).

        A consulta usa o JWT de quem pediu, então o RLS aplica a política por
        dono no banco. Continua devolvendo lista sempre — [] em qualquer
        falha de infraestrutura, nunca 500 (FIX-01/FIX-08).

        Aceita recorte opcional por `device`, janela `desde`/`ate` e `limite`.
        Sem parâmetro nenhum o comportamento é o de antes: as 20 leituras mais
        recentes de todos os dispositivos do usuário.

        Parâmetro malformado responde **400**, e não lista vazia: um uuid
        digitado errado que devolvesse `[]` faria o usuário concluir que o
        dispositivo não mandou nada. Ver a nota em `consulta.py`.
        """
        parametros, erro = ler_parametros(request.args)
        if erro:
            return jsonify({"error": erro}), 400

        return jsonify(
            db.get_leituras_do_usuario(
                g.jwt,
                g.usuario_id,
                device_id=parametros["device_id"],
                desde=parametros["desde"],
                ate=parametros["ate"],
                limite=parametros["limite"],
            )
        )

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

        # Ausente vira 'travesseiro': todo dispositivo que existia antes do
        # DATA-05 e um ESP32, e cliente antigo continua funcionando.
        tipo, erro = dispositivos.validar_tipo(corpo.get("tipo"))
        if erro:
            return jsonify({"error": erro}), 400

        client = _cliente_do_usuario()
        if client is None:
            return jsonify({"error": "fonte de dados indisponivel"}), 503

        token = gerar_token()
        device = dispositivos.criar(client, g.usuario_id, nome, hash_token(token), tipo)
        if device is None:
            return jsonify({"error": "nao foi possivel parear o dispositivo"}), 503

        # ÚNICA vez que o token em claro sai daqui. Não é recuperável depois:
        # o banco só tem o hash.
        return jsonify({"device": device, "token": token}), 201

    @app.route('/api/devices/celular', methods=['POST'])
    @require_auth
    def device_do_celular():
        """Devolve o dispositivo `celular` do usuário, criando se não houver.

        É o pareamento automático do APP-08. Sem isto, quem quer usar o
        próprio aparelho precisa parear à mão e colar um token de 43
        caracteres — fluxo de desenvolvedor, não de usuário.

        **Reaproveita em vez de criar.** Uma chamada por sessão de coleta,
        criando toda vez, encheria a conta de dispositivos órfãos e tornaria
        o painel inútil. Create-or-get.

        **Não devolve token, e isso é o ponto.** O aparelho vai enviar
        autenticado por sessão (ver `ingestao.py`), então nenhuma credencial
        de escrita precisa existir no navegador.

        O `token_hash` da linha é gerado e o valor em claro é **descartado**:
        a coluna é obrigatória e única no esquema, e um segredo que ninguém
        conhece é mais seguro do que abrir exceção de nulo para esta classe
        de dispositivo. O caminho por token simplesmente não é utilizável
        neste registro — o que é exatamente o desejado.
        """
        client = _cliente_do_usuario()
        if client is None:
            return jsonify({"error": "fonte de dados indisponivel"}), 503

        device = dispositivos.primeiro_do_tipo(client, g.usuario_id, "celular")
        if device is not None:
            return jsonify(device), 200

        device = dispositivos.criar(
            client, g.usuario_id, dispositivos.NOME_CELULAR,
            hash_token(gerar_token()), "celular",
        )
        if device is None:
            return jsonify({"error": "nao foi possivel preparar o dispositivo"}), 503
        return jsonify(device), 201

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

    def _device_por_token():
        """Caminho do dispositivo em campo (SEC-02). Inalterado."""
        token = extrair_token(request.headers)
        if token is None:
            return None, "X-Device-Token ausente", 401

        device = db.get_device_by_token_hash(hash_token(token))
        if device is None:
            # Ausente, revogado ou desconhecido: a mesma resposta para os
            # três. Não informamos qual é o caso — isso só ajudaria quem
            # estivesse sondando tokens.
            return None, "device nao autorizado", 401
        return device, None, 200

    def _device_por_sessao():
        """Caminho do celular (APP-08): a sessão já identifica o dono.

        O `user_id` sai do JWT validado, nunca do corpo. O cliente informa
        apenas QUAL dos seus dispositivos está enviando, e isso é conferido
        contra o dono antes de qualquer escrita.
        """
        jwt = extrair_bearer(request.headers)
        usuario_id = db.validar_token_de_usuario(jwt) if jwt else None
        if usuario_id is None:
            return None, "sessao invalida ou expirada", 401

        device_id, erro = extrair_device_id(request.get_json(silent=True))
        if erro:
            return None, erro, 400

        client = db.cliente_do_usuario(jwt)
        if client is None:
            return None, "fonte de dados indisponivel", 503

        device = dispositivos.buscar_do_dono(client, usuario_id, device_id)
        if device is None:
            # Inexistente, revogado e "de outra pessoa" respondem igual:
            # distinguir permitiria descobrir ids de dispositivos alheios.
            return None, "dispositivo nao encontrado", 404

        # `buscar_do_dono` não devolve `user_id` (não está em CAMPOS), e o
        # resto da rota carimba a linha com ele. Vem do JWT, não do corpo.
        return dict(device, user_id=usuario_id), None, 200

    @app.route('/api/data', methods=['POST'])
    def receive_data():
        try:
            # --- AUTENTICAÇÃO DO DISPOSITIVO (SEC-02) ---
            # Antes de olhar o corpo: quem não se identifica não gasta nosso
            # tempo de parsing nem entra no banco.
            # Dois caminhos, um por classe de origem. Ver `ingestao.py` para
            # o porquê. O `user_id` nunca vem do corpo em nenhum dos dois.
            caminho = identificar_caminho(request.headers)

            if caminho == CAMINHO_TOKEN:
                device, erro, status = _device_por_token()
            elif caminho == CAMINHO_SESSAO:
                device, erro, status = _device_por_sessao()
            else:
                return jsonify({"error": "credencial ausente"}), 401

            if device is None:
                return jsonify({"error": erro}), status

            content = request.json

            # --- VALIDAÇÃO DE ENTRADA (SEC-03) ---
            # Autenticado não é o mesmo que confiável: token roubado, sensor
            # solto ou firmware antigo não podem contaminar a base.
            content, erro = validar_leitura(content)
            if erro:
                return jsonify({"error": erro}), 400

            # Instante da MEDIÇÃO, quando o dispositivo souber informá-lo
            # (contrato v2.0.0). O `created_at` do banco continua sendo o do
            # recebimento — este é um campo novo, não uma substituição.
            captado_em, erro = validar_captacao(content.get("ts"))
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
                # Agregação por época (v2.0.0). Nulos para o ESP32, que envia
                # amostra instantânea.
                "captured_at":      captado_em,
                "epoca_segundos":   content.get("epoca_s"),
                "metodo_agregacao": content.get("metodo"),
                "amostras":         content.get("amostras"),
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