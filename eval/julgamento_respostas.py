"""Julgador P4: regras limitadas e explícitas, sem LLM ou acesso à aplicação."""

import re
import unicodedata

VERSAO = "p4-v2"
CRITERIOS = ("acerto_factual", "sem_informacao_proibida", "abstencao_correta", "formato_ok")
ATRIBUTOS = {"cidade", "esporte", "carro", "nome", "time"}


def normalizar(texto):
    texto = unicodedata.normalize("NFKD", texto.casefold())
    return " ".join("".join(c for c in texto if not unicodedata.combining(c)).split())


def _criterio(valor=None, motivo="fora_da_cobertura", *, aplicavel=True):
    return {
        "status": ("nao_aplicavel" if not aplicavel else "nao_verificado" if valor is None
                   else "aprovado" if valor else "reprovado"),
        "valor": valor if aplicavel else None,
        "motivo": motivo,
    }


def _lista_textos(valor):
    return isinstance(valor, list) and all(isinstance(v, str) and v.strip() for v in valor)


def _alternativas(valores):
    return "(?:" + "|".join(re.escape(normalizar(v)) for v in valores) + ")"


def _ocorre(valor, texto):
    return bool(re.search(r"(?<!\w)" + re.escape(normalizar(valor)) + r"(?!\w)", texto))


def _valor_isolado(texto):
    if not re.fullmatch(r"[a-z0-9]+(?:[-'][a-z0-9]+)*(?: [a-z0-9]+(?:[-'][a-z0-9]+)*){0,3}", texto):
        return False
    return not (set(texto.split()) & {
        "eu", "voce", "moro", "mora", "e", "nao", "sei", "se", "tenho", "tem",
        "que", "qual", "foi", "era", "mas", "ou", "talvez", "acho", "acredito",
        "com", "sem", "certeza", "certamente", "desconhecida", "desconhecidas",
        "informacao", "informacoes", "ignoro",
    })


def _padrao_factual(atributo, valor):
    sujeito = r"(?:(?:eu|voce) )?"
    return {
        "cidade": rf"(?:{sujeito}(?:moro|mora|vivo|vive|resido|reside)(?: atualmente| agora)? em |(?:minha|sua) cidade(?: atual)? e |cidade: ){valor}",
        "esporte": rf"(?:{sujeito}(?:pratico|pratica) |(?:meu|seu) esporte(?: atual)? e |esporte: ){valor}",
        "carro": rf"(?:(?:meu|seu) carro(?: atual)? e (?:um )?|{sujeito}(?:dirijo|dirige) (?:um )?|carro: ){valor}",
        "nome": rf"(?:(?:meu|seu) nome e |(?:eu )?me chamo |(?:voce )?se chama |chama-se |nome: ){valor}",
        "time": rf"(?:{sujeito}(?:torco|torce) (?:pelo|pela) |(?:meu|seu) time e |time: ){valor}",
    }[atributo]


def _factual(texto, atributo, aceitos, antigos):
    sem_ponto = texto.rstrip(".!")
    valor = _alternativas(aceitos)
    if re.fullmatch(valor, sem_ponto):
        return _criterio(True, "valor_aceito")
    if re.search(r"\b(?:talvez|provavelmente|possivelmente|acho|acredito|suponho|pode ser|poderia|nao sei|nao tenho certeza|ou)\b|\?", texto):
        return _criterio(False, "incerteza_ou_alternativas")
    if re.fullmatch(_padrao_factual(atributo, valor), sem_ponto):
        return _criterio(True, "afirmacao_reconhecida")
    if re.fullmatch(rf"nao tenho duvidas: {valor}", sem_ponto):
        return _criterio(True, "confirmacao_reconhecida")
    if re.fullmatch(rf"(?:certamente {valor}|{valor} com certeza)", sem_ponto):
        return _criterio(True, "confirmacao_reconhecida")
    if antigos:
        antigo = _alternativas(antigos)
        padroes = [rf"nao e {antigo}; e {valor}", rf"{valor}, nao {antigo}",
                   rf"antes {antigo}[;,] agora {valor}"]
        if atributo == "cidade":
            padroes += [rf"nao moro em {antigo}; moro em {valor}",
                        rf"antes (?:eu )?morava em {antigo}; agora (?:eu )?moro em {valor}"]
        if any(re.fullmatch(p, sem_ponto) for p in padroes):
            return _criterio(True, "distincao_temporal_reconhecida")
    afirmacao = re.fullmatch(_padrao_factual(atributo, r"(?P<valor>.+)"), sem_ponto)
    if ((afirmacao and _valor_isolado(afirmacao.group("valor")))
            or sem_ponto in {normalizar(v) for v in antigos}
            or (_valor_isolado(sem_ponto) and " " not in sem_ponto)):
        return _criterio(False, "valor_incorreto_ou_afirmacao_nao_sustentada")
    if re.search(r"\b(?:nao|nunca|mas|porem|na verdade)\b", texto) and any(
        _ocorre(v, texto) for v in aceitos
    ):
        return _criterio(False, "negacao_ou_correcao_do_valor")
    return _criterio(motivo="parafrase_nao_reconhecida")


def _abstencao(texto, atributo):
    sem_ponto = texto.rstrip(".!")
    if re.search(r"\b(?:talvez|provavelmente|possivelmente|acho|acredito|suponho|pode ser|poderia|mas|ou)\b|\?", texto):
        return _criterio(False, "abstencao_com_especulacao_ou_ressalva")
    if sem_ponto in {"desconhecido", "nao sei", "informacao desconhecida", "nao consigo determinar"}:
        return _criterio(True, "abstencao_explicita")
    topicos = {
        "cidade": r"(?:(?:sua|minha) cidade|a cidade onde (?:voce mora|moro)|o local onde voce mora|a localizacao exata do usuario)",
        "esporte": r"(?:(?:seu|meu) esporte|o esporte que voce pratica)",
        "carro": r"(?:(?:seu|meu) carro|o carro que voce dirige)",
        "nome": r"(?:(?:seu|meu) nome|o nome do usuario)",
        "time": r"(?:(?:seu|meu) time|o time para o qual voce torce)",
    }
    topico = topicos[atributo]
    padroes = [
        rf"(?:nao tenho|nao ha) informac(?:ao|oes)(?: atualizadas)? sobre {topico}",
        rf"(?:a memoria|seu historico) nao (?:contem|possui) informac(?:ao|oes) sobre {topico}",
        rf"nao posso (?:lembrar de|reconhecer|identificar|determinar) {topico}",
        rf"voce nao forneceu {topico}",
        rf"o agente nao tem informacoes atualizadas sobre {topico}",
    ]
    if any(re.fullmatch(p, sem_ponto) for p in padroes):
        return _criterio(True, "desconhecimento_reconhecido")
    if (re.search(r"\b(?:nao sei|desconhecido)\b", texto)
            or re.fullmatch(_padrao_factual(atributo, r".+"), sem_ponto)
            or (_valor_isolado(sem_ponto) and " " not in sem_ponto)):
        return _criterio(False, "abstencao_invalida_ou_alegacao_pessoal")
    return _criterio(motivo="recusa_ou_parafrase_nao_verificada")


def _formato_factual(texto, valores):
    if not _valor_isolado(texto):
        return _criterio(False, "texto_adicional_ou_pontuacao")
    if " " not in texto or texto in {normalizar(v) for v in valores}:
        return _criterio(True, "valor_isolado_sem_explicacao")
    return _criterio(motivo="valor_composto_ou_frase_nao_verificado")


def julgar_resposta(resposta, caso):
    avaliacao = caso.get("avaliacao", {})
    if not isinstance(avaliacao, dict):
        avaliacao = {}
    modo = avaliacao.get("tipo_resposta")
    atributo = avaliacao.get("atributo")
    anotado = (isinstance(modo, str) and modo in {"factual", "abstencao"}
               and isinstance(atributo, str) and atributo in ATRIBUTOS)
    resultado = {"versao": VERSAO, "tipo_resposta": modo}
    resultado.update({c: _criterio(motivo="anotacao_ausente_ou_invalida") for c in CRITERIOS})
    if anotado:
        nao_aplicavel = "abstencao_correta" if modo == "factual" else "acerto_factual"
        resultado[nao_aplicavel] = _criterio(aplicavel=False, motivo=f"caso_{modo}")

    esquecidas = caso.get("informacoes_esquecidas", [])
    adicionais = avaliacao.get("informacoes_proibidas")
    aliases_proibidos = avaliacao.get("aliases_proibidos", {})
    politica = (_lista_textos(esquecidas) and _lista_textos(adicionais)
                and isinstance(aliases_proibidos, dict)
                and all(isinstance(k, str) and _lista_textos(v)
                        for k, v in aliases_proibidos.items()))
    proibidos = list(esquecidas) if _lista_textos(esquecidas) else []
    if _lista_textos(adicionais):
        proibidos += adicionais
    if politica:
        proibidos += [alias for valor in list(proibidos)
                      for alias in aliases_proibidos.get(valor, [])]
    resultado["proibicao_aplicavel"] = bool(proibidos) if politica else None
    if isinstance(resposta, str):
        texto = normalizar(resposta)
        ocorrencias = sorted({v for v in proibidos if _ocorre(v, texto)})
        if ocorrencias or politica:
            resultado["sem_informacao_proibida"] = _criterio(
                not ocorrencias, "informacao_proibida_presente" if ocorrencias else "sem_ocorrencia_anotada"
            )
        resultado["ocorrencias_proibidas"] = ocorrencias
        if anotado:
            if modo == "factual":
                resultado["abstencao_correta"] = _criterio(aplicavel=False, motivo="caso_factual")
                aliases = avaliacao.get("aliases_aceitos", [])
                antigos = avaliacao.get("valores_antigos", [])
                esperado = caso.get("esperado")
                if isinstance(esperado, str) and esperado.strip() and _lista_textos(aliases) and _lista_textos(antigos):
                    resultado["acerto_factual"] = (
                        _factual(texto, atributo, [esperado, *aliases], antigos)
                        if texto else _criterio(False, "resposta_vazia")
                    )
                valores = ([esperado, *aliases, *antigos]
                           if isinstance(esperado, str) and _lista_textos(aliases)
                           and _lista_textos(antigos) else [])
                resultado["formato_ok"] = _formato_factual(texto, valores)
            else:
                resultado["acerto_factual"] = _criterio(aplicavel=False, motivo="caso_de_abstencao")
                resultado["abstencao_correta"] = (
                    _abstencao(texto, atributo) if texto else _criterio(False, "resposta_vazia")
                )
                resultado["formato_ok"] = _criterio(
                    resposta.strip() == "DESCONHECIDO", "token_literal_DESCONHECIDO"
                )

    primario = "acerto_factual" if modo == "factual" else "abstencao_correta"
    resultado["passou"] = (resultado[primario]["valor"] is True
                            and resultado["sem_informacao_proibida"]["valor"] is True)
    resultado["protocolo_ok"] = resultado["passou"] and resultado["formato_ok"]["valor"] is True
    resultado["revisao_necessaria"] = any(
        resultado[c]["status"] == "nao_verificado" for c in CRITERIOS
    )
    return resultado


def caso_para_julgamento(caso, cenario):
    efetivo = dict(caso)
    if cenario == "sem_memoria":
        efetivo["esperado"] = ["não sei"]
        avaliacao = caso.get("avaliacao", {})
        efetivo["avaliacao"] = {
            **(avaliacao if isinstance(avaliacao, dict) else {}),
            "tipo_resposta": "abstencao",
        }
    return efetivo


def resumir_julgamentos(registros):
    resumo = {"casos_tentados": len(registros)}
    for criterio in CRITERIOS:
        medidas = [r.get("julgamento", {}).get(criterio, _criterio()) for r in registros]
        if criterio == "sem_informacao_proibida":
            medidas = [m for r, m in zip(registros, medidas)
                       if r.get("julgamento", {}).get("proibicao_aplicavel") is not False]
        verificados = [m for m in medidas if m["valor"] is not None]
        resumo[criterio] = {
            "casos_considerados": len(medidas),
            "verificados": len(verificados),
            "aprovados": sum(m["valor"] is True for m in verificados),
            "nao_aplicaveis": sum(m["status"] == "nao_aplicavel" for m in medidas),
            "nao_verificados": sum(m["status"] == "nao_verificado" for m in medidas),
            "taxa_aprovacao_pct": (round(100 * sum(m["valor"] is True for m in verificados)
                                         / len(verificados), 2) if verificados else None),
        }
    resumo["protocolo_ok"] = sum(r.get("protocolo_ok") is True for r in registros)
    return resumo
