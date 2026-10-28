import os
from functools import lru_cache

from fastapi import Depends

from src.api.catalogo import Catalogo
from src.api.config import Configuracao, carregar_configuracao
from src.api.servico import Conversador


@lru_cache
def get_config() -> Configuracao:
    return carregar_configuracao()


def get_catalogo(config: Configuracao = Depends(get_config)) -> Catalogo:
    return Catalogo(config)


@lru_cache
def get_memoria():
    from src.armazenamento.repositorio import MemoriaSQLite
    return MemoriaSQLite()


@lru_cache
def get_gerenciador(memoria=Depends(get_memoria)):
    from src.memoria.gerenciador import GerenciadorMemoria
    return GerenciadorMemoria(memoria)


@lru_cache
def get_agente():
    if os.getenv("USAR_FALSOS") == "1":
        from src.api.falsos import AgenteFalso
        return AgenteFalso()
    from src.api.agente_local import AgenteLocal
    return AgenteLocal()


def get_conversador(
    agente=Depends(get_agente),
    memoria=Depends(get_memoria),
    gerenciador=Depends(get_gerenciador),
) -> Conversador:
    return Conversador(agente, memoria, gerenciador=gerenciador)