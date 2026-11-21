# Informação antiga — análise adicional em 21/11/2026

Esta pasta contém derivados dos 14 relatórios preservados em [consolidação de 20/11](../consolidacao-interface-20261120/README.md), sem reescrever originais, P4/P5 ou tokens. A métrica tem cobertura literal e gramatical limitada; não é revisão humana automática.

- [Contrato, exemplos e denominadores](../../docs/informacao-antiga-respostas.md).
- `analises/`: derivado por relatório, mais `resumo.json`, inclusive P6 e rodadas parciais.
- `fontes-originais.json`: SHA256 dos originais, conferidos antes e depois.
- `conferir.py`: recalcula cada derivado offline a partir dos originais, verifica igualdade e hashes; não usa rede ou LLM.
- `testes-python.xml`: 1.092 aprovados, 67 opcionais ignorados; `testes-node.log`: 51 aprovados.
- `manifesto-sha256.json`: hashes desta pasta, exceto o próprio manifesto.

Na última personalizada, automática e histórico tiveram 0/15 retornos antigos indevidos; pré-carregada, 0/13 verificadas e duas inconclusivas. Na P6 completa posterior de 20/11, histórico 1/9, automática 0/9. Não transformar zero de desatualização em acerto factual, misturar denominadores ou ocultar cobertura.

Novos relatórios incluem a análise; a leitura do histórico e a importação a calculam separadamente. Os downloads brutos antigos permanecem intactos. A decisão por Ollama local e o faturamento separado da API OpenAI estão documentados no [material de provedor](../../docs/openai-opcional.md#escolha-de-provedor-para-a-entrega).
