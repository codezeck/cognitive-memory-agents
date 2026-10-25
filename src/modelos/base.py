
from typing import Protocol


class ModeloLLM(Protocol):
    """Contrato que qualquer integração de modelo deve seguir."""

    def gerar(self, mensagens: list[dict[str, str]]) -> str:
        """Recebe mensagens e retorna o texto gerado pelo modelo."""
        ...
