"""Instrumentacao exclusiva do ensaio: encaminha integralmente ao SDK real."""
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import uvicorn
sys.path.insert(0, '/app')
from src.modelos.ollama_adapter import OllamaAdapter

destino = Path('/app/dados/chamadas-ollama.jsonl')
original = OllamaAdapter.gerar_com_detalhes


def registrar(evento):
    evento['instante_utc'] = datetime.now(timezone.utc).isoformat()
    evento['pid'] = os.getpid()
    with destino.open('a', encoding='utf-8') as arquivo:
        arquivo.write(json.dumps(evento, ensure_ascii=False) + '\n')


def observar(self, mensagens, options=None):
    registrar({'tipo': 'pedido_modelo', 'modelo': self.modelo,
               'options_explicitas': options, 'mensagens': mensagens})
    try:
        resultado = original(self, mensagens, options)
    except Exception as erro:
        registrar({'tipo': 'erro_modelo', 'classe': type(erro).__name__})
        raise
    registrar({'tipo': 'resposta_modelo', 'resultado': resultado})
    return resultado


OllamaAdapter.gerar_com_detalhes = observar
registrar({'tipo': 'inicio_observador', 'passagem_integral_sem_fallback': True,
           'sha256_agent': hashlib.sha256(Path('/app/src/agent.py').read_bytes()).hexdigest()})
uvicorn.run('src.api.main:app', host='0.0.0.0', port=8000, workers=1)
