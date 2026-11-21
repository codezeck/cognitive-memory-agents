"""Análise adicional da P6; P4 e relatórios originais permanecem intactos."""
from __future__ import annotations

from copy import deepcopy
import re

from eval import julgamento_respostas as p4

VERSAO = 'p6-conteudo-v2'


def _pergunta(caso):
    pergunta = caso.get('pergunta', '')
    return p4.normalizar(pergunta) if isinstance(pergunta, str) else ''


def _padroes(atributo, valor, pergunta):
    base = p4._padrao_factual(atributo, valor)
    if atributo == 'carro':
        base = base.replace('(?:um )?', '(?:(?:um|o|a) )?')
    elif atributo == 'filhos':
        base = base.replace('(?:tenho|tem) ', '(?:tenho|tem)(?: (?:agora|atualmente))? ')
    elif atributo == 'profissao':
        base = base.replace('(?:sou|e) ', '(?:sou|e) (?:(?:um|uma) )?')
    elif atributo == 'time':
        base = base.replace('(?:pelo|pela)', '(?:pelo|pela|para o|para a)')
    elif atributo == 'pet':
        base = base.replace('(?:meu|seu)', '(?:meu|seu|minha|sua)')
        especies = [s for s in ('cachorro', 'cachorra', 'gato', 'gata') if re.search(r'\b'+s+r'\b', pergunta)]
        if especies:
            base = base.replace('(?:pet|animal de estimacao)', '(?:pet|animal de estimacao|'+'|'.join(especies)+')')
    elif atributo == 'quantidade_pets':
        especies = [s for s in ('gatos', 'cachorros', 'gatas', 'cachorras') if re.search(r'\b'+s+r'\b', pergunta)]
        if especies:
            base = base.replace('(?:pets|animais de estimacao)', '(?:pets|animais de estimacao|'+'|'.join(especies)+')')
    padroes = [base]
    if atributo == 'cidade':
        padroes += [rf'(?:hoje|atualmente|agora),? {base}',
                    rf'(?:a )?(?:sua|minha) casa (?:atual |atualmente )?e em {valor}']
    if atributo == 'profissao':
        padroes.append(rf'(?:meu|seu) trabalho(?: atual)? e (?:de )?{valor}')
    if atributo == 'viagem':
        planejamento = rf'(?:(?:eu|voce) )?(?:estou|esta) planejando (?:uma )?viagem para {valor}'
        padroes.append(planejamento)
        meses = 'janeiro fevereiro marco abril maio junho julho agosto setembro outubro novembro dezembro'.split()
        for mes in meses:
            if re.search(r'\bem '+mes+r'\b', pergunta):
                padroes += [rf'em {mes},? {p}' for p in (base, planejamento)]
                padroes += [rf'{p} em {mes}' for p in (base, planejamento)]
    return [rf'(?:(?:sua memoria|a memoria) registra que )?{p}' for p in padroes]


def _abstencao(texto, atributo):
    texto = re.sub(r'^(?:desculpe|sinto muito)[,:]?\s*(?:mas )?', '', texto).rstrip('.!')
    original = p4._abstencao(texto, atributo)
    if original['valor'] is True:
        return original
    topicos = {
        'carro': r'(?:(?:o|qual) carro (?:que )?voce dirige(?: agora|atualmente)?)',
        'time': r'o time (?:que|para o qual|pelo qual) voce torce',
        'profissao': r'(?:a )?(?:sua profissao|seu cargo|sua posicao atual)',
        'hobby': r'(?:o )?seu hobby',
        'quantidade_pets': r'(?:a quantidade de|o numero de) (?:seus )?(?:pets|gatos|cachorros)',
    }
    topico = topicos.get(atributo)
    if topico and re.fullmatch(rf'nao tenho informacoes(?: atualizadas)? sobre {topico}', texto):
        return p4._criterio(True, 'abstencao_sem_fato_adicional')
    if atributo == 'time' and re.fullmatch(r'voce nao disse (?:qual|para qual) time (?:voce )?torce', texto):
        return p4._criterio(True, 'ausencia_do_fato_declarada')
    return original


def _recusa_factual(texto, atributo, aceitos, antigos):
    if any(p4._ocorre(v, texto) for v in [*aceitos, *antigos]):
        return False
    if _abstencao(texto, atributo)['valor'] is True:
        return True
    if atributo == 'profissao' and re.fullmatch(
        r'como voce nao forneceu (?:a )?(?:sua posicao atual|seu cargo|sua profissao), '
        r'nao posso fornecer uma informacao precisa[.!]?', texto,
    ):
        return True
    if atributo in ('quantidade_pets', 'filhos') and re.fullmatch(
        r'como voce nao forneceu a quantidade(?: especifica)? (?:dos seus|de seus|de) '
        r'(?:pets|animais de estimacao|gatos|cachorros|filhos), '
        r'nao posso fornecer (?:um numero exato|uma quantidade precisa)[.!]?', texto,
    ):
        return True
    return atributo == 'hobby' and bool(re.fullmatch(
        r'(?:como )?sou (?:uma inteligencia artificial|um modelo de linguagem|um assistente virtual)'
        r'[, ]+(?:e )?nao (?:tenho|possuo) hobbies(?: como voce)?'
        r'(?:\. eu sou aqui para responder suas perguntas e fornecer informacoes)?[.!]?', texto,
    ))


def julgar_resposta_p6(resposta, caso, *, trajetoria_integra=True):
    resultado = deepcopy(p4.julgar_resposta(resposta, caso))
    resultado['versao'] = VERSAO
    if trajetoria_integra is not True:
        for chave in p4.CRITERIOS:
            if resultado[chave]['status'] != 'nao_aplicavel':
                resultado[chave] = p4._criterio(motivo='trajetoria_incompleta')
    elif isinstance(resposta, str) and len(resposta) <= 16000:
        texto = p4.normalizar(resposta)
        a = caso.get('avaliacao')
        if isinstance(a, dict) and isinstance(a.get('atributo'), str) and a['atributo'] in p4.ATRIBUTOS:
            atributo, modo = a['atributo'], a.get('tipo_resposta')
            if modo == 'abstencao':
                resultado['abstencao_correta'] = _abstencao(texto, atributo)
            elif modo == 'factual':
                esperado, aliases, antigos = caso.get('esperado'), a.get('aliases_aceitos', []), a.get('valores_antigos', [])
                if isinstance(esperado, str) and esperado.strip() and p4._lista_textos(aliases) and p4._lista_textos(antigos):
                    aceitos = [esperado, *aliases]
                    valor = p4._alternativas(aceitos)
                    if any(re.fullmatch(p, texto.rstrip('.!')) for p in _padroes(atributo, valor, _pergunta(caso))):
                        resultado['acerto_factual'] = p4._criterio(True, 'afirmacao_contextual_reconhecida')
                    elif _recusa_factual(texto, atributo, aceitos, antigos):
                        resultado['acerto_factual'] = p4._criterio(False, 'abstencao_indevida_fato_esperado')
    primario = 'acerto_factual' if resultado['tipo_resposta'] == 'factual' else 'abstencao_correta'
    resultado['passou'] = resultado[primario]['valor'] is True and resultado['sem_informacao_proibida']['valor'] is True
    resultado['protocolo_ok'] = resultado['passou'] and resultado['formato_ok']['valor'] is True
    resultado['revisao_necessaria'] = any(resultado[c]['status'] == 'nao_verificado' for c in p4.CRITERIOS)
    return resultado
