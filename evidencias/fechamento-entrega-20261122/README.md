# Conferência de fechamento — 22/11/2026

Este pacote complementa as evidências de 18–21/11. Não substitui os brutos experimentais nem representa revisão humana, tag ou envio ao professor.

## Vídeo da demonstração

[Assistir ou baixar o MP4](demonstracao.mp4): **4 min 59,75 s**, 1920 × 1080, 60 quadros/s, áudio estéreo. A gravação foi feita pelo usuário em 22/11 e confirmada como definitiva. O terminal mostra o commit `38e34e2bf375757f419a25d86676bc37f39caa6c`; a árvore dessa versão foi integrada à `master` pela PR #45. A preparação, o chat, as memórias e os relatórios aparecem na tela inteira.

Foram removidas somente pausas na abertura e no encerramento, preservando os intervalos originais 1,20–2,45 s e 2,85–301,35 s. Não houve aceleração, recorte da tela ou alteração dos resultados. O original permanece preservado pelo usuário. [Hashes, duração e descrição da edição](video-proveniencia.json). A cópia publicada foi decodificada integralmente sem erro; a equipe ainda deve revisar a demonstração antes do envio. O vídeo não substitui o CI da tag.

## Instalação isolada e percurso real

Fontes da aplicação iguais às integradas na `master`; referência documental inicial da PR #46: `bb3c659b5a01af19ccf677fb69ad732510c47895`. Foram usados projeto `cma-fechamento-20261122`, porta `18022` e volumes novos de banco, credenciais e modelo. Imagens e camadas de dependências puderam usar cache; os pesos foram preparados no novo volume. O serviço habitual do usuário não foi reiniciado nem teve seus volumes removidos.

[Registro do ambiente](instalacao.json), [log do preparo](preparo.log), [percurso HTTP com data/hora e dados fictícios](percurso-http.jsonl) e [resumo](percurso-resumo.json): **19 verificações aprovadas, nenhuma falha**. Inclui extração, nova sessão, recuperação por modelo real, atualização, reinício da API, persistência, isolamento, esquecimento e pergunta geral. Não é uma nova P6 nem uma medição de qualidade em larga escala. Não houve captura visual nova do percurso automatizado.

Para repetir em outro ambiente isolado, conferir antes que o nome/porta não pertencem a uma instalação a preservar. Na raiz do checkout desta PR:

```powershell
$env:CMA_PORT='18022'
docker compose --env-file .env.example -p cma-fechamento-20261122 up -d --build
python -B evidencias/fechamento-entrega-20261122/verificar-percurso.py
```

O script exige `httpx`, já incluído nas dependências do projeto, e cria os arquivos de saída sem sobrescrever registros existentes. Para outra execução, usar uma cópia do script em nova pasta e alterar projeto/porta de forma explícita.

## Conferência offline e correção

O manifesto da P6 de 21/11 exigia `__pycache__/recalcular.cpython-313.pyc`, um cache que não é distribuído pelo Git. A exigência foi removida; relatórios, julgamentos, tokens e demais hashes foram preservados. A conferência agora passa sem esse cache e os comandos abaixo foram acrescentados ao CI para evitar regressão em checkout limpo:

```powershell
python -B evidencias/fechamento-p6-20261121/recalcular.py
python -B evidencias/consolidacao-interface-20261120/recalcular.py
python -B evidencias/informacao-antiga-20261121/conferir.py
```

Conferidos: cinco P6/cem pares; 14 relatórios com consumos e médias; 14 análises adicionais com originais e hashes. Nenhum modelo foi chamado por esses comandos. [Manifesto deste pacote](manifesto-sha256.json).

## Fechamento que continua pendente

Aprovação humana da [PR #46](https://github.com/codezeck/cognitive-memory-agents/pull/46), revisão coletiva da pesquisa/referências e das interpretações dos históricos, parecer complementar do baseline quando utilizado, integração revisada, tag `v1.0`, CI verde e captura da tag, apresentação/defesa e envio no canal do professor. A publicação desta atualização não equivale a esses atos.
