"""Controle experimental: uma pergunta ao Ollama, sem agente ou memória."""
from __future__ import annotations

import os
import time

import httpx

VERSAO = 'comparativo-v3-ollama-direto-v1'


def executar_sem_memoria(caso, provedor, modelo, *, timeout=60):
    """Não reutiliza clientes, credenciais, estado ou política de abstenção da API."""
    if provedor.lower() != 'ollama':
        raise ValueError('O controle direto desta versão suporta somente Ollama.')
    from eval.historico_processo import timeout_positivo
    timeout = timeout_positivo(timeout)
    from eval import avaliar_comparativo as avaliador
    from eval.julgamento_respostas import julgar_resposta

    inicio = time.perf_counter()
    resposta = None
    erro = None
    chamada = None
    try:
        host = os.getenv('OLLAMA_HOST', 'http://127.0.0.1:11434').rstrip('/')
        with httpx.Client(timeout=httpx.Timeout(timeout, connect=min(10, timeout)), trust_env=False,
                          follow_redirects=False) as cliente:
            retorno = cliente.post(host + '/api/chat', json={
                'model': modelo, 'stream': False,
                'messages': [{'role': 'user', 'content': caso['mensagens'][-1]}],
            })
            retorno.raise_for_status()
            dados = retorno.json()
        if (not isinstance(dados, dict) or dados.get('done') is not True
                or dados.get('error') or not isinstance(dados.get('message'), dict)
                or dados['message'].get('role') != 'assistant'
                or not isinstance(dados['message'].get('content'), str)
                or not dados['message']['content'].strip()):
            raise ValueError('Resposta incompleta do provedor')
        resposta = dados['message']['content']
        def contagem(nome):
            valor = dados.get(nome)
            return valor if type(valor) is int and valor > 0 else None
        chamada = {'tokens_entrada': contagem('prompt_eval_count'),
                   'tokens_saida': contagem('eval_count'), 'origem_uso': 'provedor',
                   'chamadas_modelo_observadas': 1}
    except httpx.TimeoutException:
        erro = 'O Ollama não respondeu no prazo do controle direto; sem repetição ou fallback local. Consumo desconhecido.'
    except (httpx.HTTPError, httpx.InvalidURL):
        erro = 'Falha HTTP no controle direto do Ollama; sem repetição ou fallback local. Consumo desconhecido.'
    except (ValueError, TypeError, AttributeError):
        erro = 'Resposta inválida ou incompleta no controle direto do Ollama; consumo desconhecido.'

    julgamento = julgar_resposta(resposta, caso)
    etapas = (avaliador.tokens_tentativa(caso, 'sem_memoria', [chamada]) if chamada
              else avaliador.tokens_tentativa(caso, 'sem_memoria', []))
    # Nenhuma ingestão é feita neste controle, inclusive quando a pergunta falha.
    etapas['ingestao'] = {**avaliador.tokens_etapa([]), 'chamadas_previstas': 0,
                         'chamadas_observadas': 0}
    registro = {
        'id': caso['id'], 'categoria': caso['categoria'], 'cenario': 'sem_memoria',
        'via': 'ollama_direto', 'versao_metodo': VERSAO,
        'timeout_modelo_s': timeout,
        'provedor': 'ollama', 'modelo': modelo, 'repeticao': None,
        'passou': julgamento['passou'], 'julgamento': julgamento,
        'vazamento_esquecidos': avaliador.avaliar_vazamento_esquecidos(caso, julgamento),
        'protocolo_ok': julgamento['protocolo_ok'],
        'esperado': 'DESCONHECIDO' if caso['avaliacao']['tipo_resposta'] == 'abstencao' else caso['esperado'],
        'resposta': resposta, 'memorias_esperadas': [], 'memorias_usadas': [],
        'recuperacao_memoria_ok': None, 'recuperacao_equivalente_ok': None,
        'estado_regras_esperado': None, 'estado_regras_obtido': None, 'estado_regras_ok': None,
        'tempo_execucao_ms': round((time.perf_counter() - inicio) * 1000, 2),
        **etapas['sessao'], 'tokens_por_etapa': etapas,
        'latencia_api_total_ms': None, 'latencia_api_media_ms': None,
        'latencia_ollama_http_ms': round((time.perf_counter() - inicio) * 1000, 2),
        'preparacao': avaliador.preparacao_cenario('sem_memoria', caso),
        'parametros_geracao': 'padrões do modelo no Ollama; sem sobreposição pelo controle',
    }
    if erro:
        registro['erro'] = erro
    return registro
