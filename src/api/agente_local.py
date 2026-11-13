import inspect

import httpx
import ollama

from src import agent as agente_mod
from src.api.config import carregar_configuracao
from src.api.erros import (
    ModeloNaoPermitido,
    ProvedorIndisponivel,
    ProvedorNaoConfigurado,
    ProvedorTimeout,
)
from src.api.servico import ResultadoAgente
from src.modelos.base import RespostaModeloVaziaError
from src.modelos.ollama_adapter import (
    ModeloIndisponivelError,
    OllamaAdapter,
)
from src.modelos.openai_adapter import OpenAIAdapter


class AgenteLocal:
    """Liga a API aos adaptadores de modelos disponíveis."""

    def __init__(self):
        self._adaptadores: dict[tuple[str, str], object] = {}

    def _adaptador(self, provedor: str, modelo: str):
        # A allowlist é responsabilidade do catálogo da API. Aqui validamos
        # também os chamadores locais do avaliador, antes de criar um cliente.
        if not isinstance(provedor, str) or provedor not in {"ollama", "openai"}:
            raise ModeloNaoPermitido("O provedor selecionado ainda não tem adaptador.")
        if not isinstance(modelo, str) or not modelo.strip() or modelo != modelo.strip():
            raise ModeloNaoPermitido("Informe um identificador de modelo não vazio, sem espaços externos.")
        chave = (provedor, modelo)

        if chave in self._adaptadores:
            return self._adaptadores[chave]

        if provedor == "ollama":
            adaptador = OllamaAdapter(modelo)

        elif provedor == "openai":
            config = carregar_configuracao()
            api_key = config.chave_de("openai")

            if not api_key:
                raise ProvedorNaoConfigurado(
                    "O provedor 'openai' não está configurado neste servidor."
                )

            adaptador = OpenAIAdapter(modelo, api_key)

        self._adaptadores[chave] = adaptador
        return adaptador

    def responder(
        self,
        usuario_id: str,
        mensagem: str,
        memorias: list,
        selecao,
    ) -> ResultadoAgente:
        parametros = inspect.signature(agente_mod.responder).parameters
        adaptador = self._adaptador(selecao.provedor, selecao.modelo)
        extras = {}

        if "adaptador" in parametros:
            extras["adaptador"] = adaptador
        elif "modelo" in parametros:
            extras["modelo"] = adaptador
        elif (
            selecao.provedor != "ollama"
            or selecao.modelo != agente_mod.MODEL
        ):
            raise ModeloNaoPermitido(
                "O agente atual não permite selecionar esse provedor ou modelo."
            )

        if "retornar_detalhes" in parametros:
            extras["retornar_detalhes"] = True

        try:
            texto = agente_mod.responder(
                mensagem=mensagem,
                usuario_id=usuario_id,
                memorias=memorias,
                **extras,
            )
        except (ProvedorTimeout, ProvedorIndisponivel):
            raise
        except RespostaModeloVaziaError as exc:
            # Reutiliza o contrato 503 existente, sem alterar endpoints.
            # Nunca devolve conteúdo ou detalhes do erro do provedor ao cliente.
            raise ProvedorIndisponivel(
                "O provedor não retornou uma resposta válida."
            ) from exc
        except ModeloIndisponivelError as exc:
            causa = exc.__cause__

            if isinstance(causa, (httpx.TimeoutException, TimeoutError)):
                raise ProvedorTimeout(
                    "O modelo demorou demais para responder."
                ) from exc

            raise ProvedorIndisponivel(
                "Não foi possível consultar o modelo no Ollama."
            ) from exc
        except (httpx.TimeoutException, TimeoutError) as exc:
            raise ProvedorTimeout(
                "O modelo demorou demais para responder."
            ) from exc
        except (ConnectionError, httpx.ConnectError) as exc:
            raise ProvedorIndisponivel(
                "Não foi possível conectar ao Ollama."
            ) from exc
        except ollama.ResponseError as exc:
            if exc.status_code == 404:
                raise ProvedorIndisponivel(
                    f"O modelo '{selecao.modelo}' não está instalado no Ollama. "
                    f"Rode: ollama pull {selecao.modelo}"
                ) from exc

            raise ProvedorIndisponivel(
                "O Ollama devolveu um erro."
            ) from exc

        if isinstance(texto, dict):
            return ResultadoAgente(
                resposta=texto.get("resposta", ""),
                tokens_entrada=texto.get("tokens_entrada"),
                tokens_saida=texto.get("tokens_saida"),
            )

        return ResultadoAgente(resposta=texto)

    def nova_sessao(self, usuario_id: str) -> None:
        agente_mod.limpar_historico(usuario_id)
