
from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    OpenAI,
)

from src.api.erros import ProvedorIndisponivel, ProvedorTimeout


class RespostaOpenAIVaziaError(RuntimeError):
    """Indica que a OpenAI retornou uma resposta vazia ou inválida."""


class OpenAIAdapter:
    """Implementa o contrato ModeloLLM usando a API da OpenAI."""

    def __init__(
        self,
        modelo: str,
        api_key: str,
        timeout: float = 60.0,
    ):
        self.modelo = modelo
        self.cliente = OpenAI(api_key=api_key, timeout=timeout)

    def gerar(self, mensagens: list[dict[str, str]]) -> str:
        try:
            resposta = self.cliente.chat.completions.create(
                model=self.modelo,
                messages=mensagens,
            )
        except APITimeoutError as erro:
            raise ProvedorTimeout(
                "A OpenAI demorou demais para responder."
            ) from erro
        except (APIConnectionError, APIStatusError) as erro:
            raise ProvedorIndisponivel(
                "Não foi possível consultar a OpenAI."
            ) from erro

        try:
            escolhas = resposta.choices
            texto = escolhas[0].message.content if escolhas else None
        except (AttributeError, IndexError, TypeError) as erro:
            raise RespostaOpenAIVaziaError(
                "A OpenAI retornou uma resposta inválida."
            ) from erro

        if not isinstance(texto, str) or not texto.strip():
            raise RespostaOpenAIVaziaError(
                "A OpenAI retornou uma resposta vazia."
            )

        return texto
