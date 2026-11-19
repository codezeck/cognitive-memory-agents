# Roteiro da demonstração v3 — 4 minutos e 30 segundos

Vídeo pendente. Em 18/11 a ferramenta de controle da tela encerrou o acesso por não conseguir confirmar a URL do navegador no Windows. Nenhum vídeo oficial foi produzido. Este roteiro permite ao grupo gravar a execução real em tela inteira com o gravador de sua preferência.

Preparação: Docker Desktop aberto, projeto próprio, dados sintéticos e porta livre. Declarar imagens/pesos em cache; não apagar volumes existentes para simular instalação fria. Não mostrar `.env`, tokens ou cookies. Usar [manual](manual-professor.md) e [índice](../evidencias/entrega-v3-20261118/README.md). A identificação do commit entra no início da gravação; a tag final virá depois da revisão.

| Tempo | Ação visível e fala sugerida |
|---|---|
| 0:00–0:35 | Terminal em tela inteira: `docker compose --env-file .env.example -p cma-video up --build`. “Ollama, preparo e API locais. Imagens e pesos já estão em cache nesta demonstração.” Aguardar saúde real |
| 0:35–1:00 | Abrir `http://127.0.0.1:8001/`, perfil A. Mostrar modelo e acesso automático |
| 1:00–1:40 | Enviar `Moro em Niteroi.`; mostrar memória; Nova sessão; `Em qual cidade eu moro?`. Distinguir confirmação local de resposta gerada pelo modelo |
| 1:40–2:15 | `Agora moro em Sorocaba.`; Nova sessão; repetir pergunta. Conferir valor atual e memória utilizada |
| 2:15–2:55 | Executar `docker compose --env-file .env.example -p cma-video restart api`; atualizar página e perguntar cidade. Mostrar persistência após reinício do processo |
| 2:55–3:20 | Perfil B, perguntar cidade sem ter informado uma. Esperado: `DESCONHECIDO`, sem dados de A |
| 3:20–4:00 | Voltar A; `Esqueça minha cidade.`; Nova sessão; perguntar cidade. Depois `Qual e a capital da Franca?`, mostrando que perguntas gerais continuam no modelo |
| 4:00–4:30 | Mostrar índice/PDF. “P6: 21/21 aprovações da automática, 83,84% menos tokens nos 20 pares. São casos sintéticos; há limitações do julgador e da gramática. Revisão humana e CI na tag fecham a entrega.” |

Verificar as respostas antes de narrar sucesso. Se ocorrer falha, preservá-la e explicar. Assistir ao vídeo inteiro, conferir duração de 180–300 segundos, comandos legíveis, ausência de segredos e correspondência ao commit. Adicionar MP4, duração, SHA256, data/fuso e capturas ao índice. PNGs históricos não substituem o vídeo.
