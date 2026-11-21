# Consolidação da interface — 20/11/2026

14 relatórios sintéticos do perfil Professor desta instalação, copiados byte a byte; não incluem cookies ou arquivos de credenciais. Não é inventário de todos os computadores ou perfis. Os originais do Docker e os históricos do repositório foram preservados.

- [Análise e médias](../../docs/consolidacao-testes-20261120.md).
- [Inventário com hashes e medição por cenário](inventario.json); [consolidados por versão/conjunto](consolidado.json).
- [Tabela de todas as rodadas e cenários](rodadas-por-cenario.csv), delimitador ponto e vírgula; números decimais usam ponto.
- [Relatórios brutos](relatorios/), incluindo falhas e controles locais antigos; [qualidade atual](qualidade-atual.json).
- [Conjunto personalizado compatível](conjunto-personalizado-20.json), 15 casos factuais e cinco de abstenção; [revisão do original](revisao-conjunto-original.json). Seleção com ajuda de IA, não teste cego independente.
- `recalcular.py`: leitura local, sem rede, Docker ou modelo; verifica hashes, qualidade e médias diretamente dos brutos.
- `coleta-historico-local.py`: registro do procedimento usado para extrair o inventário. Depende do contêiner local e não é necessário para o recálculo offline. Não executa avaliações.
- `manifesto-sha256.json`: hashes das evidências desta pasta, exceto o próprio manifesto.
- `medias-atuais.png`: figura derivada dos consolidados, sem alterar imagens históricas.

Critério principal: quatro cenários completos, pares únicos completos e nenhuma falha técnica; não excluir reprovação semântica. Uma rodada sintética parcial e uma P6 parcial ficam fora dos consolidados completos e permanecem descritas. P6 usa sessão, comparativo usa tentativa do episódio inteiro. Os zeros dos controles legados não são medição de Ollama direto.

84,80% descreve o histórico oficial de várias versões; 84,91% a rodada oficial atual; 74,13% as duas rodadas personalizadas atuais. Não publicar como economia universal nem equivalência estatística. Aprovação funcional pelo usuário não equivale à revisão humana da pesquisa, PR ou entrega institucional.
