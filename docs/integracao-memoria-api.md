# Integração das regras de memória com a API

Proposta para o grupo revisar. Nada aqui altera `src/api/` ou `src/armazenamento/`: são trechos para aplicar depois da aprovação.

## Situação atual

- `Conversador.conversar` só faz `buscar` e chama o agente. **Nada grava memórias a partir da conversa.** Memórias só entram por `POST /usuarios/{id}/memorias`.
- Quatro caminhos mexem na memória: `POST /conversas` (lê), `POST /usuarios/{id}/memorias`, `DELETE /usuarios/{id}/memorias/{id}` e `DELETE /usuarios/{id}/memorias` (via `Conversador.esquecer_usuario`).

## Proposta (três mudanças pequenas)

1. `get_memoria` devolve `MemoriaSQLiteComChaves`: a mesma `MemoriaSQLite`, com os métodos `listar` e `esquecer_por_chave`. A classe original não muda.
2. `Conversador` recebe um `gerenciador` opcional e chama `processar` **antes** de `buscar`.
3. `get_conversador` cria o `GerenciadorMemoria`. Ele não guarda estado, então criá-lo a cada requisição é barato e seguro.

```python
# src/api/dependencias.py
@lru_cache
def get_memoria():
    from src.memoria.sqlite_chaves import MemoriaSQLiteComChaves
    return MemoriaSQLiteComChaves()


def get_conversador(agente=Depends(get_agente),
                    memoria=Depends(get_memoria)) -> Conversador:
    from src.memoria.gerenciador import GerenciadorMemoria
    return Conversador(agente, memoria, gerenciador=GerenciadorMemoria(memoria))
```

```python
# src/api/servico.py
class Conversador:
    def __init__(self, agente, memoria, k: int = 5, gerenciador=None):
        self.agente = agente
        self.memoria = memoria
        self.k = k
        self.gerenciador = gerenciador

    def conversar(self, usuario_id, mensagem, selecao):
        if self.gerenciador is not None:
            self.gerenciador.processar(usuario_id, mensagem)  # guarda, atualiza ou esquece
        memorias = self.memoria.buscar(usuario_id, mensagem, self.k)
        ...
```

## O que muda no comportamento

- "Moro em Osasco" passa a ser guardado sozinho; "Mudei para Campinas" substitui; "Esqueça meu carro" apaga (inclusive o histórico substituído).
- Como `processar` roda antes de `buscar`, um pedido de esquecer já vale na mesma resposta.
- Os endpoints manuais continuam funcionando: uma memória criada à mão com `chave` é substituída pelas regras, e `DELETE /usuarios/{id}/memorias` não deixa estado velho (`tests/test_contrato_memoria.py` cobre isso nas duas implementações).
- A conversa passa a **gerar memórias automaticamente**. Vale deixar isso claro no README e manter os endpoints de esquecer (LGPD).

## Testes sugeridos para `tests/test_api.py`

- `POST /conversas` com "Moro em Osasco." e depois `GET /usuarios/{id}/memorias?consulta=Mora em Osasco` devolve a memória.
- `POST /conversas` com "Mudei para Campinas." depois de Osasco: a consulta só devolve Campinas.
- `POST /conversas` com "Esqueça meu endereço.": a consulta não devolve nada.

## Fora desta proposta (decisões do grupo)

- **Embedder semântico.** A API usa `EmbedderHash`. O semântico (`src/memoria/embeddings_semantico.py`) precisa de `requirements-memoria.txt` e baixa um modelo na primeira execução. O Dockerfile usa Python 3.13 e instala só o `requirements.txt`; não foi testado se o `fastembed` instala lá. **Atenção:** `MemoriaSQLite.buscar` ignora em silêncio vetores de dimensão diferente, então trocar o embedder exige reindexar as memórias existentes.
- **Limiar de similaridade.** `buscar` devolve sempre os k mais parecidos; com o embedder semântico isso traz memórias pouco relacionadas e aumenta os tokens.
