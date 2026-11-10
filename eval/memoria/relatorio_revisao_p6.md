# Relatório de revisão — Anotações P6

## Resultado da validação
- Usuários: 4
- Sessões: 20
- Perguntas previstas: 21
- Anotações presentes: 21
- Compatíveis: 10
- Incompatíveis: 11
- Ausentes: 0
- Cobertura compatível: 47,62%

## Dependência do julgador P4
O julgador atual aceita os atributos cidade, esporte, carro, nome e time.

As 11 incompatibilidades envolvem atributos ainda não suportados:
profissao, pet, filhos, disciplina, hobby, viagem,
quantidade_pets e instrumento.

Não foram alterados os atributos das anotações para forçar compatibilidade.

## Pendências de revisão
1. u02/s5/esquecer_chaves:
   depende da definição e aprovação do contrato para esquecimento por chave.

2. u03/s4/pergunta3:
   revisar a diferença entre o resultado esperado do dataset,
   que apresenta os nomes Luna e Simba, e a anotação,
   que espera a quantidade de gatos (dois).

## Limites da validação
Foi executada a verificação estrutural das anotações.
Não foram executadas sessões reais do chatbot.

Não foram modificados componentes do P4.
