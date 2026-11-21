# Proteção dos campos de entrada — conferência local

Foram conferidos os caminhos da conversa, consulta de memórias e importação de casos. O usuário fornece dados à API; não fornece instruções SQL ou acesso direto ao SQLite. A memória continua podendo persistir fatos da conversa pelo fluxo autorizado do agente.

## Controles existentes conferidos

- As operações de dados do repositório SQLite usam parâmetros, incluindo usuário, chave, texto e identificador. O esquema e as migrações são código fixo do projeto.
- A interface obtém o usuário da credencial autenticada e rejeita tentativas de informar outro usuário ou campos extras na conversa. A API mantém o isolamento por usuário.
- A importação lê JSON, valida campos, tipos, tamanho e protocolo. Campos extras para comandos, SQL, URLs de execução ou caminhos não são aceitos. Validar/importar não inicia avaliação.
- O painel cria texto com `textContent` e nós de texto; mensagens, respostas e perguntas importadas não são inseridas como HTML executável. A política de conteúdo restringe scripts ao próprio projeto.
- A execução de avaliação usa argumentos separados, caminho gerado pelo servidor e ambiente dedicado. Texto de caso não é um comando de terminal.

## Evidência e limites

Doze testes adicionais, com SQLite temporário e agente simulado, verificam tentativas de alterar consultas, preservar dados de outro perfil, campos extras e JSON inválido. Uma conferência em navegador descartável verificou que marcação com atributo de script aparece literalmente na conversa e na pergunta importada, sem criar elementos executáveis ou iniciar avaliação.

Digitar um trecho de código como exemplo não precisa ser proibido: ele deve permanecer texto. Uma lista de palavras proibidas não substitui consultas parametrizadas, autenticação e renderização segura. Nesta revisão não foi necessário alterar esses caminhos de produção.

A conferência não demonstra segurança universal nem resistência a toda instrução maliciosa dirigida ao LLM. Ações legítimas de guardar, atualizar e esquecer memórias continuam disponíveis no escopo do usuário autenticado. Os perfis de demonstração são compartilhados localmente; exposição pública exige configuração de identidade, transporte e revisão próprios.
