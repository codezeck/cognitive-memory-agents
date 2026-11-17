"""Suporte conservador para consultas pessoais diretas em portugues.

Nao extrai nem grava memorias. Reconhece consultas diretas, nao toda a lingua;
fora dessa gramatica o agente continua usando o percurso normal de geracao.
"""
from dataclasses import dataclass
import re
import unicodedata


def _normalizar(texto: str) -> str:
    texto = unicodedata.normalize('NFKD', texto.lower())
    return ''.join(c for c in texto if not unicodedata.combining(c))


@dataclass(frozen=True)
class ConsultaSemSuporte:
    atributos: tuple[str, ...]
    restante: str


_CIDADE = re.compile(
    r'^(?:(?:voce\s+)?(?:sabe|lembra)\s+)?'
    r'(?:onde\s+(?:e\s+que\s+)?(?:eu\s+)?(?:moro|vivo|resido)'
    r'|(?:em\s+)?(?:que|qual)\s+cidade\s+(?:eu\s+)?(?:moro|vivo|resido))\b'
)
_POSSE = re.compile(
    r'^(?:(?:voce\s+)?(?:sabe|lembra)\s+)?'
    r'(?:qual|quais|quanto|quantos|quantas)\s+'
    r'(?:(?:e|sao|era|eram)\s+)?(?:o\s+|a\s+|os\s+|as\s+)?'
    r'(?:meu|minha|meus|minhas)\s+([\w -]+?)[?!.]*$'
)
_CONSELHO = re.compile(r'\b(?:melhor|ideal|escolher|escolha|devo|posso|recomenda|opcao)\b')


def _atributo(trecho: str) -> str | None:
    texto = _normalizar(trecho).strip()
    if _CONSELHO.search(texto):
        return None
    if _CIDADE.search(texto):
        return 'cidade'
    if re.search(r'\bcomo\s+(?:eu\s+)?me\s+chamo\b', texto):
        return 'nome'
    match = _POSSE.match(texto)
    if not match:
        return None
    atributo = match[1].strip()
    if atributo in {'cidade', 'cidade de residencia', 'cidade atual'}:
        return 'cidade'
    if atributo == 'nome completo':
        return 'nome'
    return atributo


def _afirma_suporte(texto: str, atributo: str, *, memoria: bool) -> bool:
    atributo_literal = atributo
    atributo = re.escape(atributo)
    # Suporte explicito do usuario: perguntas, hipoteses e negacoes nao sao
    # declaracoes positivas do valor. Respostas do assistente nao chegam aqui.
    ligacao = r'(?:e|sao|se chama|chama-se)'
    generico = rf'(?:o |a |os |as )?(?:meu|minha|meus|minhas)\s+{atributo}\s+{ligacao}\s+\S'
    padroes = [generico]
    if atributo == 'cidade':
        sujeito = r'(?:(?:o usuario|o interlocutor)\s+)?' if memoria else r'(?:eu\s+)?'
        verbo = r'(?:mora|vive|reside|moro|vivo|resido)' if memoria else r'(?:moro|vivo|resido)'
        padroes.append(sujeito + verbo + r'\s+(?:(?:agora|atualmente)\s+)?(?:em|na|no|nas|nos)\s+\S')
        padroes.append(r'(?:eu\s+)?(?:me\s+)?mudei\s+(?:de cidade\s+)?(?:para|pra)\s+\S')
    elif atributo == 'nome':
        padroes.append(r'(?:eu\s+)?me\s+chamo\s+\S')
        if memoria:
            padroes.append(r'chama-se\s+\S')
    elif atributo == 'profissao':
        padroes.append(r'(?:eu\s+)?trabalho\s+como\s+\S')
    if memoria:
        padroes.extend([rf'{atributo}\s*:\s*\S',
                        rf'(?:o |a )?{atributo}(?: do usuario)?\s+{ligacao}\s+\S'])
        # Formas canonicas ja produzidas pelas regras existentes, sem muda-las.
        canonicos = {
            'esporte': r'pratica\s+\S', 'time': r'torce para\s+\S',
            'apelido': r'prefere ser chamado de\s+\S',
            'viagem': r'planeja viajar para\s+\S',
            'filhos': r'(?:tem\s+\d+\s+filh[oa]s?|nao tem filhos)\b',
        }
        if atributo in canonicos:
            padroes.append(canonicos[atributo])
        favorito = re.fullmatch(r'(\w+) favorit[oa]', atributo_literal)
        if favorito:
            padroes.append(r'favorito\s*\(' + favorito[1] + r'\)\s*:\s*\S')
    for frase in re.split(r'(?<=[.!?;])\s*|\n+', _normalizar(texto)):
        frase = frase.strip()
        if '?' in frase or re.match(r'(?:talvez|suponha|imagine|se)\b', frase):
            continue
        frase = re.sub(r'^(?:agora|atualmente)\s+', '', frase)
        if any(re.match(padrao, frase) for padrao in padroes):
            return True
    return False


def consultar_suporte(mensagem: str, historico: list[dict], memorias: list | None
                      ) -> ConsultaSemSuporte:
    fontes_usuario = [m['content'] for m in historico if m['role'] == 'user'] + [mensagem]
    fontes_memoria = []
    for memoria in memorias or []:
        if isinstance(memoria, str):
            fontes_memoria.append(memoria)
        elif isinstance(memoria, dict):
            fontes_memoria.append(str(memoria.get('texto') or memoria.get('content') or ''))
    desconhecidos, restantes = [], []
    for trecho in re.split(r'(?<=[.!?])\s*|\n+', mensagem):
        atributo = _atributo(trecho)
        if atributo and not (
            any(_afirma_suporte(f, atributo, memoria=False) for f in fontes_usuario)
            or any(_afirma_suporte(f, atributo, memoria=True) for f in fontes_memoria)
        ):
            desconhecidos.append(atributo)
        else:
            restantes.append(trecho)
    # Instrucoes de formato nao sao outra pergunta. Uma parte geral real deve
    # continuar no LLM em vez de ser bloqueada junto com o dado pessoal.
    restante = ' '.join(restantes).strip()
    tem_outra_pergunta = '?' in restante or re.search(
        r'\b(?:explique|resuma|calcule|traduza|sugira|recomende)\b', _normalizar(restante))
    return ConsultaSemSuporte(tuple(dict.fromkeys(desconhecidos)),
                             restante if tem_outra_pergunta else '')
