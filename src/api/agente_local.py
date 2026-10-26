import inspect

import httpx
import ollama

from src import agent as agente_mod
from src.api.erros import (ModeloNaoPermitido, ProvedorIndisponivel,
                           ProvedorTimeout)
from src.api.servico import ResultadoAgente
from src.modelos.ollama_adapter import OllamaAdapter


class AgenteLocal:
    """Liga a API ao agente do Ezequiel (src/agent.py)."""

    def __init__(self):
        parametros = inspect.signature(agente_mod.responder).parameters
        # Hoje o agent.py não aceita escolher o modelo; se o Ezequiel adicionar
        # o parâmetro "modelo", esta classe passa a usá-lo sozinha.
        self._aceita_modelo = "modelo" in parametros
        self._adaptadores: dict[str, OllamaAdapter] = {}

    def _adaptador(self, nome: str) -> OllamaAdapter:
        if nome not in self._adaptadores:
            self._adaptadores[nome] = OllamaAdapter(nome)
        return self._adaptadores[nome]

    def responder(self, usuario_id: str, mensagem: str, memorias: list,
                  selecao) -> ResultadoAgente:
        if selecao.provedor != "ollama":
            raise ModeloNaoPermitido(
                f"O provedor '{selecao.provedor}' ainda não tem adaptador.")

        extras = {}
        if self._aceita_modelo:
            extras["modelo"] = self._adaptador(selecao.modelo)
        elif selecao.modelo != agente_mod.MODEL:
            raise ModeloNaoPermitido(
                f"O agente atual só usa o modelo {agente_mod.MODEL}.")

        try:
            texto = agente_mod.responder(
                mensagem=mensagem, usuario_id=usuario_id,
                memorias=memorias, **extras)
        except (httpx.TimeoutException, TimeoutError) as exc:
            raise ProvedorTimeout("O modelo demorou demais para responder.") from exc
        except (ConnectionError, httpx.ConnectError) as exc:
            raise ProvedorIndisponivel(
                "Não consegui conectar ao Ollama. Ele está aberto?") from exc
        except ollama.ResponseError as exc:
            if exc.status_code == 404:
                raise ProvedorIndisponivel(
                    f"O modelo '{selecao.modelo}' não está instalado no Ollama. "
                    f"Rode: ollama pull {selecao.modelo}") from exc
            raise ProvedorIndisponivel("O Ollama devolveu um erro.") from exc

        return ResultadoAgente(resposta=texto)

    def nova_sessao(self, usuario_id: str) -> None:
        agente_mod.limpar_historico(usuario_id)