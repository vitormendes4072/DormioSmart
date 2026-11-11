import os
import sys

# Garante que o diretório web-app esteja no sys.path para importar
# os módulos da aplicação (routes, database) durante os testes.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


import pytest


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "sem_consentimento: o teste controla o consentimento (LGPD-12) por conta propria")


@pytest.fixture(autouse=True)
def _consentimento_vigente(request):
    """LGPD-12: por padrão, o titular dos testes consentiu.

    Sem isto, toda rota com a trava do consentimento responderia 403 nos testes que existiam antes
    dela, e eles passariam a testar o consentimento, não o que testam. Os testes da trava pedem o
    contrário com `@pytest.mark.sem_consentimento`, ou trocam o retorno pelo `patch` deles.
    """
    from unittest.mock import patch
    import consentimento
    vigente = None if request.node.get_closest_marker("sem_consentimento") else True
    if vigente is None:
        yield
        return
    with patch.object(consentimento, "estado", return_value=True):
        yield
