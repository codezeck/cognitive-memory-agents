"""Ensaio destrutivo somente de usuarios sinteticos em um projeto Docker dedicado.

Requer Playwright/Chromium instalados separadamente. Nao grava cookies, headers,
traces ou HAR. Todas as respostas de conversa sao as da aplicacao real.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import subprocess
import time
import unicodedata
from datetime import datetime, timezone
from urllib.parse import urlsplit

from playwright.sync_api import sync_playwright


def normalizar(t):
    return ''.join(c for c in unicodedata.normalize('NFKD', t.casefold()) if not unicodedata.combining(c))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--url', required=True)
    p.add_argument('--projeto', required=True)
    p.add_argument('--saida', required=True)
    p.add_argument('--rodada', required=True)
    p.add_argument('--ambiente-isolado', action='store_true', required=True)
    args = p.parse_args()
    url = urlsplit(args.url)
    if url.hostname != '127.0.0.1' or url.port in {None, 8000, 8001, 18000}:
        p.error('Usar URL loopback e porta exclusiva do ensaio.')
    if not re.fullmatch(r'cma-(?:entrega|ensaio)-[a-z0-9-]+', args.projeto):
        p.error('Projeto precisa ter prefixo cma-entrega- ou cma-ensaio-.')
    if not re.fullmatch(r'[a-z0-9-]+', args.rodada):
        p.error('Rodada invalida.')
    pasta = Path(args.saida)
    pasta.mkdir(parents=True, exist_ok=True)
    log = (pasta / (args.rodada + '-interface.jsonl')).open('x', encoding='utf-8')
    verificacoes = []

    def gravar(tipo, **campos):
        log.write(json.dumps({'instante_utc':datetime.now(timezone.utc).isoformat(),
                              'tipo':tipo, **campos}, ensure_ascii=False) + '\n')
        log.flush()

    def verificar(nome, condicao, **campos):
        verificacoes.append({'nome':nome, 'aprovado':bool(condicao)})
        gravar('verificacao', nome=nome, aprovado=bool(condicao), **campos)

    def docker(*argumentos):
        return subprocess.check_output(['docker', *argumentos], encoding='utf-8')

    api_id = docker('ps','-q','--filter',f'label=com.docker.compose.project={args.projeto}',
                    '--filter','label=com.docker.compose.service=api').split()
    ollama_id = docker('ps','-q','--filter',f'label=com.docker.compose.project={args.projeto}',
                       '--filter','label=com.docker.compose.service=ollama').split()
    if len(api_id) != 1 or len(ollama_id) != 1:
        p.error('API/Ollama dedicados precisam estar ativos, uma instancia de cada.')
    api_id, ollama_id = api_id[0], ollama_id[0]
    configuracao = json.loads(docker('inspect', api_id))[0]
    env = dict(v.split('=',1) for v in configuracao['Config']['Env'])
    if env.get('USAR_FALSOS') != '0' or env.get('MODO_DEMONSTRACAO') != '1':
        p.error('Exige demonstracao local e agente real.')
    gravar('inicio', projeto=args.projeto, url=args.url, imagem=configuracao['Image'],
           api_id=api_id, ollama_id=ollama_id, modelo=env.get('LLM_MODEL'),
           observacao_ram=env.get('HABILITAR_OBSERVACAO_RAM'), p6_executada=False)

    def banco(etapa):
        codigo = "import sqlite3,json; c=sqlite3.connect('file:/app/dados/memorias.db?mode=ro',uri=True); print(json.dumps(c.execute('SELECT id,usuario_id,texto,ativa,chave FROM memorias ORDER BY id').fetchall(),ensure_ascii=False))"
        linhas = json.loads(docker('exec',api_id,'python','-c',codigo))
        gravar('sqlite_somente_leitura', etapa=etapa, linhas=linhas)
        return linhas

    def aguardar_api():
        import urllib.request
        for _ in range(90):
            try:
                with urllib.request.urlopen(args.url + '/saude',timeout=2) as resposta:
                    if resposta.status == 200:
                        return
            except OSError:
                pass
            time.sleep(1)
        raise RuntimeError('API de ensaio nao voltou.')

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        contexto = browser.new_context(viewport={'width':1440,'height':1000}, locale='pt-BR')
        pagina = contexto.new_page()
        pagina.set_default_timeout(20000)
        pagina.on('pageerror', lambda erro:gravar('erro_javascript', erro=str(erro)))
        try:
            pagina.goto(args.url)
            pagina.wait_for_selector('#model option[value="0"]',state='attached')
            pagina.wait_for_selector('#message:not([disabled])')
            verificar('acesso_automatico', pagina.locator('#user-name').inner_text()=='demo_professor')
            verificar('agente_real_na_tela', not pagina.locator('#test-badge').is_visible())

            def fotografia(nome):
                destino=pasta/(args.rodada+'-'+nome+'.png')
                if destino.exists(): raise RuntimeError('Captura ja existe.')
                pagina.screenshot(path=str(destino),full_page=True)
                gravar('captura',arquivo=destino.name)

            def token_atual():
                return next(c['value'] for c in contexto.cookies() if c['name']=='cma_acesso')

            def ram(etapa, token=None):
                r=contexto.request.post(args.url+'/avaliacao/ram',
                    headers={'Authorization':'Bearer '+(token or token_atual())},
                    data={'alvos':[{'rotulo':'cidade_antiga','termos':['Niteroi']},
                                   {'rotulo':'cidade_atual','termos':['Vitoria']}]})
                if r.status != 200: raise RuntimeError('Observador RAM nao disponivel no ensaio.')
                d=r.json();gravar('ram_processo_real',etapa=etapa,observacao=d)
                return d

            def perfil(valor):
                if pagina.locator('#demo-profile').input_value()!=valor:
                    with pagina.expect_response(lambda r:r.url.endswith('/interface/demonstracao')):
                        pagina.locator('#demo-profile').select_option(valor)
                esperado='demo_professor' if valor=='a' else 'demo_visitante'
                pagina.wait_for_function('(u)=>document.getElementById("user-name").textContent===u', arg=esperado)
                pagina.wait_for_selector('#message:not([disabled])')
                if pagina.locator('#user-name').inner_text()!=esperado:
                    raise RuntimeError('Perfil sintetico nao confirmado; abortar exclusoes.')

            def apagar_todas():
                pagina.once('dialog',lambda d:d.accept())
                with pagina.expect_response(lambda r:r.url.endswith('/interface/memorias') and r.request.method=='DELETE') as evento:
                    pagina.locator('#forget-all').click()
                gravar('exclusao_total_ui',status=evento.value.status,resultado=evento.value.json())
                pagina.wait_for_selector('#message:not([disabled])')

            def sessao():
                with pagina.expect_response(lambda r:r.url.endswith('/interface/nova-sessao')) as evento:
                    pagina.locator('#new-session').click()
                verificar('nova_sessao_http',evento.value.status==204)
                pagina.wait_for_selector('#message:not([disabled])')

            def conversar(mensagem,etapa,esperado_status=200):
                gravar('tentativa_conversa_ui',etapa=etapa,mensagem=mensagem,
                       usuario=pagina.locator('#user-name').inner_text())
                pagina.locator('#message').fill(mensagem)
                with pagina.expect_response(lambda r:r.url.endswith('/interface/conversas'),timeout=120000) as evento:
                    pagina.locator('#send').click()
                r=evento.value;dados=r.json()
                gravar('resposta_conversa_ui',etapa=etapa,status=r.status,resultado=dados)
                verificar(etapa+'_status',r.status==esperado_status)
                if r.status == 200:
                    origem = dados.get('origem_uso')
                    chamadas = dados.get('chamadas_modelo_observadas')
                    verificar(etapa+'_origem_explicita',origem in ('politica_local','provedor','provedor_com_abstencao_local'))
                    verificar(etapa+'_chamadas_coerentes',chamadas == (0 if origem == 'politica_local' else 1))
                    if origem == 'politica_local':
                        verificar(etapa+'_tokens_legados_preservados',dados.get('tokens_entrada') is None and dados.get('tokens_saida') is None)
                pagina.wait_for_selector('#message:not([disabled])',timeout=120000)
                return dados

            for valor in ('a','b'):
                perfil(valor);apagar_todas()
            perfil('a')
            fotografia('01-acesso')
            r0=ram('inicial')
            verificar('ram_inicial_sem_pessoais',r0['mensagens_pessoais']==0)
            a=conversar('Moro em Niteroi.','salvar_automaticamente')
            verificar('fato_extraido',any('Niteroi' in m for m in a.get('memorias_usadas',[])))
            sessao()
            a=conversar('Em qual cidade eu moro?','recuperar_nova_sessao')
            verificar('recuperacao_correta','niteroi' in normalizar(a.get('resposta','')))
            fotografia('02-recuperacao')
            conversar('Agora moro em Vitoria.','atualizar')
            a=conversar('Em que cidade eu moro? Responda somente a cidade.','consultar_atualizacao')
            verificar('resposta_atualizada','vitoria' in normalizar(a.get('resposta','')) and 'niteroi' not in normalizar(a.get('resposta','')))
            antes=banco('antes_reinicio')
            verificar('antigo_inativo',any(l[1]=='demo_professor' and 'Niteroi' in l[2] and l[3]==0 for l in antes))
            fotografia('03-atualizacao')
            instancia=ram('antes_reinicio')['instancia_id']
            estado_antes=json.loads(docker('inspect',api_id))[0]['State']['StartedAt']
            gravar('reinicio_solicitado',api_id=api_id,started_at=estado_antes)
            docker('restart',api_id);aguardar_api()
            pagina.reload();pagina.wait_for_selector('#model option[value="0"]',state='attached')
            verificar('identidade_preservada_apos_reinicio',pagina.locator('#user-name').inner_text()=='demo_professor')
            apos=banco('apos_reinicio')
            verificar('sqlite_persistiu',antes==apos)
            nova_instancia=ram('apos_reinicio')['instancia_id']
            verificar('processo_real_reiniciado',instancia!=nova_instancia and json.loads(docker('inspect',api_id))[0]['State']['StartedAt']!=estado_antes)
            a=conversar('Em que cidade eu moro?','perguntar_apos_reinicio')
            verificar('resposta_persistiu','vitoria' in normalizar(a.get('resposta','')))
            perfil('b');conversar('Moro em Maceio.','salvar_b');sessao()
            b=conversar('Em que cidade eu moro?','recuperar_b')
            verificar('isolamento_resposta_b','maceio' in normalizar(b.get('resposta','')) and 'vitoria' not in normalizar(b.get('resposta','')))
            token_b=token_atual();ram_b=ram('b_antes_exclusoes_a')
            fotografia('04-isolamento')
            perfil('a');token_a=token_atual()
            for metodo,caminho,corpo in [('GET','/usuarios/demo_visitante/memorias?consulta=cidade',None),
                                       ('DELETE','/usuarios/demo_visitante/memorias',None),
                                       ('POST','/conversas',{'usuario_id':'demo_visitante','mensagem':'Oi'})]:
                r=contexto.request.fetch(args.url+caminho,method=metodo,
                    headers={'Authorization':'Bearer '+token_a},data=corpo)
                verificar('acesso_cruzado_'+metodo,r.status==403,status=r.status)
            with pagina.expect_response(lambda r:r.url.endswith('/interface/memorias') and r.request.method=='POST'):
                pagina.locator('#memory-query').fill('Vitoria');pagina.locator('#memory-search').click()
            pagina.wait_for_selector('.memory-item button')
            pagina.once('dialog',lambda d:d.accept())
            with pagina.expect_response(lambda r:'/interface/memorias/' in r.url and r.request.method=='DELETE') as evento:
                pagina.locator('.memory-item button').first.click()
            verificar('exclusao_individual_http',evento.value.status==204)
            pagina.wait_for_selector('#message:not([disabled])')
            rs=ram('apos_delete_individual')
            verificar('ram_alvos_apagados',rs['alvos_no_historico']==0 and rs['mensagens_pessoais']==0)
            linhas=banco('apos_delete_individual')
            verificar('individual_preserva_versao_inativa',any(l[1]=='demo_professor' and l[3]==0 for l in linhas))
            a=conversar('Em qual cidade eu moro?','abstencao_apos_individual')
            verificar('abstencao_individual',a.get('resposta')=='DESCONHECIDO')
            rs=ram('apos_pergunta_sem_suporte')
            verificar('mensagens_legitimas_nao_sao_residuos',rs['mensagens_pessoais']>0 and rs['alvos_no_historico']==0)
            fotografia('05-abstencao')
            apagar_todas();linhas=banco('apos_exclusao_total')
            verificar('sqlite_usuario_sem_linhas',not any(l[1]=='demo_professor' for l in linhas))
            verificar('sqlite_b_preservado',any(l[1]=='demo_visitante' and 'Maceio' in l[2] for l in linhas))
            rb=ram('b_apos_exclusao_a',token_b)
            verificar('ram_b_preservada',rb['mensagens_total']==ram_b['mensagens_total'])
            a=conversar('Qual e o meu telefone?','nunca_informado')
            verificar('abstencao_nunca_informado',a.get('resposta')=='DESCONHECIDO')
            a=conversar('Qual e a capital da Franca?','pergunta_geral')
            verificar('geral_preservada','paris' in normalizar(a.get('resposta','')))
            a=conversar('Minha palavra de exemplo e NEVOA. Qual e a minha palavra de exemplo?','suporte_mensagem_atual')
            verificar('suporte_atual','nevoa' in normalizar(a.get('resposta','')))
            a=conversar('Qual e a minha palavra de exemplo?','suporte_historico')
            verificar('suporte_historico','nevoa' in normalizar(a.get('resposta','')))
            sessao();a=conversar('Qual e a minha palavra de exemplo?','apos_nova_sessao_sem_persistencia')
            verificar('historico_nao_persistido_desconhecido',a.get('resposta')=='DESCONHECIDO')
            pagina.locator('#model').select_option('1')
            a=conversar('Quanto e 2 + 3?','modelo_ausente',503)
            verificar('erro_modelo_tratado',a.get('codigo')=='provedor_indisponivel')
            fotografia('06-falha-modelo')
            pagina.locator('#model').select_option('0')
            docker('stop',ollama_id)
            a=conversar('Explique em uma frase o que e uma API.','ollama_indisponivel',503)
            verificar('erro_conexao_modelo_tratado',a.get('codigo')=='provedor_indisponivel')
            fotografia('07-falha-conexao')
            docker('start',ollama_id)
            # Erro de autenticacao verdadeiro, sem registrar o valor do cookie.
            contexto.clear_cookies()
            pagina.locator('#message').fill('Oi')
            with pagina.expect_response(lambda r:r.url.endswith('/interface/conversas')) as evento:
                pagina.locator('#send').click()
            verificar('sessao_sem_cookie_recusada',evento.value.status==401)
            pagina.wait_for_selector('#reactivate-demo:not([hidden])')
            fotografia('08-acesso-expirado')
            pagina.locator('#reactivate-demo').click()
            pagina.wait_for_selector('#message:not([disabled])')
            verificar('retomar_sem_copiar_token',pagina.locator('#user-name').inner_text()=='demo_professor')
            pagina.set_viewport_size({'width':390,'height':844})
            fotografia('09-mobile')
            verificar('layout_sem_rolagem_horizontal',pagina.evaluate('document.documentElement.scrollWidth<=innerWidth'))
            pagina.set_viewport_size({'width':1440,'height':1000})
            gravar('fim',verificacoes=verificacoes,aprovadas=sum(v['aprovado'] for v in verificacoes),
                   reprovadas=sum(not v['aprovado'] for v in verificacoes))
        except Exception as erro:
            gravar('interrupcao',classe=type(erro).__name__,erro=str(erro),verificacoes=verificacoes)
            raise
        finally:
            # Nao deixar o Ollama de ensaio parado depois de uma falha.
            subprocess.run(['docker','start',ollama_id],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            browser.close()
            log.close()
    print(json.dumps({'aprovadas':sum(v['aprovado'] for v in verificacoes),
                      'reprovadas':sum(not v['aprovado'] for v in verificacoes)}))
    return 1 if any(not v['aprovado'] for v in verificacoes) else 0


if __name__=='__main__':
    raise SystemExit(main())
