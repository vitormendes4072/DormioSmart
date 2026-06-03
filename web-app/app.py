import os
import sys

# --- BLOCO DE CORREÇÃO DE PATH ---
# Descobre onde este arquivo (app.py) está
base_dir = os.path.dirname(os.path.abspath(__file__))

# Força o Python a olhar para esta pasta ao procurar imports
if base_dir not in sys.path:
    sys.path.insert(0, base_dir)
# ---------------------------------

# Carrega variáveis de ambiente do .env (desenvolvimento local).
# Em produção (Vercel), as vars já estão no ambiente e load_dotenv()
# não as sobrescreve — seguro em qualquer ambiente. (FIX-03)
from dotenv import load_dotenv
load_dotenv()

from flask import Flask
# Agora o Python consegue achar o routes.py
from routes import init_routes

app = Flask(__name__)

# Inicializa as rotas
init_routes(app)

# O Vercel precisa que a variável 'app' esteja disponível globalmente.
# Não coloque nada dentro de blocos 'if' que impeça a criação do app.

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)