"""Congela novos casos sintéticos antes da primeira rodada v3; não sobrescreve."""
import hashlib
import json
from pathlib import Path


def main():
    casos = []
    def caso(mensagens, memorias, esperado, atributo, estado, antigos=(), esquecidos=()):
        abstencao = esperado is None
        casos.append({'id': f'V3T{len(casos)+1:03}',
                      'categoria': 'esquecimento' if esquecidos else 'sem_resposta' if abstencao else 'atualizacao' if antigos else 'recuperacao',
                      'descricao': 'Validação sintética v3; valores novos e escopo congelado',
                      'mensagens': mensagens, 'memorias': memorias,
                      'esperado': ['não sei'] if abstencao else esperado,
                      'estado_regras_esperado': estado,
                      'informacoes_esquecidas': list(esquecidos),
                      'avaliacao': {'tipo_resposta': 'abstencao' if abstencao else 'factual',
                                    'atributo': atributo, 'aliases_aceitos': [],
                                    'valores_antigos': list(antigos), 'informacoes_proibidas': []}})
    final = (' Responda somente com o valor solicitado, sem explicações. '
             'Se não houver informação suficiente, responda exatamente DESCONHECIDO.')
    caso(['Moro em Jacareí.', 'Em qual cidade eu vivo?' + final], ['Moro em Jacareí.'], 'Jacareí', 'cidade', {'cidade':'Jacareí'})
    caso(['Moro em Taubaté.', 'Mudei para Maringá.', 'Qual é a minha cidade atual?' + final],
         ['Mora em Maringá.'], 'Maringá', 'cidade', {'cidade':'Maringá'}, ['Taubaté'])
    caso(['Meu carro é um Siena.', 'Meu carro agora é um Duster.', 'Que automóvel dirijo hoje?' + final],
         ['Carro: Duster.'], 'Duster', 'carro', {'carro':'Duster'}, ['Siena'])
    caso(['Meu carro é um Etios.', 'Não uso mais o Etios.', 'Qual é meu carro?' + final],
         [], None, 'carro', {}, esquecidos=['Etios'])
    caso(['Meu carro é um Ka.', 'Meu carro agora é um Kicks.', 'Não tenho mais o Ka.', 'Qual é meu carro atual?' + final],
         ['Carro: Kicks.'], 'Kicks', 'carro', {'carro':'Kicks'}, ['Ka'])
    caso(['Pratico pilates.', 'Qual atividade física eu pratico?' + final],
         ['Pratica pilates.'], 'pilates', 'esporte', {'esporte':'pilates'})
    caso(['Meu nome é Beatriz.', 'Pratico tênis.', 'Qual esporte pratico?' + final],
         ['Pratica tênis.'], 'tênis', 'esporte', {'nome':'Beatriz','esporte':'tênis'})
    caso(['Torço pelo Fortaleza.', 'Para qual time torço?' + final],
         ['Torce para Fortaleza.'], 'Fortaleza', 'time', {'time':'Fortaleza'})
    caso(['Torço pelo Vitória.', 'Não torço mais pelo Vitória.', 'Para qual time eu torço?' + final],
         [], None, 'time', {}, esquecidos=['Vitória'])
    caso(['Trabalho como arquiteta.', 'Qual é minha ocupação?' + final],
         ['Profissão: arquiteta.'], 'arquiteta', 'profissao', {'profissao':'arquiteta'})
    caso(['Meu nome é Cecília.', 'Qual é meu nome?' + final],
         ['Chama-se Cecília.'], 'Cecília', 'nome', {'nome':'Cecília'})
    caso(['Meu nome é Otávio.', 'Apague meu nome.', 'Como me chamo?' + final],
         [], None, 'nome', {}, esquecidos=['Otávio'])
    caso(['Tenho quatro filhos.', 'Quantos filhos eu tenho?' + final],
         ['Tem 4 filhos.'], '4', 'filhos', {'filhos':'4'})
    caso(['Moro em Blumenau.', 'Qual é meu nome?' + final], [], None, 'nome', {'cidade':'Blumenau'})
    caso(['Meu carro é um Fit.', 'Meu nome é Elisa.', 'Esqueça tudo sobre mim.', 'Qual é meu nome?' + final],
         [], None, 'nome', {}, esquecidos=['Elisa','Fit'])
    caso(['Moro em Aracaju.', 'Meu carro é um Versa.', 'Qual é meu carro?' + final],
         ['Carro: Versa.'], 'Versa', 'carro', {'cidade':'Aracaju','carro':'Versa'})
    destino = Path('eval/dataset_validacao_v3_20261118.json')
    bruto = json.dumps(casos, ensure_ascii=False, indent=2) + '\n'
    with destino.open('x', encoding='utf-8') as f:
        f.write(bruto)
    from eval.avaliar_comparativo import validar_dataset_p4
    validar_dataset_p4(casos)
    print(json.dumps({'casos':len(casos),'sha256':hashlib.sha256(destino.read_bytes()).hexdigest()}))


if __name__ == '__main__':
    main()
