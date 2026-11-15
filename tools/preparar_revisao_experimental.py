"""Prepara propostas nao executaveis; nunca altera dados oficiais ou chama LLM."""
import hashlib
import json
from pathlib import Path

from eval.avaliar_comparativo import validar_dataset_p4


def main():
    pasta = Path('docs/revisao-experimental')
    pasta.mkdir(parents=True, exist_ok=True)
    origem = Path('eval/dataset_teste.json')
    casos = json.loads(origem.read_text(encoding='utf-8-sig'))
    atributos = {
        'TST001':'cidade','TST002':'cidade','TST003':'esporte','TST004':'carro',
        'TST005':'nome','TST006':'carro','TST007':'esporte','TST008':'carro',
        'TST009':'esporte','TST010':'carro',
    }
    antigos = {'TST002':['Recife','Salvador'],'TST008':['Uno'],'TST010':['Gol','Palio']}
    candidatos = []
    for caso in casos:
        metadata = {
            'tipo_resposta':'abstencao' if caso['categoria'] in {'esquecimento','sem_resposta'} else 'factual',
            'atributo':atributos[caso['id']], 'aliases_aceitos':[],
            'valores_antigos':antigos.get(caso['id'],[]),
            'informacoes_proibidas':[], 'aliases_proibidos':{},
        }
        candidatos.append({**caso, 'avaliacao':metadata})
    validar_dataset_p4(candidatos)  # Somente forma dos metadados; sem respostas.
    try:
        validar_dataset_p4(casos)
    except ValueError:
        bloqueio_original = True
    else:
        bloqueio_original = False
    documento = {
        'estado':'proposta_nao_aprovada', 'aprovado':False,
        'origem':str(origem), 'sha256_origem':hashlib.sha256(origem.read_bytes()).hexdigest(),
        'finalidade':'Revisao de anotacoes, sem execucao ou ajuste do produto com respostas reservadas.',
        'validacao_estrutural_candidatos':'10 compativeis; nao certifica semantica',
        'dataset_oficial_continua_bloqueado':bloqueio_original,
        'revisoes_necessarias':['Vinicius: atributos, valores antigos, aliases e alvos esquecidos',
                               'Zeck: politica P4 e denominadores; sem adaptar dados a respostas'],
        'casos_propostos':candidatos,
    }
    with (pasta/'metadados-reservados.proposta.json').open('x',encoding='utf-8') as f:
        json.dump(documento,f,ensure_ascii=False,indent=2)
    p6 = Path('eval/memoria/anotacoes_p6.json')
    protocolo = {
        'estado':'proposta_nao_aprovada', 'aprovado':False,
        'sha256_anotacoes_oficiais':hashlib.sha256(p6.read_bytes()).hexdigest(),
        'contrato_esquecimento':{
            'evento':'u02/s5/esquecer_chaves','chaves':['carro'],
            'mensagem':'Esque\u00e7a tudo sobre meu carro.', 'aprovado':False,
            'referencia':None,'revisores_necessarios':['Vinicius','Paloma'],
            'limite':'A forma das regras pode ser testada em desenvolvimento; isso nao aprova a mensagem oficial.',
        },
        'quantidade_gatos':{
            'evento':'u03/s4/pergunta3','recuperacao':['Luna','Simba'],
            'resposta':'dois','aliases':['2'],'aprovado':False,
            'pergunta_revisao':'Os dois nomes representam exatamente dois gatos atuais nesta pergunta?',
        },
        'checkpoint_vazio':{
            'evento':'u04/s4/checkpoint_persistencia','aprovado':False,
            'proposta':'Separar consistencia de estado vazio de persistencia de fatos nao vazios.',
            'evidencias_necessarias':['reinicio real e identidade da instancia',
                'SQLite incluindo inativos antes/depois','mesmo volume/arquivo, ausencia de escritores concorrentes'],
            'classificacao_atual':'nao_verificado; o executor nao foi alterado',
            'decisao_necessaria':'Equipe decide aplicabilidade e formato versionado antes de executar P6.',
        },
        'coleta_ram':{'implementado':'POST /avaliacao/ram opt-in, um worker identificado',
                     'aprovado_para_p6':False,'limite':'Alvos literais normalizados; contagem de mensagens pessoais separada de mensagens de sistema.'},
    }
    with (pasta/'p6.proposta.json').open('x',encoding='utf-8') as f:
        json.dump(protocolo,f,ensure_ascii=False,indent=2)
    print('Propostas preparadas sem alterar dados oficiais; nenhuma resposta de LLM obtida.')
    print('Validacao estrutural de 10 candidatos; dados oficiais continuam bloqueados:',bloqueio_original)


if __name__=='__main__':
    main()
