# TAL v1.3 — Tool Calling (experimental)

Este incremento é aditivo: `tal explain`, `tal chat`, relatórios e `.env` continuam intactos. O novo comando `python -m tal.agent` permite comparar o agente com o comportamento anterior.

## Requisitos

- TAL v1.2 (Vision), dependências já instaladas e Stockfish configurado.
- llama-server com Qwen3.5 4B, tool calling nativo e thinking desativado; alias e URL já configurados no `.env`.
- `LLM_MAX_TOKENS=512`, `LLM_TEMPERATURE=0.2` são sugestões; `LLM_TIMEOUT=180`.
- Contexto de 4096 tokens pode ser suficiente para poucas chamadas; se houver erro de contexto, tente `--max-calls 2` ou `-c 8192` no servidor se couber na GPU. Os schemas e retornos também consomem contexto.

## Teste controlado

```bash
python -m unittest discover -s tests -v
python -m tal.agent --report data/reports/cpato-20261124T193623799365Z.json --move 4 --color black --question 'Consulte inspect_square na posição antes do lance. Qual peça está em c4?' --max-calls 1 --trace
```

O agente precisa produzir pelo menos um resultado de ferramenta válido. O rastreamento deve exibir `[TOOL]` e `bispo (brancas)`. Se o modelo não chamar ferramentas ou responder vazio, o comando termina com erro explícito.

## Consulta ao Stockfish

```bash
python -m tal.agent --report data/reports/cpato-20261124T193623799365Z.json --move 4 --color black --question 'Use compare_moves para comparar Nf6 e dxc4 e explique a captura e a avaliação.' --depth 14 --max-calls 2 --trace
```

As avaliações de consultas dinâmicas podem diferir do relatório devido à profundidade, ao contexto de busca e ao histórico. `compare_moves` avalia as posições após cada alternativa com a mesma perspectiva do jogador do lance selecionado. Não compara cp com mate. O mate informado corresponde à posição consultada, não necessariamente à posição original.

## Benchmark

```bash
mkdir -p data/benchmarks
for move in 4 9 13 26 28; do
  echo "===== LANCE $move ====="
  python -m tal.agent --report data/reports/cpato-20261124T193623799365Z.json --move "$move" --color black --depth 14 --trace
done 2>&1 | tee data/benchmarks/qwen35-tools-v13.txt
```

## Ferramentas

`get_board`, `inspect_square`, `get_legal_moves`, `get_attackers`, `simulate_move`, `analyze_position`, `compare_moves`, `validate_sequence`.

Todas aceitam `position=before|after` (padrão before) e `line` (até oito movimentos SAN hipotéticos). Cada chamada reconstrói uma posição independente, sem alterar a partida. `get_attackers` retorna ataques geométricos, incluindo peças cravadas, não necessariamente capturas legais. `validate_sequence` verifica a legalidade, não se a sequência é forçada. Como a origem é FEN, histórico de repetição não é reconstruído.

O orquestrador usa a API OpenAI-compatible: recebe `tool_calls`, valida argumentos, executa a lista fechada de ferramentas, devolve mensagens `role=tool` com `tool_call_id`, e solicita a resposta final. O máximo padrão é quatro chamadas (configurável de 1 a 6). Ao atingir o limite, solicita `tool_choice=none`. Não executa comandos arbitrários. O Stockfish é aberto sob demanda e encerrado ao sair. A profundidade é limitada a 18. O código não adiciona `/no_think` às mensagens de ferramenta.

Ainda não há RAG nem verificador semântico de respostas finais: ferramentas fornecem fatos, mas o LLM ainda pode interpretá-los incorretamente. O uso de `--trace` permite conferir quais dados foram realmente consultados. Use apenas em partidas finalizadas.

## Validação da entrega

Foram executados seis testes simulados do orquestrador, quatro testes de coach e quatro de Chess.com, todos aprovados. Sintaxe compilada. A biblioteca chess não está instalada no ambiente de construção: os cinco novos testes de ferramentas e dez testes de análise/Vision devem ser executados localmente. O total esperado é 29 testes. A comunicação real com llama.cpp e Stockfish ainda deve ser validada no computador do jogador.
