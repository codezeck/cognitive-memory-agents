import hmac
import os

from fastapi import Depends, Header

from src.api.erros import AcessoNegado, NaoAutenticado

from src.api.schemas import UsuarioIdPath

def _ler_tokens() -> dict[str, str]:
    """'tokenA:u001,tokenB:u002' -> {'tokenA': 'u001', 'tokenB': 'u002'}"""
    tokens = {}
    for item in os.getenv("API_TOKENS", "").split(","):
        token, _, usuario = item.strip().partition(":")
        if token and usuario:
            tokens[token] = usuario
    return tokens


def usuario_autenticado(authorization: str | None = Header(default=None)) -> str:
    """Devolve o usuario_id dono do token enviado no cabeçalho."""
    if not authorization or not authorization.startswith("Bearer "):
        raise NaoAutenticado("Informe o cabeçalho Authorization: Bearer <token>.")
    recebido = authorization[len("Bearer "):].strip()
    for token, usuario in _ler_tokens().items():
        if hmac.compare_digest(token, recebido):
            return usuario
    raise NaoAutenticado("Token inválido.")


def exigir_mesmo_usuario(usuario_id: str, autenticado: str) -> None:
    if usuario_id != autenticado:
        raise AcessoNegado("Você não tem acesso às memórias de outro usuário.")

    

def autorizar_usuario(usuario_id: UsuarioIdPath,
                      autenticado: str = Depends(usuario_autenticado)) -> None:
    """Para as rotas /usuarios/{usuario_id}/...: o token precisa ser desse usuário."""
    exigir_mesmo_usuario(usuario_id, autenticado)