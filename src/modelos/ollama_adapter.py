
import ollama


class ErroModelo(RuntimeError):
    """Erro base para falhas na comunicação com o modelo."""


class ModeloIndisponivelError(ErroModelo):
    """O modelo não pôde ser consultado."""


class RespostaModeloVaziaError(ErroModelo):
    """O modelo não retornou conteúdo utilizável."""


class OllamaAdapter:
    """Integra o projeto ao Ollama seguindo o contrato comum."""

    def __init__(self, modelo: str):
        self.modelo = modelo

    def gerar_com_detalhes(
        self,
        mensagens: list[dict[str, str]],
        options: dict | None = None,
    ) -> dict:
        """Gera uma resposta e retorna também as métricas disponíveis."""

        try:
            resposta = ollama.chat(
                model=self.modelo,
                messages=mensagens,
                options=options,
            )
        except Exception as erro:
            raise ModeloIndisponivelError(
                f"Não foi possível consultar o modelo "
                f"'{self.modelo}' no Ollama. Verifique se o serviço "
                "está ativo e se o modelo está instalado."
            ) from erro

        try:
            texto = resposta.message.content or ""
        except (AttributeError, TypeError):
            texto = ""

        if not isinstance(texto, str) or not texto.strip():
            raise RespostaModeloVaziaError(
                f"O modelo '{self.modelo}' retornou uma resposta vazia."
            )

        return {
            "resposta": texto,
            "tokens_entrada": (
                getattr(resposta, "prompt_eval_count", 0) or 0
            ),
            "tokens_saida": (
                getattr(resposta, "eval_count", 0) or 0
            ),
        }

    def gerar(self, mensagens: list[dict[str, str]]) -> str:
        """Retorna apenas o texto gerado pelo modelo."""
        resultado = self.gerar_com_detalhes(mensagens)
        return resultado["resposta"]
