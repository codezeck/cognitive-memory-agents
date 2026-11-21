"""Carregamento explícito do Ollama antes das tentativas, sem prompts de teste."""
from __future__ import annotations

import os
import time
from datetime import datetime, timezone

import httpx

from src.interface.protocolos import gravar_progresso


class FalhaPreparo(RuntimeError):
    def __init__(self, codigo, mensagem):
        super().__init__(mensagem)
        self.codigo = codigo


def preparar_modelo(modelo, progresso, *, previstos, unidade):
    """Não instala nem baixa pesos. O prazo maior é só para carregar o modelo."""
    inicio = time.monotonic()
    gravar_progresso(progresso, fase='Carregando o modelo no Ollama; os testes ainda não começaram',
                     concluidos=0, previstos=previstos, unidade=unidade)
    host = os.getenv('OLLAMA_HOST', 'http://127.0.0.1:11434').rstrip('/')
    try:
        with httpx.Client(timeout=httpx.Timeout(900, connect=10), trust_env=False) as cliente:
            tags = cliente.get(host + '/api/tags', timeout=10)
            tags.raise_for_status()
            dados = tags.json()
            instalado = next((m for m in dados.get('models', []) if m.get('name') == modelo), None)
            if instalado is None:
                raise FalhaPreparo('modelo_ausente', 'O modelo selecionado não está instalado. Conclua o preparo da demonstração antes de avaliar; nenhum peso foi baixado automaticamente.')
            resposta = cliente.post(host + '/api/generate', json={'model': modelo, 'prompt': '', 'stream': False})
            resposta.raise_for_status()
            carregamento = resposta.json()
            if carregamento.get('done') is not True or carregamento.get('error'):
                raise FalhaPreparo('carregamento_nao_confirmado', 'O Ollama respondeu, mas não confirmou o carregamento do modelo. Nenhuma tentativa do roteiro foi iniciada.')
    except httpx.TimeoutException as erro:
        raise FalhaPreparo('timeout_preparo', 'O Ollama não ficou pronto dentro do prazo de preparação (até 15 minutos). Confira recursos do Docker e disponibilidade do modelo. Nenhuma tentativa do roteiro foi iniciada.') from erro
    except httpx.HTTPError as erro:
        raise FalhaPreparo('ollama_indisponivel', 'Não foi possível preparar o Ollama. Confira o serviço e seus recursos; nenhuma tentativa do roteiro foi iniciada.') from erro
    except (ValueError, TypeError, AttributeError) as erro:
        raise FalhaPreparo('resposta_preparo_invalida', 'O Ollama retornou dados de preparação inválidos. Nenhuma tentativa do roteiro foi iniciada.') from erro
    return {'tipo': 'carregamento_sem_prompt_de_teste', 'modelo': modelo,
            'digest': instalado.get('digest'), 'concluido_em': datetime.now(timezone.utc).isoformat(),
            'duracao_segundos': round(time.monotonic() - inicio, 3),
            'prazo_segundos': 900, 'incluido_nos_tokens_dos_casos': False,
            'limite': 'Preparação separada; não mede o custo total do sistema nem garante ausência de falhas futuras.'}
