"""Roteiros existentes e validação de conjuntos próprios antes do modelo."""
from __future__ import annotations

import json
import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
DATASET_V3 = Path('eval/dataset_validacao_v3_20261118.json')
LIMITE_BYTES = 128 * 1024
NOMES = {'comparativo_v3': 'Comparativo sintético v3', 'p6': 'P6 — 20 sessões por cenário'}


def validar(protocolo, repeticoes):
    if protocolo not in NOMES or type(repeticoes) is not int or repeticoes not in (1, 3):
        raise ValueError('Escolha um protocolo existente e uma ou três repetições.')
    if protocolo == 'p6' and repeticoes != 1:
        raise ValueError('P6 usa uma rodada integral de 20 sessões por cenário; não três repetições.')


def validar_casos(casos):
    from eval.avaliar_comparativo import validar_dataset_p4
    if not isinstance(casos, list) or not 1 <= len(casos) <= 20:
        raise ValueError('O conjunto próprio deve ser uma lista JSON com 1 a 20 casos.')
    if len(json.dumps(casos, ensure_ascii=False, allow_nan=False).encode('utf-8')) > LIMITE_BYTES:
        raise ValueError('O conjunto próprio excede 128 KB.')
    permitidos = {'id', 'categoria', 'descricao', 'mensagens', 'memorias', 'esperado',
                  'estado_regras_esperado', 'informacoes_esquecidas', 'avaliacao'}
    for i, caso in enumerate(casos, 1):
        if not isinstance(caso, dict) or caso.keys() - permitidos:
            raise ValueError(f'Caso {i}: use somente os campos do modelo JSON; caminhos, comandos e URLs de execução não são aceitos.')
        if not isinstance(caso.get('id'), str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,64}', caso['id']):
            raise ValueError(f'Caso {i}: ID exige 1 a 64 letras, números, _ ou -.')
        mensagens = caso.get('mensagens')
        if (not isinstance(mensagens, list) or not 2 <= len(mensagens) <= 16
                or any(not isinstance(m, str) or not m.strip() or len(m) > 2000 for m in mensagens)):
            raise ValueError(f'Caso {i}: use 2 a 16 mensagens não vazias, até 2000 caracteres cada; a última é a pergunta.')
        for campo in ('memorias', 'informacoes_esquecidas'):
            valores = caso.get(campo)
            if (not isinstance(valores, list) or len(valores) > 32
                    or any(not isinstance(v, str) or not v.strip() or len(v) > 2000 for v in valores)):
                raise ValueError(f'Caso {i}: {campo} deve ser lista de até 32 textos não vazios.')
        if not isinstance(caso.get('estado_regras_esperado'), dict):
            raise ValueError(f'Caso {i}: estado_regras_esperado deve ser objeto (pode ser vazio).')
        if any(not isinstance(k, str) or not k.strip() or len(k) > 100
               or not isinstance(v, str) or not v.strip() or len(v) > 500
               for k, v in caso['estado_regras_esperado'].items()):
            raise ValueError(f'Caso {i}: estado esperado deve mapear chaves textuais para valores textuais não vazios.')
        esperado = caso.get('esperado')
        if not ((isinstance(esperado, str) and 0 < len(esperado) <= 2000)
                or (isinstance(esperado, list) and 0 < len(esperado) <= 32
                    and all(isinstance(v, str) and v.strip() and len(v) <= 2000 for v in esperado))):
            raise ValueError(f'Caso {i}: esperado exige texto ou lista de textos válidos de até 2000 caracteres.')
        for campo in ('categoria', 'descricao'):
            if not isinstance(caso.get(campo), str) or not caso[campo].strip() or len(caso[campo]) > 500:
                raise ValueError(f'Caso {i}: {campo} deve ser texto não vazio de até 500 caracteres.')
        anotacao = caso.get('avaliacao')
        permitidos_avaliacao = {'tipo_resposta', 'atributo', 'aliases_aceitos', 'valores_antigos',
                               'informacoes_proibidas', 'aliases_proibidos'}
        if not isinstance(anotacao, dict) or anotacao.keys() - permitidos_avaliacao:
            raise ValueError(f'Caso {i}: avaliacao deve usar somente os campos P4 do exemplo.')
        for campo in ('aliases_aceitos', 'valores_antigos', 'informacoes_proibidas'):
            valores = anotacao.get(campo, [])
            if (not isinstance(valores, list) or len(valores) > 32
                    or any(not isinstance(v, str) or not v.strip() or len(v) > 500 for v in valores)):
                raise ValueError(f'Caso {i}: {campo} exige lista de até 32 textos não vazios de até 500 caracteres.')
    validar_dataset_p4(casos)
    return casos


def fonte_v3():
    return json.loads((RAIZ / DATASET_V3).read_text(encoding='utf-8'))


def roteiros():
    casos = fonte_v3()
    dados = json.loads((RAIZ / 'eval/memoria/sessoes.json').read_text(encoding='utf-8'))
    return [
        {'id': 'comparativo_v3', 'nome': NOMES['comparativo_v3'],
         'descricao': '16 casos independentes; quatro cenários: sem memória (Ollama direto, somente pergunta final), histórico completo, memória pré-carregada e memória automática.',
         'conferencia': '1 repetição: 64 tentativas. É menor que a bateria completa, mas ainda pode levar vários minutos.',
         'completa': '3 repetições: 192 tentativas do mesmo conjunto v3. Não são dois datasets diferentes.',
         'objetivos': ['Comparar tokens nos mesmos pares com medição completa.',
                       'Conferir recuperação, atualização, abstenção e esquecimento conforme P4/P5.',
                       'Mostrar controles sem memória e pré-carregado.'],
         'limites': 'Não mede reinício nem exclusão física no SQLite/RAM. Dados sintéticos conhecidos e julgador de cobertura limitada.',
         'questoes': [{'id': c['id'], 'categoria': c['categoria'], 'mensagens': c['mensagens'],
                       'pergunta': c['mensagens'][-1]} for c in casos]},
        {'id': 'p6', 'nome': NOMES['p6'],
         'descricao': '4 usuários × 5 sessões × 2 cenários: 20 sessões por cenário, 40 no total e 42 respostas previstas.',
         'conferencia': 'A P6 preserva o roteiro integral; não existe P6 abreviada nesta tela.',
         'completa': 'Uma rodada integral com checkpoints de reinício/exclusão. Pode demorar bastante.',
         'objetivos': ['Medir continuidade e tokens de ingestão/perguntas em 20 pares de sessões.',
                       'Conferir respostas atualizadas, isolamento e esquecimento com anotações P4/P5 existentes.',
                       'Observar persistência por reinício e exclusão no SQLite e RAM da API dedicada.'],
         'limites': 'Só a API temporária é reiniciada, preservando chat e credenciais. Observação literal não certifica todas as formas de resíduo. Revisão humana continua separada.',
         'questoes': [{'id': f"{u['usuario_id']}/s{q['apos_sessao']}/pergunta{i}",
                       'usuario': u['usuario_id'], 'sessao': q['apos_sessao'], 'pergunta': q['pergunta']}
                      for u in dados['usuarios'] for i, q in enumerate(u['perguntas'], 1)],
         'sessoes': [{'usuario': u['usuario_id'], **s} for u in dados['usuarios'] for s in u['sessoes']]},
    ]


def gravar_progresso(caminho, **campos):
    if caminho is None:
        return
    caminho = Path(caminho)
    temporario = caminho.with_suffix('.tmp')
    temporario.write_text(json.dumps(campos, ensure_ascii=False, allow_nan=False), encoding='utf-8')
    temporario.replace(caminho)
