# Roteiro de demonstração: 4 minutos e 30 segundos

Preparação de 14/11/2026, sem vídeo oficial gravado. Requer gravação em tela inteira, 3–5 minutos, versão revisada identificada e subida Docker visível. O chat agora está integrado em `/`; `/docs` permanece para inspeção técnica. [Manual](manual-professor.md), [matriz](andamento-entrega.md) e [limites experimentais](ensaio-desenvolvimento-20261114.md).

## Antes de gravar

Escolher projeto/porta próprios e dados sintéticos. Verificar Docker disponível, disco, áudio e legibilidade. Declarar se imagens/pesos já estão em cache e se houve aquecimento; primeiro download pode ultrapassar o tempo do vídeo. Não remover caches/volumes existentes para encenar instalação fria. Não exibir `.env`, credenciais, cookies, cabeçalhos ou `docker inspect` completo. A versão local atual não é uma tag publicada. O vídeo final deve corresponder à versão efetivamente revisada.

Ensaio e capturas reais já existem em `evidencias/entrega/20261114-entrega-ae9eb113/`, mas não são gravação oficial. Ajustar o ritmo e regravar se exceder cinco minutos, sem cortar falhas para inventar sucesso.

## Sequência

| Tempo | Ação visível | Narração e afirmação permitida |
|---|---|---|
| 0:00–0:35 | Terminal em tela inteira: `docker compose --env-file .env.example -p cma-video up --build` | “Execução local sem API paga. Ollama, preparação e API; pesos/credenciais persistentes. Cache declarado.” |
| 0:35–1:00 | Abrir `http://127.0.0.1:8001/`, mostrar perfil A e modelo | “A página usa API e modelo reais. O acesso local é preparado no servidor, sem copiar tokens.” |
| 1:00–1:40 | Enviar `Moro em Niteroi.`; ver memória; nova sessão; perguntar `Em qual cidade eu moro?` | “Nova sessão limpa a conversa transitória e preserva a memória persistente.” Mostrar resposta e memórias realmente retornadas. |
| 1:40–2:15 | Enviar `Agora moro em Sorocaba.`; nova sessão; repetir pergunta | “A residência atual deve mudar; o valor antigo não deve ser apresentado como atual.” Não narrar sucesso antes da resposta. |
| 2:15–2:55 | Terminal: `docker compose --env-file .env.example -p cma-video restart api`; atualizar chat e perguntar | “Reinício é troca do processo, diferente de nova sessão. Banco e identidade permanecem nos volumes.” |
| 2:55–3:25 | Selecionar B e perguntar cidade sem informar fato | “As memórias são separadas por identidade. Aqui se espera DESCONHECIDO.” |
| 3:25–4:05 | Retornar A; apagar tudo e confirmar; nova sessão; perguntar cidade; perguntar capital da França | “Exclusão total difere de excluir um ID. A forma pessoal ensaiada deve abster; conversa geral continua.” |
| 4:05–4:30 | Mostrar índice/relatório e limites | “SQLite e RAM delimitada têm evidências próprias. P6 depende de revisão. O comparativo de desenvolvimento aumentou tokens completos 6,72%; a meta global não foi atingida.” |

Se uma resposta falhar, preservar a execução e explicar o desvio. Não atribuir a uma busca vazia prova de banco ou RAM. O DELETE individual remove um ID e reinicia histórico, podendo conservar versões inativas; ele pode ser mostrado no ensaio técnico, sem obrigar inserir todas as operações no vídeo curto. A falha de autenticação pode ser demonstrada por acesso protegido sem cookie/token em ambiente próprio, se houver tempo, sem exposição de segredos.

## Conferência posterior

Assistir ao vídeo inteiro: tempo, tela inteira, comandos legíveis, fluxo real, falhas/limites honestos e nenhum segredo. Guardar arquivo, data/fuso, versão, logs e link no índice após publicação autorizada. Paloma revisa ambiente/contratos; Vinicius o significado de atualizar/esquecer; Zeck agente e interpretação das métricas. Nenhuma revisão foi registrada automaticamente por este roteiro.
