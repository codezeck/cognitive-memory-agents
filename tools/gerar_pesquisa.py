"""Gera rascunho ABNT e figuras a partir de textos e resultados preservados."""
from __future__ import annotations

import hashlib
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
    autores=academicos['integrantes']
    p(academicos['instituicao'].upper(),centro)
    p('PROJETO INTEGRADOR',centro);p('EAD_PROINT_100.DD-ADS-PI-10-74.2026.74',centro)
    elementos.append(Spacer(1,2*cm))
    for autor in autores:p(autor,centro)
    elementos.append(Spacer(1,3*cm))
    p('COGNITIVE MEMORY AGENTS',ParagraphStyle('Titulo',parent=centro,fontName='TimesBold',fontSize=16,leading=22))
    p('Memória contextual, abstenção e avaliação de um agente local',centro)
    elementos.append(Spacer(1,3*cm));p('Versão candidata v3 para revisão',centro);p('18 de novembro de 2026',centro)
    elementos.append(PageBreak())
    p('COGNITIVE MEMORY AGENTS',centro)
    elementos.append(Spacer(1,3*cm))
    p('Trabalho preparatório do Projeto Integrador sobre o Tema 11: memória de longo prazo para agentes. Consolida a contribuição de agente e avaliação com evidências operacionais da versão local. Não constitui submissão final.',corpo)
    p('Grupo com três integrantes, composição validada pelo usuário em 18/11/2026. Instituição registrada conforme informada: '+academicos['instituicao']+'. Cidade e nome do professor foram omitidos por orientação expressa do usuário.',corpo)
    p('Esta versão incorpora a avaliação v3, o inventário de evidências e a licença MIT autorizada pelo grupo. A P6 teve 21 respostas aprovadas da memória automática e redução de 83,84% dos tokens completos nos vinte pares medidos. A revisão humana e os registros finais de publicação são verificados separadamente no checklist.',corpo)
    elementos.append(PageBreak());titulo('RESUMO')
    p('Este trabalho apresenta um agente conversacional com memória persistente por usuário, API, SQLite e Ollama. O objetivo é avaliar continuidade, atualização, esquecimento e custo em tokens, distinguindo geração de linguagem e evidências de armazenamento. A versão v3 confirma localmente operações inteiramente reconhecidas e usa contexto breve em consultas pessoais com suporte, mantendo o modelo nas respostas factuais e gerais. Na avaliação P6, vinte sessões por cenário produziram 42 respostas sem falhas técnicas. A memória automática teve 21 respostas aprovadas pelo P4; no histórico completo, oito foram aprovadas e doze ficaram sem julgamento conclusivo. O custo completo foi de 3.593 e 22.228 tokens, respectivamente, redução de 83,84% nos vinte pares medidos. Dezenove checkpoints de persistência após reinício e dois de exclusão foram verificados; a consistência de estado vazio foi analisada separadamente. Uma bateria sintética de dezesseis casos com três repetições teve 48 aprovações na memória automática e 36 no baseline, incluindo um timeout deste; a economia foi 84,88% nos 47 pares medidos. Os resultados anteriores negativos foram preservados. O estudo não é cego ou independente, não isola causalmente cada alteração e não comprova equivalência estatística, generalização irrestrita ou conformidade jurídica.')
    p('Palavras-chave: agentes de linguagem; memória contextual; avaliação; esquecimento; reprodutibilidade.',refs)
    elementos.append(PageBreak());titulo('ABSTRACT')
    p('This study presents a conversational agent with per-user persistent memory, an API, SQLite and Ollama. The evaluation examines continuity, updates, forgetting and token cost while distinguishing language generation from storage evidence. Version v3 confirms fully recognized memory operations locally and uses brief context for supported personal queries; factual and general answers still use the model. The P6 evaluation completed twenty sessions per scenario and collected 42 answers without technical failures. Automatic memory received 21 P4 approvals; full history received eight approvals and twelve unresolved judgments. Full-session token totals were 3,593 and 22,228 respectively, an 83.84 percent reduction across all twenty measured pairs. Nineteen nonempty persistence checkpoints after restarts and two deletion checkpoints passed; empty-state consistency was assessed separately. Sixteen synthetic cases with three repetitions yielded 48 approvals for automatic memory and 36 for the baseline, which had one timeout. Token savings were 84.88 percent across the 47 measured pairs. Earlier negative results were preserved. The study is neither blind nor independent, does not isolate individual causal effects, and does not establish statistical equivalence, unrestricted generalization or legal compliance.')
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
    for n,nome in [(2,'1 INTRODUÇÃO'),(3,'2 REFERENCIAL TEÓRICO'),(4,'3 METODOLOGIA')]:
        if n>2:elementos.append(PageBreak())
        titulo(nome);markdown(secoes[n])
    p('3.1 Protocolo e métricas',sub);markdown(secoes[5])
    p('Os textos preparatórios a seguir registram a metodologia em 14/11. As pendências de execução mencionadas nesse registro foram tratadas pela decisão local de 18/11; a execução e os limites atuais constam da subseção 4.3. Não se atribui aprovação humana aos colegas.')
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
    elementos.append(KeepTogether([Paragraph('Figura 2 - Comparativo exploratório atual de desenvolvimento',figura),Image(str(FIG/'desenvolvimento.png'),width=15.5*cm,height=5.74*cm),Paragraph('Fonte: comparativo-desenvolvimento.json; P4-v3, P5-v1 e p3-uso-local-v1. Três repetições não são casos independentes.',legenda)]))
    dados=json.loads(arquivos['desenvolvimento'].read_text(encoding='utf-8'))
    celula=ParagraphStyle('Celula',parent=legenda,fontSize=10,leading=12,spaceAfter=0)
    linhas=[['Cenário','Conteúdo','Tokens da sessão','Cobertura']]
    for nome,c in zip(nomes,cenarios):
        s=dados['resumo'][c];linhas.append([nome,f"{s['aprovados']}/21",str(s['tokens_total']),'21/21'])
    tab=Table([[Paragraph(limpo(v),celula) for v in row] for row in linhas],colWidths=[5*cm,3*cm,4.5*cm,3.5*cm],repeatRows=1)
    tab.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#e2e9e6')),('LINEBELOW',(0,0),(-1,0),0.6,colors.black),('LINEBELOW',(0,-1),(-1,-1),0.6,colors.black),('VALIGN',(0,0),(-1,-1),'TOP'),('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7)]))
    elementos.append(KeepTogether([Paragraph('Tabela 1 - Conteúdo e uso no desenvolvimento atual',tabela),tab,Spacer(1,6),Paragraph('Fonte: resumo bruto, sem novo julgamento; sessão inclui ingestão e pergunta final. Pré-carregada não mede aquisição.',legenda)]))
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
    p('4.4 Análise de erros e validade',sub)
    markdown(blocos_v3['Erros e alcance'])
    elementos.append(PageBreak())
    titulo('5 CONSIDERAÇÕES FINAIS')
    markdown(blocos_v3['Conclusão v3'])
    elementos.append(PageBreak());titulo('REFERÊNCIAS')
    referencias=secoes[8]
    for linha in referencias.splitlines():
        if re.match(r'^\d+\. ',linha):
            texto=re.sub(r'\[([^]]+)\]\(([^)]+)\)',r'\2',linha)
            p(re.sub(r'^\d+\. ','',texto),refs)
    for txt in [
        'DOCKER. Control startup and shutdown order in Compose. Documentação oficial. Disponível em: https://docs.docker.com/compose/how-tos/startup-order/. Acesso em: 14 nov. 2026.',
        'OLLAMA. Docker. Documentação oficial. Disponível em: https://docs.ollama.com/docker. Acesso em: 14 nov. 2026.',
        'QWEN. Qwen2.5-Coder-3B-Instruct. Model card e licença Qwen Research. Disponível em: https://huggingface.co/Qwen/Qwen2.5-Coder-3B-Instruct. Acesso em: 14 nov. 2026.',
    ]:p(txt,refs)
    destino=ROOT/'docs/pesquisa-abnt.pdf'
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
    revisao=ROOT/'.env.pdf-revisao-v3-final';revisao.mkdir(exist_ok=True)
    for i,pg in enumerate(pdf):pg.get_pixmap(matrix=pymupdf.Matrix(0.8,0.8)).save(revisao/f'pagina-{i+1:02}.png')
    metadados={'paginas_total':len(pdf),'paginas_textuais':fim-inicio,'primeira_textual':inicio+1,'primeira_referencias':fim+1,'status':'candidata_v3_para_revisao_humana','sha256':hashlib.sha256(destino.read_bytes()).hexdigest(),'fontes':{str(a.relative_to(ROOT)):hashlib.sha256(a.read_bytes()).hexdigest() for a in arquivos.values()}}
    metadados['fontes_atuais']={str(a.relative_to(ROOT)):hashlib.sha256(a.read_bytes()).hexdigest() for a in [ROOT/'docs/pesquisa-v3.md', ROOT/'docs/dados-academicos.json', ROOT/'evidencias/contexto-v3-20261118/p6-r01/resumo.json', ENTREGA3/'figuras/p6-v3.png', ENTREGA3/'figuras/validacao-v3.png']}
    (ENTREGA3/'pesquisa-geracao.json').write_text(json.dumps(metadados,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(metadados,ensure_ascii=True))


if __name__=='__main__':main()
