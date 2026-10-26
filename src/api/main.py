import logging
import time

from fastapi import Depends, FastAPI, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from src.api.dependencias import get_catalogo, get_conversador, get_memoria
from src.api.erros import ErroDominio, MemoriaNaoEncontrada
from src.api.schemas import (ApagadasSaida, ConversaEntrada, ConversaSaida,
                             MemoriaBuscaSaida, MemoriaCriadaSaida,
                             MemoriaEntrada, MemoriaIdPath, ProvedorSaida,
                             UsuarioIdPath)

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("api")

app = FastAPI(title="API de Memória de Longo Prazo", version="0.1.0")


# ---------- erros: todos saem no mesmo formato {codigo, mensagem} ----------
@app.exception_handler(ErroDominio)
async def tratar_erro_dominio(request: Request, exc: ErroDominio):
    log.warning("erro %s: %s", exc.codigo, exc.mensagem)
    return JSONResponse(status_code=exc.status_http,
                        content={"codigo": exc.codigo, "mensagem": exc.mensagem})


@app.exception_handler(RequestValidationError)
async def tratar_validacao(request: Request, exc: RequestValidationError):
    campos = [".".join(str(p) for p in e["loc"] if p not in ("body", "path", "query"))
              for e in exc.errors()]
    return JSONResponse(status_code=422, content={
        "codigo": "entrada_invalida",
        "mensagem": "Dados inválidos nos campos: " + ", ".join(campos)})


@app.exception_handler(ValueError)
async def tratar_valor_invalido(request: Request, exc: ValueError):
    # a memória e o agente levantam ValueError para entradas inválidas (ex.: texto em branco)
    return JSONResponse(status_code=422, content={
        "codigo": "entrada_invalida", "mensagem": str(exc)})


@app.exception_handler(Exception)
async def tratar_inesperado(request: Request, exc: Exception):
    log.exception("erro inesperado")  # o detalhe fica só no log, nunca vai ao cliente
    return JSONResponse(status_code=500, content={
        "codigo": "erro_interno", "mensagem": "Erro interno. Tente novamente."})


# ---------- endpoints ----------
@app.get("/saude")
def saude():
    return {"status": "ok"}


@app.get("/provedores", response_model=list[ProvedorSaida])
def provedores(catalogo=Depends(get_catalogo)):
    return catalogo.listar()


@app.post("/conversas", response_model=ConversaSaida)
def conversar(corpo: ConversaEntrada, conversador=Depends(get_conversador),
              catalogo=Depends(get_catalogo)):
    selecao = catalogo.resolver(corpo.provedor, corpo.modelo)
    inicio = time.perf_counter()
    r = conversador.conversar(corpo.usuario_id, corpo.mensagem, selecao)
    latencia = int((time.perf_counter() - inicio) * 1000)
    # o texto da mensagem não vai para o log (privacidade)
    log.info("conversa usuario=%s provedor=%s modelo=%s memorias=%d latencia_ms=%d",
             corpo.usuario_id, selecao.provedor, selecao.modelo,
             len(r.memorias_usadas), latencia)
    return ConversaSaida(resposta=r.resposta, memorias_usadas=r.memorias_usadas,
                         provedor=selecao.provedor, modelo=selecao.modelo,
                         latencia_ms=latencia, tokens_entrada=r.tokens_entrada,
                         tokens_saida=r.tokens_saida)


@app.post("/usuarios/{usuario_id}/sessoes", status_code=204)
def nova_sessao(usuario_id: UsuarioIdPath, conversador=Depends(get_conversador)):
    conversador.nova_sessao(usuario_id)


@app.post("/usuarios/{usuario_id}/memorias", response_model=MemoriaCriadaSaida,
          status_code=201)
def criar_memoria(usuario_id: UsuarioIdPath, corpo: MemoriaEntrada,
                  memoria=Depends(get_memoria)):
    return MemoriaCriadaSaida(id=memoria.salvar(usuario_id, corpo.texto, corpo.chave))


@app.get("/usuarios/{usuario_id}/memorias", response_model=list[MemoriaBuscaSaida])
def buscar_memorias(usuario_id: UsuarioIdPath,
                    consulta: str = Query(min_length=1, max_length=500),
                    k: int = Query(default=5, ge=1, le=20),
                    memoria=Depends(get_memoria)):
    return [MemoriaBuscaSaida(**m) for m in memoria.buscar(usuario_id, consulta, k)]


@app.delete("/usuarios/{usuario_id}/memorias/{memoria_id}", status_code=204)
def esquecer_uma(usuario_id: UsuarioIdPath, memoria_id: MemoriaIdPath,
                 memoria=Depends(get_memoria)):
    if not memoria.esquecer(usuario_id, memoria_id):
        raise MemoriaNaoEncontrada("Memória não encontrada para este usuário.")


@app.delete("/usuarios/{usuario_id}/memorias", response_model=ApagadasSaida)
def esquecer_usuario(usuario_id: UsuarioIdPath, conversador=Depends(get_conversador)):
    return ApagadasSaida(removidas=conversador.esquecer_usuario(usuario_id))