"""Interface local; credencial em cookie HttpOnly e API Bearer preservada."""
from __future__ import annotations

import logging
import os
import re
from pathlib import Path
from urllib.parse import quote, urlsplit
from typing import Literal

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.security import HTTPAuthorizationCredentials
from fastapi.routing import APIRoute
from pydantic import BaseModel, ConfigDict, Field

from src.api.dependencias import get_catalogo
from src.api.erros import AcessoNegado, NaoAutenticado
from src.api.schemas import ID_REGEX, MemoriaIdPath
from src.api.seguranca import usuario_autenticado
from src.interface import avaliacoes
from src.interface.analise import analisar_tarefa
from src.interface.protocolos import LIMITE_BYTES, fonte_v3, roteiros, validar_casos

class RotaLimitada(APIRoute):
    def get_route_handler(self):
        original = super().get_route_handler()

        async def limitado(request: Request):
            if request.method == 'POST' and request.url.path in {'/interface/avaliacoes', '/interface/conjuntos/validar', '/interface/relatorios/analise'}:
                partes, total = [], 0
                limite = 8 * 1024 * 1024 if request.url.path == '/interface/relatorios/analise' else LIMITE_BYTES + 16 * 1024
                async for parte in request.stream():
                    total += len(parte)
                    if total > limite:
                        raise HTTPException(413, 'Relatório excede 8 MB.' if request.url.path == '/interface/relatorios/analise' else 'Arquivo muito grande: use um conjunto JSON de até 128 KB.')
                    partes.append(parte)
                request._body = b''.join(partes)
            return await original(request)

        return limitado


router = APIRouter(prefix="/interface", include_in_schema=False, route_class=RotaLimitada)
PASTA = Path(__file__).parent / "static"
COOKIE = "cma_acesso"


class _SemConsultaNoLog(logging.Filter):
    def filter(self, registro):
        # O logger do cliente HTTP inclui a URL. O assunto da busca fica
        # fora do log, assim como o corpo das mensagens.
        if isinstance(registro.args, tuple):
            registro.args = tuple(
                item.copy_with(query=None)
                if isinstance(item, httpx.URL) and item.host == "api-interna"
                else item
                for item in registro.args
            )
        return True


logging.getLogger("httpx").addFilter(_SemConsultaNoLog())


class EntradaLogin(BaseModel):
    model_config = ConfigDict(extra="forbid")
    token: str = Field(min_length=1, max_length=1024)


class EntradaDemonstracao(BaseModel):
    model_config = ConfigDict(extra="forbid")
    perfil: str = Field(default="a", pattern="^[ab]$")


@router.get("/configuracao")
def configuracao_publica():
    return _sem_cache(JSONResponse({"demonstracao_local": os.getenv("MODO_DEMONSTRACAO") == "1"}))


class EntradaMensagem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    mensagem: str = Field(min_length=1, max_length=4000)
    provedor: str | None = Field(default=None, max_length=32)
    modelo: str | None = Field(default=None, max_length=100)


class EntradaConsulta(BaseModel):
    model_config = ConfigDict(extra="forbid")
    consulta: str = Field(min_length=1, max_length=500)


class EntradaAvaliacao(BaseModel):
    model_config = ConfigDict(extra="forbid")
    modelo: str = Field(min_length=1, max_length=100)
    repeticoes: int = Field(default=1, strict=True, ge=1, le=3)
    protocolo: Literal['comparativo_v3', 'p6'] = 'comparativo_v3'
    casos: list[dict] | None = Field(default=None, min_length=1, max_length=20)


class EntradaConjunto(BaseModel):
    model_config = ConfigDict(extra='forbid')
    casos: list[dict] = Field(min_length=1, max_length=20)


class EntradaRelatorio(BaseModel):
    model_config = ConfigDict(extra='forbid')
    documento: dict


def mesma_origem(request: Request):
    origem = request.headers.get("origin")
    if request.headers.get("sec-fetch-site") == "cross-site":
        raise AcessoNegado("Abra a interface pelo endereço local da aplicação.")
    if origem:
        url = urlsplit(origem)
        if (url.scheme, url.netloc) != (request.url.scheme, request.url.netloc):
            raise AcessoNegado("A origem da solicitação não é permitida.")


def credencial(request: Request) -> tuple[str, str]:
    mesma_origem(request)
    token = request.cookies.get(COOKIE)
    if not token:
        raise NaoAutenticado("Entre na interface com sua credencial local.")
    usuario = usuario_autenticado(HTTPAuthorizationCredentials(scheme="Bearer", credentials=token))
    if not re.fullmatch(ID_REGEX, usuario):
        raise AcessoNegado("O usuário associado à credencial não tem um identificador válido.")
    return token, usuario


def _sem_cache(response: Response) -> Response:
    response.headers["Cache-Control"] = "no-store"
    return response


@router.post('/conjuntos/validar')
def validar_conjunto(corpo: EntradaConjunto, auth=Depends(credencial)):
    try:
        validar_casos(corpo.casos)
    except ValueError as erro:
        raise HTTPException(422, str(erro)) from None
    return _sem_cache(JSONResponse({'valido': True, 'casos': corpo.casos,
                                   'quantidade': len(corpo.casos), 'limite_bytes': LIMITE_BYTES}))


@router.get('/roteiros')
def consultar_roteiros(auth=Depends(credencial)):
    return _sem_cache(JSONResponse({'protocolos': roteiros()}))


@router.post('/relatorios/analise')
def analisar_relatorio(corpo: EntradaRelatorio, auth=Depends(credencial)):
    return _sem_cache(JSONResponse(analisar_tarefa(corpo.documento)))


@router.get('/conjuntos/exemplo')
def baixar_exemplo(auth=Depends(credencial)):
    # Um exemplo real do conjunto oficial; 1/3 repetições são opções de execução.
    return _sem_cache(JSONResponse(fonte_v3()[:1], headers={
        'Content-Disposition': 'attachment; filename="modelo-casos-comparativo.json"'}))


@router.get('/conjuntos/oficial')
def baixar_conjunto_oficial(auth=Depends(credencial)):
    return _sem_cache(JSONResponse(fonte_v3(), headers={
        'Content-Disposition': 'attachment; filename="dataset-validacao-v3.json"'}))


@router.post("/demonstracao", dependencies=[Depends(mesma_origem)])
def entrar_demonstracao(corpo: EntradaDemonstracao, request: Request):
    if os.getenv("MODO_DEMONSTRACAO") != "1":
        raise HTTPException(404, "Demonstração local não habilitada.")
    if request.url.hostname not in {"localhost", "127.0.0.1", "::1"}:
        raise AcessoNegado("O acesso automático é exclusivo do endereço local da demonstração.")
    from src.inicializacao import ler_credenciais
    try:
        perfil = ler_credenciais()[corpo.perfil]
    except (OSError, ValueError, KeyError, TypeError):
        raise HTTPException(503, "Credenciais locais indisponíveis. Confira a preparação do Docker.") from None
    token, usuario = perfil["token"], perfil["usuario_id"]
    usuario_autenticado(HTTPAuthorizationCredentials(scheme="Bearer", credentials=token))
    resposta = JSONResponse({"usuario_id": usuario, "modo_teste": os.getenv("USAR_FALSOS") == "1",
                            "perfil": corpo.perfil})
    resposta.set_cookie(COOKIE, token, httponly=True, samesite="strict", path="/interface",
                        secure=request.url.scheme == "https", max_age=30 * 24 * 3600)
    return _sem_cache(resposta)


async def api(request, metodo, rota, token, **kwargs):
    # O transporte ASGI chama as rotas reais, com suas dependências e a mesma
    # autorização Bearer; não duplica regras de memória nem abre outra porta.
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=request.app, raise_app_exceptions=False),
        base_url="http://api-interna", headers={"Authorization": "Bearer " + token},
        trust_env=False,
    ) as client:
        r = await client.request(metodo, rota, **kwargs)
    if r.status_code == 204:
        return _sem_cache(Response(status_code=204))
    return _sem_cache(JSONResponse(r.json(), status_code=r.status_code))


@router.get("/sessao")
def identidade(auth=Depends(credencial)):
    return _sem_cache(JSONResponse({
        "usuario_id": auth[1], "modo_teste": os.getenv("USAR_FALSOS") == "1",
        "perfil": "b" if auth[1] == "demo_visitante" else "a",
    }))


@router.post("/sessao", dependencies=[Depends(mesma_origem)])
def entrar(corpo: EntradaLogin, request: Request):
    token = corpo.token.strip()
    usuario = usuario_autenticado(HTTPAuthorizationCredentials(scheme="Bearer", credentials=token))
    if not re.fullmatch(ID_REGEX, usuario):
        raise AcessoNegado("O identificador do usuário configurado é inválido.")
    resposta = JSONResponse({"usuario_id": usuario, "modo_teste": os.getenv("USAR_FALSOS") == "1"})
    resposta.set_cookie(
        COOKIE, token, httponly=True, samesite="strict", path="/interface",
        secure=request.url.scheme == "https",
    )
    return _sem_cache(resposta)


@router.delete("/sessao", dependencies=[Depends(mesma_origem)])
def sair():
    resposta = Response(status_code=204)
    resposta.delete_cookie(COOKIE, path="/interface", httponly=True, samesite="strict")
    return _sem_cache(resposta)


@router.post("/conversas")
async def conversar(corpo: EntradaMensagem, request: Request, auth=Depends(credencial)):
    return await api(request, "POST", "/conversas", auth[0],
                     json={"usuario_id": auth[1], **corpo.model_dump()})


@router.post("/nova-sessao")
async def nova_sessao(request: Request, auth=Depends(credencial)):
    return await api(request, "POST", f"/usuarios/{quote(auth[1], safe='')}/sessoes", auth[0])


@router.post("/memorias")
async def memorias(
    corpo: EntradaConsulta, request: Request, auth=Depends(credencial),
):
    return await api(request, "GET", f"/usuarios/{quote(auth[1], safe='')}/memorias",
                     auth[0], params={"consulta": corpo.consulta, "k": 5})


@router.delete("/memorias/{memoria_id}")
async def excluir_memoria(memoria_id: MemoriaIdPath, request: Request, auth=Depends(credencial)):
    return await api(request, "DELETE", f"/usuarios/{quote(auth[1], safe='')}/memorias/{memoria_id}", auth[0])


@router.delete("/memorias")
async def excluir_todas(request: Request, auth=Depends(credencial)):
    return await api(request, "DELETE", f"/usuarios/{quote(auth[1], safe='')}/memorias", auth[0])


@router.get("/disponibilidade")
async def disponibilidade(auth=Depends(credencial), catalogo=Depends(get_catalogo)):
    modelos = catalogo.listar()
    estado = "indisponivel"
    instalados = []
    try:
        async with httpx.AsyncClient(timeout=3, trust_env=False) as client:
            r = await client.get(os.getenv("OLLAMA_HOST", "http://localhost:11434").rstrip("/") + "/api/tags")
            r.raise_for_status()
            instalados = [m["name"] for m in r.json().get("models", []) if isinstance(m.get("name"), str)]
            estado = "disponivel"
    except (httpx.HTTPError, ValueError, KeyError, TypeError):
        pass
    return _sem_cache(JSONResponse({
        "api": "disponivel", "ollama": estado, "modelos_instalados": instalados,
        "modelos": modelos,
        "comparativo_liberado": os.getenv("HABILITAR_COMPARATIVO_INTERFACE") == "1",
        "impedimento_avaliacao": avaliacoes.impedimento(),
        "avaliacao_ativa": avaliacoes.ativa(auth[1]),
    }))


@router.post("/avaliacoes")
def iniciar_avaliacao(
    corpo: EntradaAvaliacao, request: Request, auth=Depends(credencial), catalogo=Depends(get_catalogo),
):
    if request.url.hostname not in {'localhost', '127.0.0.1', '::1'}:
        raise AcessoNegado('Avaliações pela interface são exclusivas do endereço local da aplicação.')
    catalogo.resolver("ollama", corpo.modelo)
    return _sem_cache(JSONResponse(
        avaliacoes.iniciar(auth[1], corpo.modelo, corpo.repeticoes, corpo.protocolo, corpo.casos), status_code=202,
    ))


@router.get('/avaliacoes')
def historico_avaliacoes(deslocamento: int = Query(default=0, ge=0),
                        limite: int = Query(default=20, ge=1, le=50), auth=Depends(credencial)):
    return _sem_cache(JSONResponse(avaliacoes.listar(auth[1], deslocamento, limite)))


@router.get("/avaliacoes/{codigo}")
def consultar_avaliacao(codigo: str, auth=Depends(credencial)):
    documento, _ = avaliacoes.consultar(codigo, auth[1])
    if isinstance(documento.get('relatorio'), dict):
        documento['relatorio'] = {**documento['relatorio'], 'analise_tarefa': analisar_tarefa(documento['relatorio'])}
    return _sem_cache(JSONResponse(documento))


@router.get("/avaliacoes/{codigo}/relatorio")
def baixar_relatorio(codigo: str, auth=Depends(credencial)):
    documento, caminho = avaliacoes.consultar(codigo, auth[1])
    if caminho is None:
        raise HTTPException(409, documento.get("mensagem", "A avaliação ainda está em andamento."))
    return _sem_cache(FileResponse(caminho, media_type="application/json", filename="avaliacao-memoria.json"))
