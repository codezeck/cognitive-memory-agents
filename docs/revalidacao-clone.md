# Revalidar uma cópia nova antes da entrega

## Conferência executada em 22/11

O [pacote de fechamento](../evidencias/fechamento-entrega-20261122/README.md) registra uma instalação isolada com fontes equivalentes à master/PR #46, volumes novos de banco/credenciais/modelo e 19 verificações HTTP aprovadas. Imagens e dependências puderam usar cache; o código da aplicação não foi alterado nesta etapa. A gravação do usuário mostra também clone novo e o SHA da versão da PR #45. Uma verificação posterior de qualquer mudança funcional ainda precisa identificar as novas fontes; isso não foi antecipado como CI de uma tag futura. O procedimento abaixo foi escrito antes dessa conferência e continua como roteiro para novas instalações.

Registro de preparação de 21/11: o procedimento abaixo aguardava execução para as últimas alterações. A conferência executada em 22/11 está identificada acima; o aceite funcional anterior e o novo percurso permanecem evidências distintas.

1. Conferir os resultados da rodada final, incluindo perguntas, conteúdo, formato, inconclusivos e cobertura de tokens. Guardar os relatórios necessários.
2. Revisar e publicar as alterações e a documentação. Confirmar que o commit existe no GitHub e que os testes da revisão correspondente passaram. Publicar uma branch não equivale a integrar o PR ou criar a tag final.
3. Clonar a branch publicada em outra pasta e conferir o commit. Preservar a cópia anterior até concluir a conferência, principalmente se contiver arquivos ainda não publicados.
4. Usar outro nome de projeto Docker e uma porta livre. Os volumes de dados, credenciais e modelos são separados pelo projeto; clonar em pasta nova usando o mesmo projeto pode reutilizar o ambiente antigo. O comando abaixo é um exemplo para um nome ainda não utilizado e uma porta livre:

```powershell
.\Iniciar.ps1 -Projeto cma-revalidacao -Porta 8003
```

5. Conferir preparação, saúde, conversa, nova sessão, atualização, isolamento entre perfis, exclusão e recuperação após reinício. Verificar o relatório P6 e o comparativo sintético separadamente. Testes automatizados com banco temporário não substituem esse ensaio de implantação.
6. Registrar a revisão e os resultados reais. As imagens podem usar cache mesmo com volumes novos; declarar o que foi reaproveitado. Só então remover os ambientes antigos identificados como sendo deste projeto. Não usar limpeza global do Docker nem remover dados de outros projetos.

Os relatórios ficam no volume da instalação, não são enviados automaticamente ao GitHub e não acompanham um clone novo. Remover a pasta do clone também não remove automaticamente contêineres ou volumes. Bancos, credenciais e registros necessários devem ter destino definido antes de qualquer exclusão de volumes.

Após a nova rodada, revisar a pesquisa e o PDF quanto ao método atual da P6. Manter resultados históricos com suas versões originais, sem substituir suas taxas pelas notas da análise adicional nem misturar nova rodada com médias de outro protocolo.
