from flask import render_template, request, jsonify
from database import db

def init_routes(app):
    @app.route('/')
    def index():
        return render_template('dashboard.html')

    @app.route('/api/sleep-history')
    def get_history():
        response = db.get_latest_data()
        return jsonify(response.data)

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
            
            # Agora enviamos o payload traduzido
            db.insert_sleep_data(payload)
            
            return jsonify({"status": "success"}), 201
        except Exception as e:
            return jsonify({"error": str(e)}), 400