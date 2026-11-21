import re
from urllib.parse import parse_qs, urlsplit

import pytest
from fastapi.testclient import TestClient

from src.api.main import app


@pytest.mark.parametrize("caminho", [
    "/", "/interface/arquivos/app.mjs", "/interface/arquivos/relatorio.mjs",
    "/interface/arquivos/estilo.css",
])
def test_interface_revalida_pagina_e_modulos(caminho):
    with TestClient(app) as cliente:
        resposta = cliente.get(caminho)
        assert resposta.status_code == 200
        assert resposta.headers["cache-control"] == "no-cache"
        # A revalidação condicional continua segura, sem servir bytes desnecessários.
        condicional = cliente.get(caminho, headers={"If-None-Match": resposta.headers["etag"]})
        assert condicional.status_code in (200, 304)
        assert condicional.headers["cache-control"] == "no-cache"


def test_modulos_p6_tem_novos_enderecos_para_cache_anterior():
    with TestClient(app) as cliente:
        pagina = cliente.get("/").text
        app_url = re.search(r'<script type="module" src="([^"]+)"', pagina).group(1)
        versao = parse_qs(urlsplit(app_url).query)["v"]
        codigo = cliente.get(app_url)
        assert codigo.status_code == 200
        relatorio_url = re.search(r'from "(\./relatorio\.mjs[^"]+)"', codigo.text).group(1)
        assert parse_qs(urlsplit(relatorio_url).query)["v"] == versao
        relatorio = cliente.get("/interface/arquivos/" + relatorio_url.removeprefix("./"))
        assert relatorio.status_code == 200
        assert "tokensP6(doc,c)" in relatorio.text
