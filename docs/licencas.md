# Licenças do projeto e de terceiros

## Código e documentação do grupo

O usuário confirmou nesta sessão, em 18/11/2026, a escolha da MIT e a autorização
do grupo para publicá-la. O texto integral está em [LICENSE](../LICENSE), com
autoria dos três integrantes registrados no README. A licença permite uso e
adaptação com preservação dos avisos; o software é fornecido sem garantias.
Referência do texto: [Open Source Initiative — MIT](https://opensource.org/license/mit).

A MIT do grupo não altera os direitos de dependências, modelos, fontes tipográficas
ou outros materiais de terceiros. Os termos aplicáveis a eles são preservados.

## Modelo usado na entrega

O modelo `qwen2.5-coder:3b` é obtido pelo Ollama. Os pesos não são incluídos no
Git, no PDF ou no pacote de código. A identificação efetiva dos ensaios está nos
arquivos de configuração das evidências.

A ficha oficial de **Qwen2.5-Coder-3B-Instruct** identifica a licença
**Qwen Research License Agreement**, distinta da MIT do projeto e da licença
do programa Ollama. O acordo define uso não comercial para pesquisa/avaliação;
uso comercial exige licença específica do titular. Portanto, não se deve
anunciar o modelo 3B como Apache-2.0 ou como autorizado para qualquer uso.

Se houver redistribuição dos materiais do modelo, observar as condições de
acompanhamento do acordo, preservação de avisos e identificação de modificações.
O aviso de atribuição foi registrado em [NOTICE](../NOTICE). O fluxo desta entrega
baixa o modelo diretamente da distribuição, em vez de publicar seus pesos.

Fontes primárias verificadas em 18/11/2026:

- [Ficha oficial do modelo](https://huggingface.co/Qwen/Qwen2.5-Coder-3B-Instruct).
- [Texto oficial da licença](https://huggingface.co/Qwen/Qwen2.5-Coder-3B-Instruct/blob/main/LICENSE).

## Dependências Python

O [inventário](../third_party/licenses/inventario-python.json) registra versão
fixada, versão instalada, declaração de licença e hash dos textos incluídos nas
distribuições locais. As cópias preservadas estão em `third_party/licenses/python/`.
São textos fornecidos pelos próprios pacotes; não foram substituídos pela MIT.

Principais grupos: FastAPI/Pydantic/Ollama SDK/pytest sob MIT; httpx, Starlette
e Uvicorn sob BSD; OpenAI SDK e OpenTelemetry sob Apache-2.0; certifi sob MPL-2.0;
typing_extensions sob PSF-2.0. Consultar o inventário e os textos para o escopo
exato de cada versão, incluindo condições de atribuição e redistribuição.

O inventário cobre `requirements.txt` e `requirements-dev.txt`; ferramentas
opcionais de elaboração de PDF/vídeo não são dependências do aplicativo. O
FFmpeg usado na gravação não é incluído no repositório, apenas o vídeo produzido.
Fontes Windows não são redistribuídas como arquivos de fonte pelo projeto.

Reprodução: `python -B -m tools.inventariar_licencas`, usando os ambientes locais
documentados no script. A inventariação registra os textos e termos conhecidos;
não constitui certificação jurídica de todos os usos futuros.
