# Falhas conhecidas do baseline por regras

Resultados medidos em `eval/avaliar_regras.py` (rodada única do conjunto de avaliação final, sem ajustar as regras depois):

| Conjunto | Exatidão por frase | Precisão | Revocação | F1 | Conversas (pontos corretos) |
|---|---|---|---|---|---|
| Desenvolvimento (149 frases, 6 conversas) | 100% | 100% | 100% | 100% | 17/17 |
| **Avaliação final (50 frases, 4 conversas)** | **62,0%** (31/50) | 89,3% | 58,1% | 70,4% | **9/13 (69,2%)** |

O desenvolvimento é 100% porque as regras foram escritas olhando esses casos. O número que representa o comportamento esperado é o da avaliação final. Ambos os conjuntos foram escritos pela mesma pessoa que escreveu as regras, o que favorece o resultado; o ideal é que colegas acrescentem casos ao conjunto final.

## Falhas por causa

**1. Verbos e construções não cobertos (a maior parte dos erros, perdem fatos).** Exemplos que retornam nenhuma decisão:
`Acabei de me mudar para Brasília.`, `Estou morando em Fortaleza desde março.`, `Atuo como dentista.`, `Estou trabalhando como professora agora.`, `Minha profissão atual é médica.`, `Comecei a praticar yoga.`, `Comprei um Corolla novo.`, `Sou torcedor do Vasco.`, `Adoro chocolate.`, `Todos me chamam de Duda.`, `Tenho um cachorro chamado Bob.`, `Eu tenho uma gata, a Nina.`

**2. Valor com complemento no fim (guarda o valor errado).** O valor vai até a pontuação, então:
`Eu trabalho como arquiteta há cinco anos.` -> `arquiteta há cinco anos`;
`Torço pelo Fluminense desde criança.` -> `Fluminense desde criança`;
`Moro em Osasco de novo.` -> `Osasco de novo`.
Consequência em conversas: o valor errado impede detectar repetição ("duplicado") e faz a negação seguinte (`Não torço mais pelo Fluminense.`) ser ignorada como conflito, deixando um fato que deveria ter sumido. Isto causou 4 dos 13 pontos de verificação errados.

**3. Término e negação não cobertos (fato que deveria ser apagado permanece).**
`Deixei de morar em Osasco.`, `Já não trabalho como enfermeira.`, `Não quero mais que você guarde meu carro.`

**4. Falsos positivos.**
`Se eu ganhar na loteria, moro em Paris.` (condicional vira cidade);
`Eu gosto de você.` (vira o gosto "você").

**5. Duas entidades ligadas por "e o/a".**
`Meu cachorro se chama Thor e o gato se chama Tom.` -> nenhuma decisão, porque o valor passa de 6 palavras e é descartado.

## Limitações de projeto

- Frases com `?` são ignoradas inteiras, inclusive `Moro em Osasco, certo?`.
- Só considera 1ª pessoa no presente; passado ("morava") é ignorado de propósito.
- `esporte`, `carro`, `time`, `profissao` e `cidade` aceitam um valor por vez: "Faço yoga e pilates" guarda só o primeiro.
- O índice chave -> ids do `GerenciadorMemoria` fica em RAM. Com uma memória persistente, será preciso listar as memórias do usuário por chave (ou guardar a chave nos metadados e consultá-la) para esquecer por tópico depois de reiniciar.
- Cobertura lexical em português; sem tratamento de gírias, erros de digitação ou outras línguas.

## Exemplos reproduzíveis

```python
from src.memoria.regras import extrair

extrair("Atuo como dentista.")                          # []
extrair("Torço pelo Fluminense desde criança.")         # valor: "Fluminense desde criança"
extrair("Se eu ganhar na loteria, moro em Paris.")      # salva cidade "Paris" (falso positivo)
extrair("Eu gosto de você.")                            # salva gosto "você" (falso positivo)
```

Conversa que reproduz a falha 2:

```python
from src.memoria import MemoriaEmRam
from src.memoria.gerenciador import GerenciadorMemoria

g = GerenciadorMemoria(MemoriaEmRam())
g.processar("u", "Torço pelo Fluminense desde criança.")
g.processar("u", "Não torço mais pelo Fluminense.")
g.estado("u")   # {'time': 'Fluminense desde criança'}  <- deveria estar vazio
```

Todos os casos que falham: `python eval/avaliar_regras.py --conjunto avaliacao --mostrar-falhas`.

## Próximos passos possíveis

Cobrir mais verbos e formas ("estou morando", "atuo como"), cortar o valor em marcadores temporais ("desde", "há", "de novo"), tratar condicionais ("se", "quando eu ganhar"), e comparar com um extrator baseado em IA usando os mesmos conjuntos, o que fecha a comparação do trabalho.
