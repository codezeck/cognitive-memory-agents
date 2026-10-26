from typing import Annotated

from fastapi import Path
from pydantic import BaseModel, Field

ID_REGEX = r"^[A-Za-z0-9_.-]{1,64}$"
UsuarioIdPath = Annotated[str, Path(pattern=ID_REGEX)]
MemoriaIdPath = Annotated[str, Path(pattern=ID_REGEX)]


class ConversaEntrada(BaseModel):
    usuario_id: str = Field(pattern=ID_REGEX)
    mensagem: str = Field(min_length=1, max_length=4000)
    provedor: str | None = Field(default=None, max_length=32)
    modelo: str | None = Field(default=None, max_length=100)


class ConversaSaida(BaseModel):
    resposta: str
    memorias_usadas: list[str]
    provedor: str
    modelo: str
    latencia_ms: int
    tokens_entrada: int | None = None   # preenchidos quando o agente repassar
    tokens_saida: int | None = None


class ProvedorSaida(BaseModel):
    provedor: str
    modelo: str
    local: bool
    configurado: bool
    padrao: bool


class MemoriaEntrada(BaseModel):
    texto: str = Field(min_length=1, max_length=2000)
    chave: str | None = Field(default=None, max_length=50)


class MemoriaCriadaSaida(BaseModel):
    id: str


class MemoriaBuscaSaida(BaseModel):
    id: str
    texto: str
    score: float


class ApagadasSaida(BaseModel):
    removidas: int