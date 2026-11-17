"""Confere destinos locais dos links Markdown dos documentos alterados."""
import json
import re
from pathlib import Path
from urllib.parse import unquote

ROOT=Path(__file__).resolve().parents[1]
arquivos=[ROOT/'README.md',ROOT/'PROMPTS.md',ROOT/'evidencias/README.md',*(ROOT/'docs').rglob('*.md')]
links=0;falhas=[]
for arquivo in arquivos:
    texto=re.sub(r'```.*?```','',arquivo.read_text(encoding='utf-8-sig'),flags=re.S)
    for destino in re.findall(r'!?\[[^\]]*\]\(([^)]+)\)',texto):
        if re.match(r'^(?:https?://|mailto:|plugin:)',destino):continue
        destino=destino.strip('<>')
        caminho,_,ancora=unquote(destino).partition('#')
        alvo=(arquivo.parent/caminho).resolve() if caminho else arquivo
        links+=1
        if not alvo.exists():
            falhas.append({'arquivo':str(arquivo.relative_to(ROOT)),'destino':destino,'erro':'destino_ausente'})
        elif ancora and alvo.suffix=='.md':
            titulos=re.findall(r'^#{1,6}\s+(.+)$',alvo.read_text(encoding='utf-8-sig'),re.M)
            ids=[re.sub(r'[^\w\- ]','',t.lower().replace('`','')).replace(' ','-') for t in titulos]
            if ancora not in ids:falhas.append({'arquivo':str(arquivo.relative_to(ROOT)),'destino':destino,'erro':'ancora_nao_localizada'})
resultado={'links_locais':links,'falhas':falhas}
print(json.dumps(resultado,ensure_ascii=True,indent=2))
raise SystemExit(bool(falhas))
