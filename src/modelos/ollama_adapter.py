
import ollama


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
        resposta = ollama.chat(
            model=self.modelo,
            messages=mensagens,
            options=options,
        )

        return {
            "resposta": resposta.message.content or "",
            "tokens_entrada": getattr(resposta, "prompt_eval_count", 0) or 0,
            "tokens_saida": getattr(resposta, "eval_count", 0) or 0,
        }

    def gerar(self, mensagens: list[dict[str, str]]) -> str:
        """Retorna apenas o texto gerado pelo modelo."""
        resultado = self.gerar_com_detalhes(mensagens)
        return resultado["resposta"]
