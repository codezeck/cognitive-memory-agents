"""Interface da memória de longo prazo.

Qualquer implementação (RAM, PostgreSQL + pgvector) deve respeitar este
contrato. Os itens devolvidos por `buscar` têm a chave "texto", que é o
formato que `agent.formatar_memorias` já aceita.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class MemoriaLongoPrazo(Protocol):
    def salvar(
        self,
        usuario_id: str,
        texto: str,
        chave: str | None = None,
        metadados: dict | None = None,
    ) -> str:
        """Guarda uma memória e devolve o id.

        Se `chave` for informada (ex.: "cidade"), a memória ativa anterior do
        mesmo usuário com a mesma chave é substituída e deixa de ser devolvida
        pela busca.
        """

    def listar_por_usuario(self, usuario_id: str) -> list[dict]:
        """Lista memórias do usuário, incluindo registros inativos,
        para reconstruir o índice do gerenciador.
        """
        ...
    

    def buscar(self, usuario_id: str, consulta: str, k: int = 5) -> list[dict]:
        """Devolve até k memórias ativas, da mais para a menos relevante.

        Cada item: {"id": str, "texto": str, "score": float}.
        """

    def atualizar(self, usuario_id: str, memoria_id: str, novo_texto: str) -> bool:
        """Altera o texto de uma memória ativa. False se não existir."""

    def esquecer(self, usuario_id: str, memoria_id: str) -> bool:
        """Apaga uma memória. False se não existir."""

    def esquecer_usuario(self, usuario_id: str) -> int:
        """Apaga todas as memórias do usuário (LGPD). Devolve quantas."""
