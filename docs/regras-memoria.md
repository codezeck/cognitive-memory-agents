# Regras de memória (baseline sem IA)

Responsável: Vinicius. Código: `src/memoria/regras.py` e `src/memoria/gerenciador.py`.

## Objetivo

Decidir, a partir do texto de uma mensagem do usuário, o que a memória de longo prazo deve **guardar**, **atualizar** ou **esquecer**, sem usar modelo de linguagem. Serve de baseline para comparar com abordagens baseadas em IA e deixa o comportamento fácil de explicar e de testar.

## Fluxo

```
mensagem -> extrair() -> [Decisao, ...] -> GerenciadorMemoria.processar() -> MemoriaLongoPrazo
```

`extrair` só olha a mensagem. `GerenciadorMemoria` aplica as decisões usando a interface `MemoriaLongoPrazo` (`salvar`, `esquecer`, `esquecer_usuario`) e guarda um índice chave -> ids para poder esquecer por tópico.

## Decisões possíveis

| Ação | Quando | Exemplo |
|---|---|---|
| `salvar` | afirmação em 1ª pessoa que combina com uma regra | "Moro em Osasco." |
| `esquecer` | pedido para esquecer um tópico, ou negação de um fato | "Esqueça meu carro." / "Não moro mais em Osasco." |
| `apagar_usuario` | pedido para apagar tudo | "Esqueça tudo sobre mim." |
| (nenhuma) | pergunta, 3ª pessoa, passado, saudação | "Onde eu moro?" / "Minha mãe mora em Recife." |

Cada fato tem uma **chave** (`cidade`, `profissao`, `nome`, `filhos`, `time`, `esporte`, `carro`, `viagem`, `apelido`, `pet:<espécie>:<nome>`, `favorito:<categoria>`, `gosto:<coisa>`). A chave decide quando um fato substitui outro.

## Política de conflitos e atualização

1. Mesma chave com **valor diferente** substitui o fato antigo; a busca só devolve o novo.
2. Mesma chave com o **mesmo valor** (ignorando acento e maiúsculas) não duplica.
3. "Não moro mais em X" só apaga a cidade se o valor atual for X. Se a pessoa já se mudou, o fato novo é preservado.
4. Esquecer um tópico apaga também o **histórico substituído** daquela chave (não fica cópia escondida).
5. Em uma mesma mensagem, a afirmação que aparece **por último** vence.
6. Apagar o usuário remove tudo dele e não afeta os outros usuários.

## Dados

| Arquivo | Uso |
|---|---|
| `eval/memoria/regras/casos_dev.json` | frases usadas para **desenvolver** as regras (149) |
| `eval/memoria/regras/conversas_dev.json` | conversas de desenvolvimento (6) |
| `eval/memoria/regras/casos_avaliacao.json` | frases de **avaliação final** (50) |
| `eval/memoria/regras/conversas_avaliacao.json` | conversas de avaliação final (4) |
| `eval/memoria/sessoes.json` | benchmark de recuperação (embeddings), outro propósito |

Todos os dados são sintéticos, sem dados pessoais. As regras **não devem ser ajustadas olhando os resultados da avaliação final**. O teste `tests/test_separacao_dados.py` garante que nenhuma frase aparece nos dois conjuntos.

## Como rodar

```powershell
python -m pytest -v
python eval/avaliar_regras.py                         # desenvolvimento
python eval/avaliar_regras.py --conjunto avaliacao --mostrar-falhas
```

## Contrato com o agente

O agente já aceita `memorias=[{"texto": ...}]`. Fluxo para a integração:

```python
gerenciador.processar(usuario_id, mensagem)                # atualiza a memória
memorias = memoria.buscar(usuario_id, mensagem, k=3)       # recupera o contexto
resposta = agent.responder(mensagem, usuario_id, memorias=memorias)
```

Quem chama (API) decide a ordem; as falhas conhecidas estão em `docs/falhas-conhecidas-regras.md`.
