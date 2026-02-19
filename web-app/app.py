import sys
import os

# Adiciona o diretório atual (web-app) ao caminho de busca do Python
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from flask import Flask
from routes import init_routes

app = Flask(__name__)

# Inicializa as rotas isoladas
init_routes(app)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)