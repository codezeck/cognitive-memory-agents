"""Gera rascunho ABNT e figuras a partir de textos e resultados preservados."""
from __future__ import annotations

import hashlib
import argparse
import json
import re
from html import escape
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import BaseDocTemplate, Frame, Image, KeepTogether, PageBreak, PageTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.platypus.tableofcontents import TableOfContents

ROOT = Path(__file__).resolve().parents[1]
EVID = ROOT / 'evidencias/entrega/20261114-entrega-ae9eb113'
FIG = EVID / 'figuras'
ATUAL = ROOT / 'evidencias/melhorias-20261118'
ENTREGA3 = ROOT / 'evidencias/entrega-v3-20261118'
CONSOLIDACAO = ROOT / 'evidencias/consolidacao-interface-20261120'


def limpo(texto):
    texto = re.sub(r'\[([^]]+)\]\(([^)]+)\)', r'\1', texto)
    texto = texto.replace('**','').replace('`','').replace('—','-').replace('–','-')
    return escape(texto)


class Documento(BaseDocTemplate):
    def afterFlowable(self, item):
        if isinstance(item,Paragraph) and item.style.name in ('Figura','Tabela'):
            self.notify(item.style.name+'Entry',(0,item.getPlainText(),self.page-1))
        if isinstance(item, Paragraph) and item.style.name == 'Capitulo':
            texto = item.getPlainText()
            if texto=='1 INTRODUÇÃO':self.primeira_textual=self.page
            if texto in ('RESUMO','ABSTRACT','SUMÁRIO','LISTA DE FIGURAS','LISTA DE TABELAS'):
                return
            self.notify('TOCEntry',(0,texto,self.page-1))
            self.canv.bookmarkPage(texto)
            self.canv.addOutlineEntry(texto,texto,0,False)


class Indice(TableOfContents):
    def __init__(self,tipo):
        super().__init__();self.tipo=tipo

    def notify(self,kind,stuff):
        if kind==self.tipo:super().notify('TOCEntry',stuff)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--saida',type=Path,default=ROOT/'docs/pesquisa-abnt.pdf')
    parser.add_argument('--metadados',type=Path,default=ROOT/'docs/pesquisa-consolidacao-geracao.json')
    parser.add_argument('--render-dir',type=Path,default=ROOT/'.env.pdf-revisao-v3-final')
    args=parser.parse_args()
    FIG.mkdir(exist_ok=True)
    ENTREGA3.mkdir(exist_ok=True)
    academicos=json.loads((ROOT/'docs/dados-academicos.json').read_text(encoding='utf-8'))
    texto_v3=(ROOT/'docs/pesquisa-v3.md').read_text(encoding='utf-8')
    blocos_v3={n:t for n,t in re.findall(r'^## ([^\n]+)\n(.*?)(?=^## |\Z)',texto_v3,re.M|re.S)}
    arquivos = {
        'historico': ROOT/'evidencias/comparativo_oficial_3rep.json',
        'desenvolvimento': EVID/'comparativo-desenvolvimento.json',
    }
    nomes = ['Sem memória','Histórico','Pré-carregada','Automática']
    cenarios = ['sem_memoria','historico_completo','memoria_persistente_api','memoria_regras_api']
    for rotulo,arquivo in arquivos.items():
        if (FIG / f'{rotulo}.png').exists():
            continue  # Preservar bytes e hashes das figuras históricas.
        dados=json.loads(arquivo.read_text(encoding='utf-8'))
        fig,eixos=plt.subplots(1,2,figsize=(10,3.7),layout='constrained')
        for eixo,campo,titulo in zip(eixos,('aprovados','tokens_total'),('Conteúdo aprovado / 21','Tokens registrados')):
            valores=[dados['resumo'][c][campo] for c in cenarios]
            barras=eixo.bar(nomes,valores,color=['#93a9a1','#355e54','#bc9e67','#657d92'])
            eixo.set_title(titulo,fontsize=11)
            eixo.tick_params(axis='x',labelsize=8)
            eixo.bar_label(barras,padding=3,fontsize=8)
            eixo.set_ylim(0,max(valores)*1.2)
            eixo.spines[['top','right']].set_visible(False)
        fig.suptitle('Protocolo histórico (28/10)' if rotulo=='historico' else 'Desenvolvimento (14/11): sessão completa',fontsize=13)
        fig.savefig(FIG/f'{rotulo}.png',dpi=180)
        plt.close(fig)
    for n,arquivo in [('Times','times.ttf'),('TimesBold','timesbd.ttf'),('TimesItalic','timesi.ttf')]:
        pdfmetrics.registerFont(TTFont(n,'C:/Windows/Fonts/'+arquivo))
    corpo=ParagraphStyle('Corpo',fontName='Times',fontSize=12,leading=18,alignment=TA_JUSTIFY,firstLineIndent=1.25*cm,spaceAfter=9)
    cap=ParagraphStyle('Capitulo',parent=corpo,fontName='TimesBold',firstLineIndent=0,spaceBefore=10,spaceAfter=20,keepWithNext=True)
    sub=ParagraphStyle('Sub',parent=cap,fontSize=12,spaceBefore=14,spaceAfter=12)
    centro=ParagraphStyle('Centro',parent=corpo,alignment=TA_CENTER,firstLineIndent=0)
    legenda=ParagraphStyle('Legenda',parent=corpo,fontSize=10,leading=12,firstLineIndent=0,spaceAfter=12)
    figura=ParagraphStyle('Figura',parent=legenda)
    tabela=ParagraphStyle('Tabela',parent=legenda)
    refs=ParagraphStyle('Referencia',parent=corpo,firstLineIndent=0,alignment=0,leading=12,spaceAfter=12)
    elementos=[]
    def p(txt,estilo=corpo): elementos.append(Paragraph(limpo(txt),estilo))
    def titulo(txt): elementos.append(Paragraph(txt,cap))
    ras=academicos.get('ras',{})
    if (set(ras)!=set(academicos['integrantes'])
            or any(not isinstance(v,str) or not re.fullmatch(r'\d{7}',v) for v in ras.values())):
        raise ValueError('Cada integrante precisa de um RA válido no cadastro acadêmico.')
    autores=[nome+' - RA: '+ras[nome] for nome in academicos['integrantes']]
    p(academicos['instituicao'].upper(),centro)
    p('PROJETO INTEGRADOR',centro);p('EAD_PROINT_100.DD-ADS-PI-10-74.2026.74',centro)
    elementos.append(Spacer(1,2*cm))
    for autor in autores:p(autor,centro)
    elementos.append(Spacer(1,3*cm))
    p('COGNITIVE MEMORY AGENTS',ParagraphStyle('Titulo',parent=centro,fontName='TimesBold',fontSize=16,leading=22))
    p('Memória contextual, abstenção e avaliação de um agente local',centro)
    elementos.append(Spacer(1,3*cm));p('Versão candidata v3 para revisão',centro);p('Atualização documental de 21 de novembro de 2026',centro)
    elementos.append(PageBreak())
    p('COGNITIVE MEMORY AGENTS',centro)
    elementos.append(Spacer(1,3*cm))
    p('Trabalho de Projeto Integrador apresentado à '+academicos['instituicao']+' sobre o Tema 11: memória de longo prazo para agentes. O estudo documenta a arquitetura implementada, a avaliação experimental e as evidências operacionais de um chatbot com memória persistente.',corpo)
    p('Autores: '+', '.join(autores)+'. O projeto reúne as frentes de agente e avaliação, memória e conflitos, API e infraestrutura.',corpo)
    p('A versão v3 incorpora resultados de qualidade e custo, limitações do julgador e rastreabilidade dos dados. A revisão final do grupo e os registros de publicação, demonstração e envio são acompanhados no checklist de entrega.',corpo)
    elementos.append(PageBreak());titulo('RESUMO')
    p('Este trabalho apresenta um agente conversacional com memória persistente por usuário, API, SQLite e Ollama. Avalia continuidade, atualização, esquecimento e tokens de geração. A arquitetura confirma localmente operações reconhecidas e seleciona contexto para respostas com suporte. A P6 de 18/11 completou vinte sessões por cenário e 42 respostas: 21 aprovações P4 na automática; oito aprovações e doze julgamentos não verificados no histórico. A redução foi 83,84% em vinte pares completos, com dezenove checkpoints não vazios de persistência e dois de exclusão verificados. O levantamento posterior preservou 14 relatórios locais. Nove comparativos oficiais completos, ao longo de versões do executor, tiveram redução consolidada de 84,80%; a rodada oficial atual teve 84,91%. Duas rodadas do conjunto personalizado atual somaram oitenta tentativas por cenário e redução de 74,13%, com médias de 200,09 tokens na automática e 773,44 no histórico. Na última rodada personalizada, a automática aprovou 42/45 fatos e 15/15 abstenções, contra 44/45 e 8/15 no histórico. Cinco P6 posteriores de 21/11 tiveram redução consolidada de 85,62%, mantendo qualidade adicional versionada e inconclusivos. Erros, formato, inconclusivos e medições parciais permanecem explícitos. O novo controle sem memória consulta Ollama diretamente. Os dados são sintéticos, conhecidos ou selecionados pela equipe; repetições não são amostras independentes. O estudo não demonstra equivalência estatística, economia universal ou conformidade jurídica.')
    p('Palavras-chave: agentes de linguagem; memória contextual; avaliação; esquecimento; reprodutibilidade.',refs)
    elementos.append(PageBreak());titulo('ABSTRACT')
    p('This study presents a conversational agent with per-user persistent memory, an API, SQLite and Ollama. It evaluates continuity, updates, forgetting and generation tokens. Recognized memory operations are confirmed locally, while supported answers use selected context. The November 18 P6 evaluation completed twenty sessions per scenario and 42 answers: automatic memory received 21 P4 approvals, while full history received eight approvals and twelve unresolved judgments. Token reduction was 83.84 percent across twenty complete pairs; nineteen nonempty persistence checkpoints and two deletion checkpoints passed. A subsequent inventory preserved 14 local reports. Nine complete official comparisons across executor versions showed a pooled reduction of 84.80 percent; the current official run showed 84.91 percent. Two current custom-dataset runs comprised eighty attempts per scenario and showed a pooled reduction of 74.13 percent, averaging 200.09 tokens per attempt for automatic memory and 773.44 for full history. In the last custom-dataset run, automatic memory received 42/45 factual approvals and 15/15 correct abstentions, compared with 44/45 and 8/15 for full history. Five later P6 runs on November 21 showed a pooled token reduction of 85.62 percent, with versioned additional quality analysis and unresolved judgments preserved. Errors, format violations, unresolved judgments and partial measurements remain explicit. The new no-memory control queries Ollama directly. Synthetic data and selected cases are not blind independent validation; repetitions are not independent samples. The study does not establish statistical equivalence, universal savings or legal compliance.')
    p('Keywords: language agents; contextual memory; evaluation; forgetting; reproducibility.',refs)
    for nome,tipo in [('LISTA DE FIGURAS','FiguraEntry'),('LISTA DE TABELAS','TabelaEntry')]:
        elementos.append(PageBreak());p(nome,cap)
        indice=Indice(tipo);indice.levelStyles=[ParagraphStyle(tipo,parent=corpo,firstLineIndent=0,leading=20)]
        elementos.append(indice)
    elementos.append(PageBreak());p('SUMÁRIO',cap)
    toc=TableOfContents();toc.levelStyles=[ParagraphStyle('TOC',parent=corpo,firstLineIndent=0,leading=20)]
    elementos.append(toc);elementos.append(PageBreak())
    base=(ROOT/'docs/contribuicao-academica-zeck.md').read_text(encoding='utf-8')
    secoes={int(n):t for n,t in re.findall(r'^## (\d+)\.[^\n]*\n(.*?)(?=^## |\Z)',base,re.M|re.S)}
    def markdown(txt):
        txt=re.sub(r'```.*?```','',txt,flags=re.S)
        for bloco in re.split(r'\n\s*\n',txt.strip()):
            if bloco.startswith('|'):continue
            if bloco.startswith('## '):p(bloco[3:],sub)
            else:p(' '.join(bloco.splitlines()))
    secoes.update({2:blocos_v3['Introdução'],3:blocos_v3['Referencial teórico'],4:blocos_v3['Arquitetura v3'],5:blocos_v3['Protocolo e métricas']})
    for n,nome in [(2,'1 INTRODUÇÃO'),(3,'2 REFERENCIAL TEÓRICO'),(4,'3 METODOLOGIA')]:
        if n>2:elementos.append(PageBreak())
        titulo(nome);markdown(secoes[n])
    p('3.1 Protocolo e métricas',sub);markdown(secoes[5])
    p('Os procedimentos operacionais a seguir foram desenvolvidos nos ensaios de integração e reutilizados no estudo. Os resultados históricos permanecem identificados por data; os resultados da v3 e seus limites constam das subseções 4.3 a 4.6.')
    suplemento=(ROOT/'docs/pesquisa-complemento.md').read_text(encoding='utf-8')
    markdown(suplemento[suplemento.index('## '):suplemento.index('## Resultado operacional')])
    p('3.2 Política de contexto e confirmação local v3',sub)
    markdown(blocos_v3['Metodologia v3'])
    elementos.append(PageBreak());titulo('4 RESULTADOS E DISCUSSÃO')
    p('4.1 Evidência histórica',sub)
    elementos.append(KeepTogether([Paragraph('Figura 1 - Resultados históricos sob protocolo anterior',figura),Image(str(FIG/'historico.png'),width=15.5*cm,height=5.74*cm),Paragraph('Fonte: comparativo_oficial_3rep.json, resumo original. Não há recálculo com P4-v3.',legenda)]))
    markdown(secoes[6])
    p('4.2 Integração e ensaio de 14/11',sub)
    p('O ensaio de 14/11 validou o iniciador e o chat em Docker, incluindo erros tratados de modelo, conexão e autenticação. As capturas e os logs reais foram preservados. Esses ensaios operacionais não substituem as avaliações comparativas posteriores.')
    elementos.append(KeepTogether([Paragraph('Figura 2 - Comparativo exploratório de desenvolvimento (14/11)',figura),Image(str(FIG/'desenvolvimento.png'),width=15.5*cm,height=5.74*cm),Paragraph('Fonte: comparativo-desenvolvimento.json; P4-v3, P5-v1 e p3-uso-local-v1. Três repetições não são casos independentes.',legenda)]))
    dados=json.loads(arquivos['desenvolvimento'].read_text(encoding='utf-8'))
    celula=ParagraphStyle('Celula',parent=legenda,fontSize=10,leading=12,spaceAfter=0)
    linhas=[['Cenário','Conteúdo','Tokens da sessão','Cobertura']]
    for nome,c in zip(nomes,cenarios):
        s=dados['resumo'][c];linhas.append([nome,f"{s['aprovados']}/21",str(s['tokens_total']),'21/21'])
    tab=Table([[Paragraph(limpo(v),celula) for v in row] for row in linhas],colWidths=[5*cm,3*cm,4.5*cm,3.5*cm],repeatRows=1)
    tab.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#e2e9e6')),('LINEBELOW',(0,0),(-1,0),0.6,colors.black),('LINEBELOW',(0,-1),(-1,-1),0.6,colors.black),('VALIGN',(0,0),(-1,-1),'TOP'),('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7)]))
    elementos.append(KeepTogether([Paragraph('Tabela 1 - Conteúdo e uso no desenvolvimento de 14/11',tabela),tab,Spacer(1,6),Paragraph('Fonte: resumo bruto, sem novo julgamento; sessão inclui ingestão e pergunta final. Pré-carregada não mede aquisição.',legenda)]))
    estudo=(ROOT/'docs/ensaio-desenvolvimento-20261114.md').read_text(encoding='utf-8')
    p('Na rodada exploratória de 14/11, a memória automática aprovou 17/21 respostas e consumiu 17.094 tokens, contra 12/21 e 16.017 no histórico: aumento de 6,72%, sem atingir a meta adicional. As 22 falhas de conteúdo dos quatro cenários foram mantidas. A pré-carregada não mede aquisição; repetir sete casos não produz 21 usuários independentes.')
    elementos.append(PageBreak())
    p('4.3 Resultados da versão v3',sub)
    markdown(blocos_v3['Resultados v3'])
    elementos.append(KeepTogether([Paragraph('Figura 3 - P6 v3: custo completo e cobertura do julgador',figura),Image(str(ENTREGA3/'figuras/p6-v3.png'),width=15.5*cm,height=6.2*cm),Paragraph('Fonte: P6 v3, resumo e JSONL originais; vinte pares medidos. Não verificados do baseline não são erros confirmados.',legenda)]))
    linhas3=[['Cenário','P4 aprovado','Não verificados','Tokens completos'],['Automática','21/21','0','3.593'],['Histórico completo','8/21','12','22.228']]
    tab3=Table([[Paragraph(limpo(v),celula) for v in row] for row in linhas3],colWidths=[5*cm,3*cm,3.5*cm,4.5*cm],repeatRows=1)
    tab3.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#e2e9e6')),('LINEBELOW',(0,0),(-1,0),0.6,colors.black),('LINEBELOW',(0,-1),(-1,-1),0.6,colors.black),('VALIGN',(0,0),(-1,-1),'TOP'),('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7)]))
    elementos.append(KeepTogether([Paragraph('Tabela 2 - P6 v3: resultados e denominadores',tabela),tab3,Paragraph('Fonte: resumo P6 v3. A comparação de tokens tem cobertura 20/20; qualidade automática do baseline é parcialmente não verificada.',legenda)]))
    elementos.append(KeepTogether([Paragraph('Figura 4 - Validação sintética v3: aprovação e custo pareado',figura),Image(str(ENTREGA3/'figuras/validacao-v3.png'),width=15.5*cm,height=6.2*cm),Paragraph('Fonte: validação v3, dezesseis casos e três repetições. Um timeout no baseline exclui um par da comparação de tokens; não é teste cego.',legenda)]))
    p('4.4 Consolidação das rodadas locais de 20/11',sub)
    markdown(blocos_v3['Consolidação de 20/11'])
    consolidado=json.loads((CONSOLIDACAO/'consolidado.json').read_text(encoding='utf-8'))
    atuais=[g for g in consolidado['grupos'] if g['etapa']=='Etapa 4']
    oficial=next(g for g in atuais if g['conjunto']=='oficial')
    personalizado=next(g for g in atuais if g['conjunto']!='oficial')
    def numero(v):return f'{v:,.2f}'.replace(',','X').replace('.',',').replace('X','.')
    linhas4=[['Cenário','Oficial (48)','Personalizado (80)']]
    for nome in oficial['cenarios']:
        linhas4.append([nome,numero(oficial['cenarios'][nome]['media_tokens_por_tentativa']),numero(personalizado['cenarios'][nome]['media_tokens_por_tentativa'])])
    def tabela_atual(titulo_texto,linhas,larguras,nota):
        tab=Table([[Paragraph(limpo(str(v)),celula) for v in row] for row in linhas],colWidths=[v*cm for v in larguras],repeatRows=1)
        tab.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#e2e9e6')),('LINEBELOW',(0,0),(-1,0),0.6,colors.black),('LINEBELOW',(0,-1),(-1,-1),0.6,colors.black),('VALIGN',(0,0),(-1,-1),'TOP'),('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5)]))
        elementos.append(KeepTogether([Paragraph(titulo_texto,tabela),tab,Paragraph(nota,legenda)]))
    tabela_atual('Tabela 3 - Consumo médio atual em tokens por tentativa',linhas4,[6,5,5],'Fonte: relatórios locais preservados e consolidados de 20/11. Episódio completo; pré-carregada não mede aquisição. Reduções: oficial atual 84,91%; personalizado 74,13%.')
    elementos.append(KeepTogether([Paragraph('Figura 5 - Consumo médio nos dois conjuntos atuais',figura),Image(str(CONSOLIDACAO/'medias-atuais.png'),width=15.5*cm,height=6.2*cm),Paragraph('Fonte: consolidados de 20/11; tokens de geração por tentativa completa. Menos tokens não implica mais acertos.',legenda)]))
    tabela_atual('Tabela 4 - Qualidade da última rodada personalizada',[
        ['Cenário','Fatos / 45','Abstenção / 15','Estrito / 60'],
        ['Histórico completo','44','8','48'],['Memória automática','42','15','50'],['Sem memória','1','7','5'],['Pré-carregada','40','15','54']],
        [5.2,3.6,3.6,3.6],'Fonte: P4 original, três repetições de vinte casos. Estrito exige conteúdo e formato. Sem memória: sete fatos e duas abstenções inconclusivos; pré-carregada: cinco fatos inconclusivos. Não são acertos ou erros confirmados.')
    p('4.5 Consolidação da P6 de 21/11',sub)
    markdown(blocos_v3['Consolidação P6 de 21/11'])
    fechamento=json.loads((ROOT/'evidencias/fechamento-p6-20261121/consolidado.json').read_text(encoding='utf-8'))
    linhas5=[['Etapa da análise','Rodadas','Histórico','Automática','Redução']]
    for nome,g in fechamento['grupos'].items():
        linhas5.append([nome,str(g['rodadas']),numero(g['media_historico_por_rodada']),numero(g['media_automatica_por_rodada']),numero(g['reducao_consolidada_pct'])+'%'])
    tabela_atual('Tabela 5 - P6: média de tokens por rodada completa e etapa',linhas5,[4.7,1.9,3.1,3.1,3.2],'Fonte: cinco relatórios completos de 21/11, cem pares. Mesma geração e anotações por hashes; etapas não isolam causalidade. Qualidade adicional v2 preserva os originais e seus inconclusivos.')
    p('4.6 Análise de erros e validade',sub)
    markdown(blocos_v3['Erros e alcance'])
    elementos.append(PageBreak())
    titulo('5 CONSIDERAÇÕES FINAIS')
    markdown(blocos_v3['Conclusão v3'])
    elementos.append(PageBreak());titulo('REFERÊNCIAS')
    referencias=secoes[8]
    bibliografia=[]
    for linha in referencias.splitlines():
        if re.match(r'^\d+\. ',linha):
            texto=re.sub(r'\[([^]]+)\]\(([^)]+)\)',r'\2',linha)
            bibliografia.append(re.sub(r'^\d+\. ','',texto))
    for txt in [
        'OPENAI. What is ChatGPT Plus? Documento de suporte: uso de API separado da assinatura. Disponível em: https://help.openai.com/en/articles/6950777-what-is-chatgpt-plus. Acesso em: 20 nov. 2026.',
        'DOCKER. Control startup and shutdown order in Compose. Documentação oficial. Disponível em: https://docs.docker.com/compose/how-tos/startup-order/. Acesso em: 14 nov. 2026.',
        'OLLAMA. Docker. Documentação oficial. Disponível em: https://docs.ollama.com/docker. Acesso em: 14 nov. 2026.',
        'QWEN. Qwen2.5-Coder-3B-Instruct. Model card e licença Qwen Research. Disponível em: https://huggingface.co/Qwen/Qwen2.5-Coder-3B-Instruct. Acesso em: 14 nov. 2026.',
    ]:bibliografia.append(txt)
    for txt in sorted(bibliografia,key=lambda t:t.casefold()):p(txt,refs)
    elementos.append(PageBreak());titulo('APÊNDICE A - ROTEIRO E MATERIAIS DE REPRODUÇÃO')
    apendice=ParagraphStyle('Apendice',parent=corpo,alignment=0)
    for bloco in re.split(r'\n\s*\n',blocos_v3['Apêndice A'].strip()):p(' '.join(bloco.splitlines()),apendice)
    destino=args.saida.resolve()
    destino.parent.mkdir(parents=True,exist_ok=True)
    def pagina(canvas,doc):
        if doc.page>=getattr(doc,'primeira_textual',999):
            canvas.saveState();canvas.setFont('Times',10);canvas.setFillColor(colors.black)
            canvas.drawRightString(A4[0]-2*cm,A4[1]-2*cm,str(doc.page-1));canvas.restoreState()
    doc=Documento(str(destino),pagesize=A4,leftMargin=3*cm,rightMargin=2*cm,topMargin=3*cm,bottomMargin=2*cm,title='Cognitive Memory Agents - pesquisa v3',author='Equipe Cognitive Memory Agents')
    doc.addPageTemplates(PageTemplate(id='normal',frames=Frame(3*cm,2*cm,A4[0]-5*cm,A4[1]-5*cm,leftPadding=0,rightPadding=0,topPadding=0,bottomPadding=0),onPage=pagina))
    doc.multiBuild(elementos)
    import pymupdf
    pdf=pymupdf.open(destino)
    paginas=[p.get_text() for p in pdf]
    inicio=next(i for i,t in enumerate(paginas) if '1 INTRODUÇÃO' in t and 'SUMÁRIO' not in t)
    fim=next(i for i,t in enumerate(paginas) if i>inicio and ('\nREFERÊNCIAS\n' in t or t.startswith('REFERÊNCIAS')))
    revisao=args.render_dir.resolve();revisao.mkdir(parents=True,exist_ok=True)
    for i,pg in enumerate(pdf):pg.get_pixmap(matrix=pymupdf.Matrix(0.8,0.8)).save(revisao/f'pagina-{i+1:02}.png')
    metadados={'paginas_total':len(pdf),'paginas_textuais':fim-inicio,'primeira_textual':inicio+1,'primeira_referencias':fim+1,'status':'candidata_v3_consolidacao_20261121_para_revisao_humana','sha256':hashlib.sha256(destino.read_bytes()).hexdigest(),'fontes':{str(a.relative_to(ROOT)):hashlib.sha256(a.read_bytes()).hexdigest() for a in arquivos.values()}}
    metadados['fontes_atuais']={str(a.relative_to(ROOT)):hashlib.sha256(a.read_bytes()).hexdigest() for a in [ROOT/'docs/pesquisa-v3.md', ROOT/'docs/dados-academicos.json', ROOT/'docs/contribuicao-academica-zeck.md', ROOT/'docs/pesquisa-complemento.md', ROOT/'tools/gerar_pesquisa.py', ROOT/'evidencias/contexto-v3-20261118/p6-r01/resumo.json', ENTREGA3/'figuras/p6-v3.png', ENTREGA3/'figuras/validacao-v3.png']}
    fontes_consolidadas=[ROOT/'docs/consolidacao-testes-20261120.md', CONSOLIDACAO/'consolidado.json', CONSOLIDACAO/'inventario.json', CONSOLIDACAO/'qualidade-atual.json', CONSOLIDACAO/'recalcular.py', CONSOLIDACAO/'manifesto-sha256.json', CONSOLIDACAO/'medias-atuais.png']
    metadados['fontes_atuais'].update({str(a.relative_to(ROOT)):hashlib.sha256(a.read_bytes()).hexdigest() for a in fontes_consolidadas})
    metadados['relatorios_20261120']={d['pasta']:d['arquivo_sha256'] for d in json.loads((CONSOLIDACAO/'inventario.json').read_text(encoding='utf-8'))}
    fontes_adicionais=[ROOT/'docs/informacao-antiga-respostas.md', ROOT/'docs/openai-opcional.md', ROOT/'eval/informacao_antiga.py', ROOT/'evidencias/informacao-antiga-20261121/analises/resumo.json']
    metadados['fontes_atuais'].update({str(a.relative_to(ROOT)):hashlib.sha256(a.read_bytes()).hexdigest() for a in fontes_adicionais})
    fontes_fechamento=[ROOT/'docs/fechamento-avaliacao-20261121.md', ROOT/'docs/julgamento-p6.md', ROOT/'evidencias/fechamento-p6-20261121/consolidado.json', ROOT/'evidencias/fechamento-p6-20261121/manifesto-sha256.json', ROOT/'evidencias/fechamento-p6-20261121/recalcular.py']
    metadados['fontes_atuais'].update({str(a.relative_to(ROOT)):hashlib.sha256(a.read_bytes()).hexdigest() for a in fontes_fechamento})
    args.metadados.parent.mkdir(parents=True,exist_ok=True)
    args.metadados.write_text(json.dumps(metadados,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps(metadados,ensure_ascii=True))


if __name__=='__main__':main()
