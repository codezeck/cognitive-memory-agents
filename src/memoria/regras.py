"""Baseline por regras: decide o que guardar, atualizar ou esquecer a partir
do texto de uma mensagem, sem usar IA.

Entrada: uma mensagem do usuário. Saída: lista de `Decisao`, na ordem em que
aparecem no texto. Só considera frases afirmativas em primeira pessoa; frases
interrogativas são ignoradas. As regras são deliberadamente simples e têm
falhas conhecidas (ver docs/falhas-conhecidas-regras.md).
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Callable

SALVAR = "salvar"
ESQUECER = "esquecer"
APAGAR_USUARIO = "apagar_usuario"


@dataclass(frozen=True)
class Decisao:
    acao: str
    chave: str | None = None  # terminada em ":" = prefixo (vale para várias chaves)
    valor: str | None = None
    texto: str | None = None  # texto canônico que vai para a memória
    negacao: bool = False  # esquecer só se o valor atual for igual a `valor`


def sem_acento(texto: str) -> str:
    """Minúsculas e sem acentos, mantendo o mesmo comprimento do original."""
    return "".join(unicodedata.normalize("NFD", c)[0] for c in texto).lower()


def normalizar(texto: str) -> str:
    return " ".join(sem_acento(texto).split())


# ---------------------------------------------------------------- blocos
_FIM = (
    r"(?=\s*(?:[.,;!?:\n]|\s+e\s+(?:agora\s+)?(?:moro|trabalho|tenho|sou|gosto|"
    r"pratico|torco|mudei|me\s+mudei|meu|minha|vou|faco)\b|\s+mas\b|\s+porque\b|"
    r"\s+pois\b|$))"
)
_V = r"(?P<v>[^.,;!?:\n]+?)" + _FIM
_NEG = r"(?<!nao\s)(?<!nunca\s)"
_NAO_LUGAR = (
    r"(?!(?:um|uma|casa|apto|apartamento|condominio|sitio|chacara|republica|"
    r"predio|rua|avenida|bairro)\b)"
)
_PROF = (
    r"professor|professora|enfermeiro|enfermeira|programador|programadora|"
    r"desenvolvedor|desenvolvedora|designer|engenheiro|engenheira|medico|medica|"
    r"advogado|advogada|analista|coordenador|coordenadora|diretor|diretora|"
    r"gerente|dentista|arquiteto|arquiteta|contador|contadora|motorista|"
    r"cozinheiro|cozinheira|psicologo|psicologa|jornalista|fotografo|fotografa|"
    r"vendedor|vendedora|pedreiro|eletricista|mecanico|mecanica|autonomo|"
    r"empresario|empresaria"
)
_PROF_V = r"(?P<v>(?:" + _PROF + r")(?:\s+[^.,;!?:\n]+?)??)" + _FIM
_ESP = (
    r"(?:cachorro|cachorra|cao|gato|gata|papagaio|coelho|coelha|hamster|peixe|"
    r"passaro|tartaruga|cavalo)"
)
_ESP_NORM = {"cachorra": "cachorro", "cao": "cachorro", "gata": "gato", "coelha": "coelho"}
_ESPORTE = (
    r"(?:natacao|corrida|musculacao|yoga|pilates|futebol|volei|basquete|tenis|"
    r"ciclismo|judo|karate|boxe|crossfit|caminhada|danca|surfe|escalada|"
    r"jiu-jitsu|muay thai|capoeira|ginastica)"
)
_CAT = r"(?:comida|prato|doce|bebida|cor|filme|livro|musica|banda|serie|animal)"
_MESES = (
    r"(?:janeiro|fevereiro|marco|abril|maio|junho|julho|agosto|setembro|outubro|"
    r"novembro|dezembro)"
)
_NUM = {"um": 1, "uma": 1, "dois": 2, "duas": 2, "tres": 3, "quatro": 4, "cinco": 5, "seis": 6}


def _val(m: re.Match, original: str, grupo: str = "v") -> str | None:
    v = original[m.start(grupo):m.end(grupo)].strip(" \t\"'«»“”")
    return v if v and len(v.split()) <= 6 else None


def _salvar(chave: str, modelo: str) -> Callable:
    def f(m, o):
        v = _val(m, o)
        return [Decisao(SALVAR, chave, v, modelo.format(v=v))] if v else []
    return f


def _negar(chave: str) -> Callable:
    def f(m, o):
        v = _val(m, o)
        return [Decisao(ESQUECER, chave, v, negacao=True)] if v else []
    return f


def _pet(m, o):
    v = _val(m, o)
    if not v:
        return []
    esp = _ESP_NORM.get(m.group("esp"), m.group("esp"))
    return [Decisao(SALVAR, f"pet:{esp}:{normalizar(v)}", v, f"Pet: {esp} chamado {v}.")]


def _filhos(m, o):
    n = m.group("n")
    qtd = _NUM[n] if n in _NUM else int(n)
    palavra = o[m.start("s"):m.end("s")].lower()
    return [Decisao(SALVAR, "filhos", str(qtd), f"Tem {qtd} {palavra}.")]


def _fav(m, o):
    v = _val(m, o)
    cat = m.group("cat")
    return [Decisao(SALVAR, f"favorito:{cat}", v, f"Favorito ({cat}): {v}.")] if v else []


def _gosto(m, o):
    v = _val(m, o)
    if not v or len(v.split()) > 4:
        return []
    return [Decisao(SALVAR, f"gosto:{normalizar(v)}", v, f"Gosta de {v}.")]


def _desgosto(m, o):
    v = _val(m, o)
    if not v or len(v.split()) > 4:
        return []
    return [Decisao(ESQUECER, f"gosto:{normalizar(v)}", v)]


_REGRAS: list[tuple[re.Pattern, Callable]] = []


def _regra(padrao: str, fn: Callable) -> None:
    _REGRAS.append((re.compile(padrao), fn))


# cidade
_regra(_NEG + r"\b(?:moro|vivo|resido)\s+(?:agora\s+|atualmente\s+|ainda\s+)?"
       r"(?:em|na|no|nos|nas)\s+" + _NAO_LUGAR + _V, _salvar("cidade", "Mora em {v}."))
_regra(r"\b(?:me\s+)?mudei\s+(?:de\s+(?:cidade|estado|pais)\s+)?(?:para|pra)\s+"
       r"(?:o\s+|a\s+)?" + _NAO_LUGAR + _V, _salvar("cidade", "Mora em {v}."))
_regra(r"\bnao\s+(?:moro|vivo)\s+(?:mais\s+)?(?:em|na|no|nos|nas)\s+" + _NAO_LUGAR + _V,
       _negar("cidade"))
# profissão
_regra(_NEG + r"\b(?:agora\s+)?trabalho\s+(?:agora\s+)?como\s+(?:um\s+|uma\s+|a\s+|o\s+)?" + _V,
       _salvar("profissao", "Profissão: {v}."))
_regra(r"\bnao\s+trabalho\s+mais\s+como\s+(?:um\s+|uma\s+|a\s+|o\s+)?" + _V, _negar("profissao"))
_regra(r"\bminha\s+profissao\s+e\s+(?:a\s+de\s+|de\s+)?" + _V, _salvar("profissao", "Profissão: {v}."))
_regra(_NEG + r"\b(?:agora\s+)?sou\s+(?:a\s+|o\s+)?" + _PROF_V, _salvar("profissao", "Profissão: {v}."))
_regra(r"\bvirei\s+(?:a\s+|o\s+)?" + _PROF_V, _salvar("profissao", "Profissão: {v}."))
_regra(r"\bfui\s+promovid[oa]\s+(?:a|para)\s+(?:o\s+|a\s+)?" + _V, _salvar("profissao", "Profissão: {v}."))
# nome
_regra(r"\bmeu\s+nome\s+(?:completo\s+)?e\s+" + _V, _salvar("nome", "Chama-se {v}."))
_regra(r"\bme\s+chamo\s+" + _V, _salvar("nome", "Chama-se {v}."))
_regra(r"\bpode\s+me\s+chamar\s+de\s+" + _V, _salvar("apelido", "Prefere ser chamado de {v}."))
# pets
_regra(r"\b(?:meu|minha)\s+(?P<esp>" + _ESP + r")\s+(?:se\s+chama|chama-se|chama|e\s+(?:o|a)|"
       r"tem\s+o\s+nome\s+de)\s+" + _V, _pet)
_regra(r"\badotei\s+(?:um|uma)\s+(?:(?:segundo|segunda|novo|nova|outro|outra)\s+)?(?P<esp>" + _ESP +
       r")(?:\s*,\s*(?:o\s+|a\s+)?|\s+chamad[oa]\s+(?:de\s+)?|\s+de\s+nome\s+)" + _V, _pet)
# esporte
_regra(_NEG + r"\b(?:pratico|faco)\s+(?:agora\s+)?(?:aulas\s+de\s+)?(?P<v>" + _ESPORTE +
       r"(?:\s+de\s+rua)?)\b", _salvar("esporte", "Pratica {v}."))
_regra(r"\bjogo\s+(?P<v>futebol|volei|basquete|tenis)\b", _salvar("esporte", "Pratica {v}."))
_regra(r"\btroquei\s+(?:a\s+|o\s+)?" + _ESPORTE + r"\s+(?:pela|pelo|por)\s+(?:a\s+|o\s+)?(?P<v>" +
       _ESPORTE + r")\b", _salvar("esporte", "Pratica {v}."))
_regra(r"\bnao\s+(?:pratico|faco)\s+mais\s+(?P<v>" + _ESPORTE + r")\b", _negar("esporte"))
# carro
_regra(r"\bmeu\s+carro\s+(?:agora\s+)?e\s+(?:um|uma)\s+" + _V, _salvar("carro", "Carro: {v}."))
_regra(_NEG + r"\b(?:agora\s+)?dirijo\s+(?:um|uma)\s+" + _V, _salvar("carro", "Carro: {v}."))
# filhos
_regra(_NEG + r"\b(?:agora\s+)?tenho\s+(?:agora\s+)?(?P<n>um|uma|dois|duas|tres|quatro|cinco|seis|\d+)"
       r"\s+(?P<s>filhos?|filhas?)\b", _filhos)
_regra(r"\bnao\s+tenho\s+(?:nenhum\s+|nenhuma\s+)?filh[oa]s?\b",
       lambda m, o: [Decisao(SALVAR, "filhos", "0", "Não tem filhos.")])
# time
_regra(_NEG + r"\btorco\s+(?:pelo|pela|pro|para\s+o|para\s+a|para)\s+" + _V, _salvar("time", "Torce para {v}."))
_regra(r"\bmeu\s+time\s+(?:do\s+coracao\s+)?e\s+(?:o\s+|a\s+)" + _V, _salvar("time", "Torce para {v}."))
_regra(r"\bnao\s+torco\s+mais\s+(?:pelo|pela|pro|para\s+o|para\s+a|para)\s+" + _V, _negar("time"))
# favoritos e gostos
_regra(r"\b(?:minha|meu)\s+(?P<cat>" + _CAT + r")\s+favorit[oa]\s+e\s+(?:o\s+|a\s+)?" + _V, _fav)
_regra(_NEG + r"\bgosto\s+(?:muito\s+)?de\s+(?:o\s+|a\s+)?" + _V, _gosto)
_regra(r"\bnao\s+gosto\s+mais\s+de\s+(?:o\s+|a\s+)?" + _V, _desgosto)
# viagem
_regra(r"\b(?:vou|quero|pretendo|planejo)\s+viajar\s+(?:para|pra)\s+(?:o\s+|a\s+)?" + _V,
       _salvar("viagem", "Planeja viajar para {v}."))
_regra(r"\bvou\s+(?:para|pra)\s+(?:o\s+|a\s+)?(?P<v>[^.,;!?:\n]+?\s+em\s+" + _MESES + r")\b",
       _salvar("viagem", "Planeja viajar para {v}."))

# ------------------------------------------------------------ esquecimento
_FORGET = (
    r"(?:esqueca|esquece|esquecer|apague|apaga|apagar|remova|remove|remover|"
    r"delete|deleta|deletar|exclua|excluir|elimine)"
)
_APAGAR_TUDO = re.compile(
    _NEG + r"\b" + _FORGET + r"\s+(?:(?:de\s+)?tudo\b(?!\s+(?:o\s+)?que\s+(?:eu\s+)?"
    r"(?:te\s+|lhe\s+)?(?:disse|falei|contei|escrevi)\s+sobre|\s+sobre\s+(?!mim\b))"
    r"|todos\s+os\s+meus\s+dados|todas\s+as\s+minhas\s+(?:informacoes|memorias)|meus\s+dados)"
)
_TOPICOS = {
    "cidade": "cidade", "endereco": "cidade", "carro": "carro",
    "profissao": "profissao", "trabalho": "profissao", "emprego": "profissao",
    "time": "time", "esporte": "esporte", "filho": "filhos", "filhos": "filhos",
    "filha": "filhos", "filhas": "filhos", "nome": "nome", "apelido": "apelido",
    "viagem": "viagem", "pet": "pet:", "pets": "pet:", "animal de estimacao": "pet:",
    "cachorro": "pet:cachorro:", "cachorros": "pet:cachorro:",
    "gato": "pet:gato:", "gatos": "pet:gato:",
    "papagaio": "pet:papagaio:", "papagaios": "pet:papagaio:",
    "comida": "favorito:comida", "filme": "favorito:filme", "cor": "favorito:cor",
    "livro": "favorito:livro", "musica": "favorito:musica", "banda": "favorito:banda",
}
_VERBO_ESQ = re.compile(_NEG + r"\b" + _FORGET + r"\b(?P<cauda>[^.!?;\n]*)")
_TOPICO = re.compile(
    r"\b(" + "|".join(sorted(map(re.escape, _TOPICOS), key=len, reverse=True)) + r")\b"
)


def _esquecimentos(t: str) -> list[tuple[int, Decisao]]:
    achados: list[tuple[int, Decisao]] = []
    inicios_apagar = set()
    for m in _APAGAR_TUDO.finditer(t):
        inicios_apagar.add(m.start())
        achados.append((m.start(), Decisao(APAGAR_USUARIO)))
    for m in _VERBO_ESQ.finditer(t):
        if m.start() in inicios_apagar:
            continue
        vistas = set()
        for tm in _TOPICO.finditer(m.group("cauda")):
            chave = _TOPICOS[tm.group(1)]
            if chave not in vistas:
                vistas.add(chave)
                achados.append((m.start(), Decisao(ESQUECER, chave)))
    return achados


def extrair(mensagem: str) -> list[Decisao]:
    original = mensagem.strip()
    if not original:
        return []
    t = sem_acento(original)
    # frases interrogativas são ignoradas (mantém os índices)
    t = re.sub(r"[^.!?\n]*\?", lambda m: " " * len(m.group()), t)
    if not t.strip():
        return []

    achados: list[tuple[int, Decisao]] = []
    for padrao, fn in _REGRAS:
        for m in padrao.finditer(t):
            achados.extend((m.start(), d) for d in fn(m, original))
    achados.extend(_esquecimentos(t))
    achados.sort(key=lambda x: x[0])

    vistos, saida = set(), []
    for _, d in achados:
        chave = (d.acao, d.chave, normalizar(d.valor or ""))
        if chave not in vistos:
            vistos.add(chave)
            saida.append(d)
    return saida
