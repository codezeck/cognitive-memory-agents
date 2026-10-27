from types import SimpleNamespace
from openai import APIStatusError

import httpx
import pytest

from openai import APIConnectionError, APITimeoutError

from src.api.erros import ProvedorIndisponivel, ProvedorTimeout
from src.modelos.openai_adapter import (
    OpenAIAdapter,
    RespostaOpenAIVaziaError,
)


class ClienteFalso:
    def __init__(self, resposta=None, erro=None):
        self.resposta = resposta
        self.erro = erro
        self.chat = SimpleNamespace(
            completions=SimpleNamespace(create=self.create)
        )
        self.chamada = None

    def create(self, **kwargs):
        self.chamada = kwargs
        if self.erro:
            raise self.erro
        return self.resposta


def resposta_com(texto):
    return SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(content=texto)
            )
        ]
    )


def test_openai_retorna_texto_e_envia_modelo(monkeypatch):
    cliente = ClienteFalso(resposta_com("Olá!"))
    monkeypatch.setattr(
        "src.modelos.openai_adapter.OpenAI",
        lambda **kwargs: cliente,
    )

    adaptador = OpenAIAdapter("gpt-test", "chave-teste")
    mensagens = [{"role": "user", "content": "Oi"}]

    assert adaptador.gerar(mensagens) == "Olá!"
    assert cliente.chamada["model"] == "gpt-test"
    assert cliente.chamada["messages"] == mensagens


def test_openai_resposta_vazia_gera_erro(monkeypatch):
    cliente = ClienteFalso(resposta_com("   "))
    monkeypatch.setattr(
        "src.modelos.openai_adapter.OpenAI",
        lambda **kwargs: cliente,
    )

    adaptador = OpenAIAdapter("gpt-test", "chave-teste")

    with pytest.raises(RespostaOpenAIVaziaError):
        adaptador.gerar([{"role": "user", "content": "Oi"}])


def test_openai_timeout_e_convertido(monkeypatch):
    request = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")
    cliente = ClienteFalso(erro=APITimeoutError(request=request))
    monkeypatch.setattr(
        "src.modelos.openai_adapter.OpenAI",
        lambda **kwargs: cliente,
    )

    adaptador = OpenAIAdapter("gpt-test", "chave-teste")

    with pytest.raises(ProvedorTimeout):
        adaptador.gerar([{"role": "user", "content": "Oi"}])


def test_openai_falha_de_conexao_e_convertida(monkeypatch):
    request = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")
    cliente = ClienteFalso(
        erro=APIConnectionError(request=request)
    )
    monkeypatch.setattr(
        "src.modelos.openai_adapter.OpenAI",
        lambda **kwargs: cliente,
    )

    adaptador = OpenAIAdapter("gpt-test", "chave-teste")

    with pytest.raises(ProvedorIndisponivel):
        adaptador.gerar([{"role": "user", "content": "Oi"}])



def test_openai_sem_escolhas_gera_erro(monkeypatch):
    cliente = ClienteFalso(
        SimpleNamespace(choices=[])
    )
    monkeypatch.setattr(
        "src.modelos.openai_adapter.OpenAI",
        lambda **kwargs: cliente,
    )

    adaptador = OpenAIAdapter("gpt-test", "chave-teste")

    with pytest.raises(RespostaOpenAIVaziaError):
        adaptador.gerar([{"role": "user", "content": "Oi"}])


def test_openai_conteudo_nao_textual_gera_erro(monkeypatch):
    cliente = ClienteFalso(resposta_com(None))
    monkeypatch.setattr(
        "src.modelos.openai_adapter.OpenAI",
        lambda **kwargs: cliente,
    )

    adaptador = OpenAIAdapter("gpt-test", "chave-teste")

    with pytest.raises(RespostaOpenAIVaziaError):
        adaptador.gerar([{"role": "user", "content": "Oi"}])



@pytest.mark.parametrize("status_code", [401, 429, 500])
def test_openai_erro_http_e_convertido(monkeypatch, status_code):
    request = httpx.Request(
        "POST",
        "https://api.openai.com/v1/chat/completions",
    )
    resposta_http = httpx.Response(
        status_code,
        request=request,
        json={"error": {"message": "erro simulado"}},
    )
    erro = APIStatusError(
        "Erro HTTP simulado",
        response=resposta_http,
        body={"error": {"message": "erro simulado"}},
    )
    cliente = ClienteFalso(erro=erro)

    monkeypatch.setattr(
        "src.modelos.openai_adapter.OpenAI",
        lambda **kwargs: cliente,
    )

    adaptador = OpenAIAdapter("gpt-test", "chave-teste")

    with pytest.raises(ProvedorIndisponivel):
        adaptador.gerar([{"role": "user", "content": "Oi"}])
