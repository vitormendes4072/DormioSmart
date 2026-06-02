import os
import sys

# Garante que o diretório web-app esteja no sys.path para importar
# os módulos da aplicação (routes, database) durante os testes.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
