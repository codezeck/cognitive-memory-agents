import os
from dataclasses import dataclass

PROVEDORES_LOCAIS = {"ollama"}


def _ler_modelos(texto: str) -> tuple[tuple[str, str], ...]:
    """'ollama:qwen2.5-coder:3b,ollama:llama3.2:3b' -> (('ollama','qwen2.5-coder:3b'), ...)"""
    pares = []
    for item in texto.split(","):
        provedor, _, modelo = item.strip().partition(":")  # separa só no 1º ':'
        if provedor and modelo:
            pares.append((provedor.lower(), modelo))
    return tuple(pares)


@dataclass(frozen=True)
class Configuracao:
    provedor_padrao: str
    modelo_padrao: str
    modelos_permitidos: tuple[tuple[str, str], ...]

    def exige_chave(self, provedor: str) -> bool:
        return provedor not in PROVEDORES_LOCAIS

    def chave_de(self, provedor: str) -> str | None:
        if not self.exige_chave(provedor):
            return None
        return os.getenv(f"{provedor.upper()}_API_KEY") or None


def carregar_configuracao() -> Configuracao:
    provedor = os.getenv("LLM_PROVIDER", "ollama").lower()
    modelo = os.getenv("LLM_MODEL", "qwen2.5-coder:3b")
    permitidos = _ler_modelos(os.getenv("MODELOS_PERMITIDOS", ""))
    if (provedor, modelo) not in permitidos:
        permitidos = ((provedor, modelo),) + permitidos
    return Configuracao(provedor, modelo, permitidos)