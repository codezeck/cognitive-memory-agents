# Evidências da parte de memória de longo prazo

Responsável: Vinicius. Gerado em **2026-11-04 19:00:55**, commit **9c5afd3**.

Todos os arquivos desta pasta foram produzidos pelo script `coletar_evidencias.ps1` a partir da execução real do projeto. Cada um traz no cabeçalho a data, o commit e o comando. Não foram editados à mão. Para regerar tudo, na raiz do repositório:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File evidencias\memoria\coletar_evidencias.ps1
```

## Índice: afirmação do trabalho, evidência e como conferir

| # | Afirmação | Evidência | Como conferir |
|---|---|---|---|
| 1 | A suíte de testes do projeto passa. | `01_testes_pytest.txt` | Última linha com o total; `python -m pytest -v` |
| 2 | A recuperação semântica acerta mais que a por palavras no benchmark de 20 sessões, sem devolver informação desatualizada. | `02_recuperacao_palavras_hash.txt`, `03_recuperacao_semantico.txt` e os `resultados_recuperacao_*.json` | `python eval/avaliar_memoria.py --embedder hash` e `--embedder semantico` |
| 3 | O baseline por regras guarda, atualiza e esquece fatos; o desempenho no conjunto de avaliação final é menor que no de desenvolvimento. | `04_regras_avaliacao_e_falhas.txt` e `resultados_regras.json` | `python eval/avaliar_regras.py --conjunto ambos --mostrar-falhas` |
| 4 | Fato antigo é substituído e fato apagado deixa de ser recuperado (nas memórias em RAM e em SQLite). | Testes `test_fato_substituido_e_apagado_nao_voltam_pela_busca`, `test_esquecer_usuario_conta_tudo_e_nao_afeta_outros` e `test_esquecer_por_topico_depois_de_reiniciar` em `01_testes_pytest.txt` e `05_contrato_depois_do_ajuste.txt` | `python -m pytest tests/test_contrato_memoria.py -v` |
| 5 | O ajuste do índice corrigiu cenários que falhavam: antes falhavam, depois passam. | `06_contrato_antes_do_ajuste.txt` (falhas) e `05_contrato_depois_do_ajuste.txt` (verde) | Compare os dois arquivos; o "antes" usa um worktree no commit anterior ao ajuste |
| 6 | O sistema erra em casos conhecidos, com causa analisada (evidência 6 do enunciado). | Lista de frases e conversas que falham em `04_regras_avaliacao_e_falhas.txt` e análise por causa em `docs/falhas-conhecidas-regras.md` | Rodar o comando da linha 3 e ler as falhas |
| 7 | Os integrantes contribuíram e os PRs foram revisados por outro membro. | `07_git_historico.txt` (commits e autores). A revisão dos PRs está nas páginas dos pull requests no GitHub | Ver o histórico no repositório |
| 8 | Ambiente de execução. | `08_ambiente.txt` | `python --version` e `pip freeze` |

## Resumo lido dos arquivos gerados (não digitado)

**Testes (`01_testes_pytest.txt`)**

```
tests/test_agent.py::test_responder_retorna_resposta_do_modelo PASSED    [  0%]
tests/test_agent.py::test_responder_mantem_historico PASSED              [  0%]
tests/test_agent.py::test_mensagem_vazia_nao_consulta_modelo PASSED      [  0%]
```

**Recuperação por palavras (`02_*`)**

```
# Comando: python eval/avaliar_memoria.py --embedder hash --saida evidencias/memoria/resultados_recuperacao_hash.json
Embedder: hash | k = 3 | perguntas: 21
Taxa de acerto geral:              71.4%
Lembranças corretas:               64.7%
Informação desatualizada devolvida: 0.0%
Esquecimento correto:              100.0%
Redução de tokens:                 74.5%
```

**Recuperação semântica (`03_*`)**

```
# Comando: python eval/avaliar_memoria.py --embedder semantico --saida evidencias/memoria/resultados_recuperacao_semantico.json
Embedder: semantico | k = 3 | perguntas: 21
Taxa de acerto geral:              100.0%
Lembranças corretas:               100.0%
Informação desatualizada devolvida: 0.0%
Esquecimento correto:              100.0%
Redução de tokens:                 55.9%
```

**Regras (`04_*`)**

```
# Comando: python eval/avaliar_regras.py --conjunto ambos --mostrar-falhas --saida evidencias/memoria/resultados_regras.json
=== Conjunto: dev ===
Frases: 149 | exatidão por frase: 100.0%
precisão 100.0% | revocação 100.0% | F1 100.0%
Conversas: 6 | pontos de verificação corretos: 17/17 (100.0%)
=== Conjunto: avaliacao ===
Frases: 50 | exatidão por frase: 62.0%
precisão 89.3% | revocação 58.1% | F1 70.4%
Conversas: 4 | pontos de verificação corretos: 9/13 (69.2%)
```

**Contrato da memória, depois do ajuste (`05_*`) e antes (`06_*`)**

```
depois: tests/test_contrato_memoria.py::test_implementa_a_interface[ram] PASSED  [  2%]
antes:  tests/test_contrato_memoria.py::test_implementa_a_interface[ram] PASSED  [  2%]
```

## Limites desta pasta

- Cobre só a parte de memória. O vídeo com `docker compose up`, o link da integração contínua na tag `v1.0`, os logs da API em execução completa e as capturas de tela são do grupo e não estão aqui.
- Os conjuntos de dados são sintéticos e pequenos; os números são preliminares.
- Os conjuntos de desenvolvimento e de avaliação das regras foram escritos pela mesma pessoa que escreveu as regras.
- Resultado ruim não é escondido: as falhas do baseline estão listadas no arquivo `04_*`.