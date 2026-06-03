from flask import render_template, request, jsonify
from database import db

def init_routes(app):
    @app.route('/')
    def index():
        return render_template('dashboard.html')

    @app.route('/api/sleep-history')
    def get_history():
        # get_latest_data() já devolve uma lista ([] em caso de falha),
        # garantindo JSON válido e evitando 500 em produção (FIX-01).
        return jsonify(db.get_latest_data())

    @app.route('/api/data', methods=['POST'])
    def receive_data():
        try:
            content = request.json
            
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
                "status":  content.get("status")
            }
            
            # Persiste e confirma: só responde 201 se o dado foi realmente
            # gravado. Se nada persistiu (fonte indisponível), responde 503 em
            # vez de mentir sucesso e enganar o firmware (FIX-02).
            result = db.insert_sleep_data(payload)
            if not result or not getattr(result, "data", None):
                return jsonify({"error": "dados nao persistidos (fonte indisponivel)"}), 503

            return jsonify({"status": "success"}), 201
        except Exception as e:
            return jsonify({"error": str(e)}), 400