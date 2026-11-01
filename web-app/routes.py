import logging
import time
from datetime import datetime, timezone

from flask import g, jsonify, request
from werkzeug.exceptions import HTTPException

import dispositivos
import features_noite
import lote
import perfil
from auth import extrair_bearer, require_auth
from database import INDISPONIVEL, db
from consulta import ler_parametros
from ingestao import CAMINHO_SESSAO, CAMINHO_TOKEN, extrair_device_id, identificar_caminho
from device_auth import extrair_token, gerar_token, hash_token
from validacao import colunas_de_features, validar_captacao, validar_leitura

logger = logging.getLogger(__name__)


def _resposta_de_falha(e, rota):
    """Exceção que escapou de uma rota de ingestão (API-04).

    Erro HTTP do próprio Flask (JSON malformado, `Content-Type` errado) é
    culpa do pedido e mantém o código dele (400, 415). Qualquer outra é bug
    do servidor: 500, com o detalhe só no log. Até 01/11 as duas viravam
    400 com `str(e)` no corpo, e o firmware descartava uma leitura válida
    por causa de um defeito nosso -- além de expor o texto interno.
    """
    if isinstance(e, HTTPException):
        return jsonify({"error": e.name.lower()}), e.code
    logger.exception("erro interno em %s", rota)
    return jsonify({"error": "erro interno"}), 500

# Versao do contrato que este backend implementa (docs/DATA-CONTRACT.md).
#
# 2.5.0 acrescentou `f`/`g`/`fs` -- o vetor de caracteristicas por epoca
# (DATA-07a) -- e esta declaracao subiu junto. Isso NAO significa que a
# ingestao processe esses campos: significa que ela e conforme a 2.5.0, e ela
# e, porque os tres sao OPCIONAIS e nada obrigatorio mudou. Um payload sem eles
# continua sendo o payload correto, e e o unico que existe hoje.
#
# O que ainda falta e o DATA-07b: aceitar, validar e persistir o vetor. Ate la
# `f` cai na validacao como campo desconhecido, que e o comportamento desejado
# -- aceita-lo sem ter coluna para grava-lo descartaria o dado em silencio.
#
# 2.5.1 (30/09, DATA-07c) e PATCH e nao mexeu em formato nenhum: acrescentou a
# secao 2.6 dois fatos medidos -- epoca incompleta nao tem paridade entre
# implementacoes, e o `‖g‖ = 1 ± 1e−3` e coerencia de um lado, nao orcamento de
# discordancia. Nada de campo, faixa ou obrigatoriedade muda, entao a ingestao
# continua conforme sem alterar uma linha de codigo.
#
# A declaracao, porem, FICOU ATRAS por duas semanas: o documento subiu em
# 2026-09-30 e esta constante nao. O `test_informa_a_versao_do_contrato_de_dados`
# acusou na primeira vez que a suite do backend rodou depois disso (16/10) --
# a suite nao era executada desde 10/09. A deteccao funcionou; o intervalo entre
# o bug e a deteccao e que foi de duas semanas, e e por isso que o backend
# tambem precisa rodar em cada push, nao so quando alguem lembra.
#
# 2.6.0 (30/10, API-03) e MINOR: `POST /api/data/lote`, rota nova e opcional.
# Nada do `/api/data` mudou; um firmware que nunca use o lote continua conforme.
#
# 2.7.0 (30/10, DATA-07b) e MINOR: `f`/`g`/`fs` validados e gravados, e
# `GET /api/features`. Payload sem `f` continua sendo o payload correto.
CONTRATO_DE_DADOS = "2.7.0"

# Frase exigida no corpo de `DELETE /api/me` (SEC-07). Em portugues e em
# maiusculas de proposito: tem de ser digitada, e nao pode ser o resultado de
# um retry automatico ou de um clique duplo.
CONFIRMACAO_EXCLUSAO = "APAGAR MINHA CONTA"

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

    #: A janela de `/api/features`. Uma noite cabe com folga; acima disso, a
    #: `inclinacao_rel` passaria a ser contra a postura típica de dias.
    JANELA_MAXIMA_DE_FEATURES_H = 24

    @app.route('/api/features')
    @require_auth
    def get_features():
        """As oito features por época de uma janela (DATA-07b (e)).

        `device`, `desde` e `ate` são obrigatórios: `inclinacao_rel` é medida
        contra a postura típica DA JANELA (`g_ref`), então a janela faz parte
        do resultado e não pode ficar implícita. O "conceito de noite" é do
        `ESC-01`; até lá, quem pede escolhe, e a resposta devolve o `g_ref` e a
        janela usados.
        """
        parametros, erro = ler_parametros(request.args)
        if erro:
            return jsonify({"error": erro}), 400
        faltando = [n for n, k in (("device", "device_id"), ("desde", "desde"), ("ate", "ate"))
                    if not parametros[k]]
        if faltando:
            return jsonify({"error": "parametros obrigatorios: " + ", ".join(faltando)}), 400
        desde = features_noite.instante_do_banco(parametros["desde"])
        ate = features_noite.instante_do_banco(parametros["ate"])
        if desde.tzinfo is None or ate.tzinfo is None:
            return jsonify({"error": "'desde' e 'ate' precisam de fuso horario"}), 400
        if (ate - desde).total_seconds() > JANELA_MAXIMA_DE_FEATURES_H * 3600:
            return jsonify({"error": f"janela acima de {JANELA_MAXIMA_DE_FEATURES_H} h"}), 400

        linhas = db.get_features_do_usuario(
            g.jwt, g.usuario_id, parametros["device_id"], desde.isoformat(), ate.isoformat())
        if linhas is None:
            return jsonify({"error": "consulta indisponivel"}), 503

        epocas = [e for e in map(features_noite.epoca_da_linha, linhas) if e is not None]
        saida, g_ref = features_noite.derivar_noite(epocas)
        return jsonify({
            "device_id": parametros["device_id"],
            "desde": desde.isoformat(),
            "ate": ate.isoformat(),
            "ordem_features": list(features_noite.ORDEM_FEATURES),
            "g_ref": g_ref,
            "lacuna_maxima_s": features_noite.LACUNA_MAXIMA_S,
            "epocas": saida,
        })

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
        device = dispositivos.criar(client, nome, hash_token(token), tipo)
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
        a credencial é obrigatória e única no esquema (agora em
        `device_tokens`, SEC-08), e um segredo que ninguém conhece é mais
        seguro do que abrir exceção de nulo para esta classe de dispositivo. O
        caminho por token simplesmente não é utilizável neste registro — o que
        é exatamente o desejado.
        """
        client = _cliente_do_usuario()
        if client is None:
            return jsonify({"error": "fonte de dados indisponivel"}), 503

        device = dispositivos.primeiro_do_tipo(client, g.usuario_id, "celular")
        if device is not None:
            return jsonify(device), 200

        device = dispositivos.criar(
            client, dispositivos.NOME_CELULAR, hash_token(gerar_token()), "celular",
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

    # --- Perfil do titular (PERFIL-01, LGPD art. 18, III) ---
    #
    # `public.profiles` é a FONTE DE VERDADE do nome e da idade desde o
    # `PERFIL-01`. Antes dele a tabela era escrita uma vez pelo gatilho do
    # signup e lida por nada, e o nome exibido vinha de
    # `auth.users.raw_user_meta_data` — duas cópias, nenhuma declarada
    # canônica. A decisão inteira, inclusive a parte que não é código, está em
    # `docs/DECISAO-FONTE-DO-PERFIL.md`.
    #
    # As duas rotas vão pelo CLIENTE DO USUÁRIO, nunca por papel privilegiado:
    # o RLS decide a posse no banco, e `tests/test_privilegio_minimo.py`
    # reprova se alguém trocar isso por `cliente_de_ingestao`. O e-mail NÃO
    # passa por aqui — é credencial de acesso, trocada pelo Supabase Auth com
    # confirmação por link (ver `frontend/src/lib/perfil.ts`).

    @app.route('/api/me/perfil')
    @require_auth
    def ler_meu_perfil():
        """Nome e idade do titular, de `public.profiles`.

        ⚠️ **ESTE `GET` ESCREVE, e é deliberado.** Quando não há linha para o
        usuário, a rota a cria — semeada pelo nome do metadado do cadastro — e
        devolve `perfil_criado_agora: true`.

        O motivo não é hipótese: `migrations/DIAGNOSTICO-perfil-nao-criado.sql`
        existe porque já houve usuário criado com `profiles` vazio (o gatilho
        `handle_new_user` não existia no projeto), com reparo manual por SQL.
        Enquanto a tabela era inerte, linha ausente era detalhe de esquema;
        com ela canônica, linha ausente é **nome em branco na tela de quem
        digitou o nome no cadastro**.

        A alternativa — deixar a tela cair para o metadado quando a linha falta
        — foi recusada: criaria um segundo leitor do metadado sob condição, e
        invariante com cláusula de exceção é o que apodrece primeiro. Reparar
        mantém "só `profiles` é lida" verdadeiro sem exceção.

        A operação é **idempotente**, que é a propriedade que de fato importa
        num `GET`: chamar dez vezes deixa o mesmo estado que chamar uma.
        """
        client = _cliente_do_usuario()
        if client is None:
            return jsonify({"error": "fonte de dados indisponivel"}), 503

        dados = perfil.ler(client, g.usuario_id)
        if dados is None:
            return jsonify({"error": "fonte de dados indisponivel"}), 503

        if dados:
            return jsonify({**dados, "perfil_criado_agora": False})

        # Linha ausente: reparo. A semente pode vir vazia (metadado sem nome,
        # ou Auth fora do ar) — e aí o perfil nasce com nome nulo. Nulo é
        # estado que a tela sabe mostrar; perfil inexistente, não.
        semente = db.nome_do_metadado(g.jwt)
        criado = perfil.gravar(client, g.usuario_id, {"nome": semente})
        if criado is None:
            # Não inventa sucesso nem devolve perfil vazio como se fosse lido:
            # o titular precisa saber que a leitura não aconteceu (FIX-02).
            return jsonify({"error": "fonte de dados indisponivel"}), 503

        logger.warning(
            "Perfil ausente reparado na leitura. O gatilho handle_new_user "
            "pode nao existir no projeto -- ver "
            "migrations/DIAGNOSTICO-perfil-nao-criado.sql."
        )
        return jsonify({**criado, "perfil_criado_agora": True})

    @app.route('/api/me/perfil', methods=['PATCH'])
    @require_auth
    def corrigir_meu_perfil():
        """Correção de nome e idade (LGPD art. 18, III).

        `PATCH` parcial: só o que vem no corpo é alterado. Campo ausente e
        campo `null` são coisas diferentes — ausente é "não mexa", `null` é
        "apague", e é assim que o titular retira a idade sem apagar o nome.

        Campo desconhecido responde **400**, e isso inclui `id` e `user_id`: o
        dono sai do JWT e não existe por onde informá-lo. Aceitar e descartar
        em silêncio responderia sucesso a um pedido que não foi atendido.

        Devolve a linha **como ficou no banco**, não como foi pedida: é a
        diferença entre confirmar a escrita e confirmar a intenção (FIX-02).
        """
        campos, erro = perfil.ler_alteracao(request.get_json(silent=True))
        if erro:
            return jsonify({"error": erro}), 400

        client = _cliente_do_usuario()
        if client is None:
            return jsonify({"error": "fonte de dados indisponivel"}), 503

        gravado = perfil.gravar(client, g.usuario_id, campos)
        if gravado is None:
            return jsonify({"error": "perfil nao atualizado (fonte indisponivel)"}), 503

        return jsonify(gravado), 200

    # --- Direito de eliminação (SEC-07, LGPD art. 18, VI) ---

    @app.route('/api/me', methods=['DELETE'])
    @require_auth
    def apagar_minha_conta():
        """Elimina todo o dado pessoal do titular. Irreversível.

        A confirmação explícita no corpo não é cerimônia: é a única barreira
        entre um `DELETE` disparado por engano — um fetch repetido, um botão
        clicado duas vezes, um cliente HTTP com retry automático — e a perda
        definitiva de todo o histórico de sono. A frase tem de ser digitada,
        então não sai de retry nenhum.

        O dono NUNCA vem daqui: a função no banco usa `auth.uid()` e não aceita
        parâmetro de usuário. Ver migrations/006.
        """
        corpo = request.get_json(silent=True) or {}
        if corpo.get("confirmacao") != CONFIRMACAO_EXCLUSAO:
            return jsonify({
                "error": "confirmacao necessaria",
                "envie": {"confirmacao": CONFIRMACAO_EXCLUSAO},
            }), 400

        recibo = db.apagar_minha_conta(g.jwt)
        if recibo is None:
            return jsonify({"error": "fonte de dados indisponivel"}), 503

        # A eliminação pode ser parcial: o dado de `public` sai, mas a linha de
        # `auth.users` (que guarda o e-mail) depende de privilégio que não
        # existe em todo projeto. Dizer isso ao titular é obrigação — uma
        # resposta de sucesso limpa esconderia dado pessoal remanescente.
        if not recibo.get("conta_de_acesso_removida"):
            recibo["aviso"] = (
                "Seus dados de sono, dispositivos e perfil foram apagados. "
                "O cadastro de acesso (e-mail) ainda existe e precisa ser "
                "removido pelo administrador."
            )
            # WARNING, nao INFO: e uma pendencia de conformidade, nao um evento
            # de rotina. Sem id de usuario no log — seria guardar justamente o
            # dado que se acabou de apagar.
            logger.warning(
                "Exclusao de conta incompleta: auth.users nao removida. "
                "Ver migrations/006 e o README."
            )

        return jsonify(recibo), 200

    def _device_por_token():
        """Caminho do dispositivo em campo (SEC-02).

        Devolve o dispositivo já com o hash do token: a gravação o repassa ao
        banco para que o DONO seja resolvido lá dentro, e não aqui (SEC-06).
        """
        token = extrair_token(request.headers)
        if token is None:
            return None, "X-Device-Token ausente", 401

        token_hash = hash_token(token)
        device = db.get_device_by_token_hash(token_hash)
        if device is INDISPONIVEL:
            # O banco falhou ao resolver o token (AUTH-08): 503, para o
            # firmware recuar e reenviar, e não 401 "nao autorizado".
            return None, "fonte de dados indisponivel", 503
        if device is None:
            # Ausente, revogado ou desconhecido: a mesma resposta para os
            # três. Não informamos qual é o caso — isso só ajudaria quem
            # estivesse sondando tokens.
            return None, "device nao autorizado", 401
        return dict(device, token_hash=token_hash), None, 200

    def _device_por_sessao():
        """Caminho do celular (APP-08): a sessão já identifica o dono.

        O `user_id` sai do JWT validado, nunca do corpo. O cliente informa
        apenas QUAL dos seus dispositivos está enviando, e isso é conferido
        contra o dono antes de qualquer escrita.
        """
        jwt = extrair_bearer(request.headers)
        usuario_id = db.validar_token_de_usuario(jwt) if jwt else None
        if usuario_id is INDISPONIVEL:
            return None, "servico de autenticacao indisponivel", 503
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

        # `buscar_do_dono` não devolve `user_id` (não está em CAMPOS). O `jwt`
        # segue junto porque a gravação deste caminho vai pelo cliente do
        # USUÁRIO, não por chave privilegiada: a função no banco deriva o dono
        # de `auth.uid()` (SEC-06).
        return dict(device, user_id=usuario_id, jwt=jwt), None, 200

    def _gravar_leitura(caminho, device, content):
        """Valida, traduz e grava UMA leitura (FIX-02, SEC-03, SEC-06).

        Devolve `(True, None, 201)` quando a gravação foi confirmada, e
        `(False, motivo, status)` quando não: 400 para leitura inválida (não
        adianta reenviar) e 503 para banco que não persistiu (adianta).

        Extraído de `receive_data` para o lote (API-03) usar exatamente a
        mesma regra: uma leitura não pode ser válida num caminho e inválida
        no outro.
        """

        # --- VALIDAÇÃO DE ENTRADA (SEC-03) ---
        # Autenticado não é o mesmo que confiável: token roubado, sensor
        # solto ou firmware antigo não podem contaminar a base.
        content, erro = validar_leitura(content)
        if erro:
            return False, erro, 400

        # Instante da MEDIÇÃO, quando o dispositivo souber informá-lo
        # (contrato v2.0.0). O `created_at` do banco continua sendo o do
        # recebimento — este é um campo novo, não uma substituição.
        captado_em, erro = validar_captacao(content.get("ts"))
        if erro:
            return False, erro, 400

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
            # Vetor da época (DATA-07b, contrato §2.6). Uma coluna por feature,
            # com o NOME dela, e não um array: um array na ordem errada passaria
            # em toda faixa. Nulos quando a leitura não traz `f`.
            **colunas_de_features(content),
            # `user_id` e `device_id` NÃO entram aqui (SEC-06). Quem carimba
            # o dono é a função no banco, a partir do token ou do
            # `auth.uid()` do JWT. Antes eram estas duas linhas de Python
            # que separavam uma chave vazada da posse de dado alheio; agora
            # não existe parâmetro por onde escolher o dono.
        }

        # Persiste e confirma: só responde 201 se o dado foi realmente
        # gravado. Se nada persistiu (fonte indisponível), responde 503 em
        # vez de mentir sucesso e enganar o firmware (FIX-02).
        #
        # Dois caminhos, duas credenciais — e nenhum dos dois manda o dono:
        #
        #   token   -> chave de ingestão (privilégio mínimo), dono do token
        #   sessão  -> JWT do usuário,    dono de `auth.uid()`
        #
        # O `last_seen_at` do dispositivo é atualizado dentro da própria
        # função, na mesma chamada — ver migrations/005.
        if caminho == CAMINHO_TOKEN:
            gravado = db.registrar_leitura(device["token_hash"], payload)
        else:
            gravado = db.registrar_leitura_da_sessao(
                device["jwt"], device["id"], payload
            )

        if not gravado:
            return False, "dados nao persistidos (fonte indisponivel)", 503

        return True, None, 201

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

            gravado, erro, status = _gravar_leitura(caminho, device, content)
            if not gravado:
                return jsonify({"error": erro}), status

            return jsonify({"status": "success"}), 201
        except Exception as e:
            return _resposta_de_falha(e, "/api/data")

    @app.route('/api/data/lote', methods=['POST'])
    def receive_lote():
        """Várias leituras numa requisição só (API-03). Ver `lote.py`."""
        try:
            # Autenticação antes do envelope, como no `/api/data`: quem não se
            # identifica não recebe diagnóstico do próprio corpo.
            caminho = identificar_caminho(request.headers)
            if caminho == CAMINHO_TOKEN:
                device, erro, status = _device_por_token()
            elif caminho == CAMINHO_SESSAO:
                device, erro, status = _device_por_sessao()
            else:
                return jsonify({"error": "credencial ausente"}), 401
            if device is None:
                return jsonify({"error": erro}), status

            leituras, erro, status = lote.extrair_leituras(request.get_json(silent=True))
            if erro:
                return jsonify({"error": erro}), status

            resposta = lote.nova_resposta()
            inicio = time.monotonic()
            for indice, content in enumerate(leituras):
                # Passou do orçamento: o resto volta como pendente, inteiro,
                # em vez de a função serverless morrer no meio do lote.
                if time.monotonic() - inicio > lote.ORCAMENTO_DE_TEMPO_S:
                    resposta["pendentes"].extend(range(indice, len(leituras)))
                    break

                try:
                    gravado, erro, status = _gravar_leitura(caminho, device, content)
                except Exception:
                    # Leitura inválida não levanta: `_gravar_leitura` devolve 400.
                    # Exceção aqui é bug do servidor (API-04), e a leitura pode ser
                    # boa: vira PENDENTE, como no 503, e não rejeitada -- rejeitada
                    # o dispositivo descarta para sempre. As anteriores continuam
                    # em `aceitas`, em vez de a exceção derrubar o lote inteiro.
                    # Custo: um item que derrube o servidor sempre trava a fila
                    # até a correção; a flash guarda 11 dias, e o log mostra.
                    logger.exception("erro interno no item %d do lote", indice)
                    gravado, erro, status = False, None, 503
                if gravado:
                    resposta["aceitas"].append(indice)
                elif status == 503:
                    # O banco não persistiu. Insistir nas próximas só acumula
                    # falha e tempo: param aqui, e o dispositivo reenvia.
                    resposta["pendentes"].extend(range(indice, len(leituras)))
                    break
                else:
                    resposta["rejeitadas"].append({"indice": indice, "erro": erro})

            return jsonify(resposta), lote.status_da_resposta(resposta)
        except Exception as e:
            return _resposta_de_falha(e, "/api/data/lote")