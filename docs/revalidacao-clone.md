# Revalidar uma cópia nova antes da entrega

Este procedimento está preparado, mas ainda não foi executado para as alterações locais posteriores de 21/11. As rodadas foram concluídas e aceitas pelo usuário no escopo testado. O ensaio deste clone novo ainda será realizado, sem presumir que o aceite funcional o substitua.

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
