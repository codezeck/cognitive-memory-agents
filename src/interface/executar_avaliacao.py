"""Processo da interface; reutiliza executores e nunca reaproveita resultados históricos."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from src.interface.protocolos import DATASET_V3, RAIZ, gravar_progresso, validar, validar_casos
from src.interface.preparo import FalhaPreparo, preparar_modelo


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--protocolo', choices=('comparativo_v3', 'p6'), required=True)
    parser.add_argument('--repeticoes', type=int, choices=(1, 3), default=1)
    parser.add_argument('--modelo', required=True)
    parser.add_argument('--saida', type=Path, required=True)
    parser.add_argument('--progresso', type=Path, required=True)
    parser.add_argument('--dataset-proprio', type=Path)
    parser.add_argument('--timeout-modelo', type=float, default=180)
    args = parser.parse_args(argv)
    dataset = args.dataset_proprio or RAIZ / DATASET_V3
    try:
        validar(args.protocolo, args.repeticoes)
        from eval.historico_processo import timeout_positivo
        timeout_positivo(args.timeout_modelo)
        if args.dataset_proprio and args.protocolo != 'comparativo_v3':
            raise ValueError('P6 não aceita conjunto genérico de casos.')
        casos = validar_casos(json.loads(dataset.read_text(encoding='utf-8'))) if args.protocolo == 'comparativo_v3' else None
        if args.protocolo == 'p6':
            from tools.reproduzir_p6 import preparar_protocolo
            # Reutiliza o congelamento antes de qualquer preparo do modelo.
            # O executor volta a conferir e grava seu protocolo junto à rodada.
            with tempfile.TemporaryDirectory(prefix='cma-p6-fontes-') as temporario:
                preparar_protocolo(Path(temporario) / 'protocolo.json')
    except (ValueError, OSError) as erro:
        parser.error(str(erro))
    if args.saida.exists():
        parser.error('Relatório já existe; escolha outra saída.')
    gravar_progresso(args.progresso, fase='Preparando API e banco temporários', concluidos=0,
                     previstos=len(casos) * 4 * args.repeticoes if casos else 40,
                     unidade='tentativas' if casos else 'sessões')
    try:
        preparo = preparar_modelo(args.modelo, args.progresso,
                                  previstos=len(casos) * 4 * args.repeticoes if casos else 40,
                                  unidade='tentativas' if casos else 'sessões')
    except FalhaPreparo as erro:
        diagnostico = {'etapa': 'preparo_modelo', 'codigo': erro.codigo, 'mensagem': str(erro),
                       'tentativas_iniciadas': 0}
        with args.saida.with_name('falha-preparo.json').open('x', encoding='utf-8') as f:
            json.dump(diagnostico, f, ensure_ascii=False)
        gravar_progresso(args.progresso, fase=str(erro), concluidos=0,
                         previstos=len(casos) * 4 * args.repeticoes if casos else 40,
                         unidade='tentativas' if casos else 'sessões')
        return 1
    revisao = os.getenv('CMA_COMMIT_BASE', '').strip()
    if not revisao:
        try:
            revisao = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=RAIZ,
                                              text=True, stderr=subprocess.DEVNULL).strip()
        except (OSError, subprocess.CalledProcessError):
            revisao = 'não informado; fontes identificadas pelos hashes desta execução'
    if args.protocolo == 'comparativo_v3':
        from src.interface import comparativo
        bruto = args.saida.with_name('comparativo.json')
        anterior = sys.argv
        try:
            sys.argv = ['comparativo', '--saida', str(bruto), '--dataset', str(dataset),
                        '--modelo', args.modelo, '--repeticoes', str(args.repeticoes),
                        '--progresso', str(args.progresso), '--controle-sem-memoria', 'modelo_direto', '--timeout-modelo', str(args.timeout_modelo)]
            codigo = comparativo.main()
        finally:
            sys.argv = anterior
        documento = json.loads(bruto.read_text(encoding='utf-8')) if bruto.is_file() else None
    else:
        from tools import reproduzir_p6
        pasta = args.saida.with_name('p6')
        codigo = reproduzir_p6.main(['--saida-dir', str(pasta), '--commit-base', revisao,
                                    '--modelo', args.modelo, '--progresso', str(args.progresso)])
        resumo = pasta / 'resumo.json'
        documento = json.loads(resumo.read_text(encoding='utf-8')) if resumo.is_file() else None
        eventos = pasta / 'eventos.jsonl'
        if eventos.is_file():
            registros = []
            for linha in eventos.read_text(encoding='utf-8').splitlines():
                try:
                    registros.append(json.loads(linha))
                except ValueError:
                    break
            documento = {**(documento or {'estado_orquestracao': 'incompleta'}),
                         'resultados': [r for r in registros if r.get('tipo') == 'resultado']}
            documento['evidencias_operacionais'] = {
                p.name: json.loads(p.read_text(encoding='utf-8')) for p in pasta.glob('*.json')
                if p.name not in {'resumo.json', 'configuracao.json'}}
    if documento is not None:
        documento['interface'] = {'protocolo': args.protocolo, 'repeticoes': args.repeticoes,
                                 'preparacao_modelo': preparo,
                                 'codigo_saida': codigo,
                                 'conjunto': 'próprio' if args.dataset_proprio else 'oficial',
                                 'casos': casos, 'modelo': args.modelo, 'commit_base': revisao,
                                 'origem': 'nova execução explícita; sem resultados históricos',
                                 'revisao_humana': 'não realizada nesta execução',
                                 'fontes_sha256': {str(p.relative_to(RAIZ)): hashlib.sha256(p.read_bytes()).hexdigest()
                                                  for pasta in ('src', 'eval', 'tools')
                                                  for p in sorted((RAIZ / pasta).rglob('*.py'))},
                                 'dataset_sha256': hashlib.sha256((dataset if casos else RAIZ / 'eval/memoria/sessoes.json').read_bytes()).hexdigest()}
        if args.protocolo == 'comparativo_v3':
            from src.interface.controle_modelo import VERSAO
            documento['interface'].update(controle_sem_memoria='modelo_direto', versao_metodo_comparativo=VERSAO, limites_execucao=documento.get('limites_execucao'))
        if args.protocolo == 'p6':
            documento['interface']['anotacoes'] = json.loads((RAIZ / 'eval/memoria/anotacoes_p6.json').read_text(encoding='utf-8'))
        documento.setdefault('gerado_em', datetime.now(timezone.utc).isoformat())
        with args.saida.open('x', encoding='utf-8') as f:
            json.dump(documento, f, ensure_ascii=False, allow_nan=False)
    return codigo


if __name__ == '__main__':
    raise SystemExit(main())
