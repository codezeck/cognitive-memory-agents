"""Busca por chave para consultas pessoais reconhecidas; fallback vetorial."""

from src.evidencias_pessoais import _atributo, _afirma_suporte


def selecionar_por_chave(consulta: str, registros: list[dict], k: int):
    # Apenas perguntas diretas do domínio já reconhecido pela política local.
    # Instruções de formato posteriores não alteram o atributo consultado.
    import re
    trecho = re.split(r'(?<=[.!?])\s*|\n+', consulta.strip())[0]
    atributo = _atributo(trecho)
    if atributo not in {'cidade', 'nome', 'profissao', 'apelido', 'carro', 'time', 'esporte',
                        'filhos', 'viagem', 'pet:gato:', 'pet:cachorro:', 'gosto:'}:
        return None
    chaves_tipadas = {'cidade', 'nome', 'profissao', 'apelido', 'carro', 'time', 'esporte', 'filhos', 'viagem'}
    correspondentes = [r for r in registros if r.get('chave') == atributo or
                       atributo.endswith(':') and (r.get('chave') or '').startswith(atributo) or
                       r.get('chave') not in chaves_tipadas and
                       not (r.get('chave') or '').startswith(('pet:', 'favorito:', 'gosto:')) and
                       _afirma_suporte(r['texto'], atributo, memoria=True)]
    if not correspondentes:
        return None
    # 1.0 representa correspondência exata de chave, não cosseno do embedder.
    return [{'id': r['id'], 'texto': r['texto'], 'score': 1.0}
            for r in correspondentes[:k]]
