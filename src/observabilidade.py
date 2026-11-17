"""Observacao opt-in, autenticada e somente leitura no processo real da API."""
from __future__ import annotations

from datetime import datetime, timezone
import os
import re
import unicodedata
import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from src import agent
from src.api.seguranca import usuario_autenticado

router = APIRouter(prefix="/avaliacao", include_in_schema=False)
INSTANCIA = uuid.uuid4().hex


class Alvo(BaseModel):
    model_config = ConfigDict(extra="forbid")
    rotulo: str = Field(pattern=r"^[A-Za-z0-9_.-]{1,64}$")
    termos: list[str] = Field(min_length=1, max_length=8)


class ConsultaRAM(BaseModel):
    model_config = ConfigDict(extra="forbid")
    alvos: list[Alvo] = Field(default_factory=list, max_length=32)


def _normalizar(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", texto.casefold())
    return " ".join("".join(c for c in texto if not unicodedata.combining(c)).split())


@router.post("/ram")
def observar_ram(corpo: ConsultaRAM, usuario: str = Depends(usuario_autenticado)):
    if os.getenv("HABILITAR_OBSERVACAO_RAM") != "1":
        raise HTTPException(404, "Observação de avaliação não habilitada.")
    permitidos = set(os.getenv("USUARIOS_AVALIACAO_RAM", "").split(","))
    if usuario not in permitidos:
        raise HTTPException(403, "Identidade fora do ambiente de avaliação autorizado.")
    rotulos = [a.rotulo for a in corpo.alvos]
    if len(set(rotulos)) != len(rotulos) or any(
        not termo.strip() or len(termo) > 200 for alvo in corpo.alvos for termo in alvo.termos
    ):
        raise HTTPException(422, "Alvos precisam de rótulos distintos e termos de 1 a 200 caracteres.")
    # Nao usar obter_historico: esse metodo criaria uma entrada se inexistente.
    original = agent.historicos_por_usuario.get(usuario)
    mensagens = tuple(dict(m) for m in original) if original is not None else ()
    pessoais = [m for m in mensagens if m.get("role") in {"user", "assistant"}]
    indices_alvo = set()
    contagens = {}
    for alvo in corpo.alvos:
        padroes = [re.compile(r"(?<!\w)" + re.escape(_normalizar(t)) + r"(?!\w)") for t in alvo.termos]
        encontrados = {i for i, m in enumerate(pessoais)
                       if any(p.search(_normalizar(m.get("content", ""))) for p in padroes)}
        indices_alvo.update(encontrados)
        contagens[alvo.rotulo] = len(encontrados)
    resposta = {
        "versao_observador": "ram-v1", "instancia_id": INSTANCIA, "pid": os.getpid(),
        "usuario_id": usuario, "coletado_em": datetime.now(timezone.utc).isoformat(),
        "escopo": "historico_do_usuario_neste_processo", "processos_cobertos": 1,
        "historico_existe": original is not None, "mensagens_total": len(mensagens),
        "mensagens_sistema": sum(m.get("role") == "system" for m in mensagens),
        "mensagens_usuario": sum(m.get("role") == "user" for m in mensagens),
        "mensagens_assistente": sum(m.get("role") == "assistant" for m in mensagens),
        "mensagens_pessoais": len(pessoais), "alvos_no_historico": len(indices_alvo),
        "mensagens_pessoais_sem_alvo": len(pessoais) - len(indices_alvo),
        "ocorrencias_por_rotulo": contagens,
        "limitacao": "Correspondencias literais normalizadas; avaliar sem escritores concorrentes e cobrir todos os workers relevantes.",
    }
    # Nao devolver textos, termos-alvo, tokens ou mensagens de outro usuario.
    return JSONResponse(resposta, headers={"Cache-Control": "no-store"})
