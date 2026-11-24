# TAL — Chess Intelligence | v1.0

Motor de análise pós-partida, preparado para a futura IA treinadora TAL. A versão 1 importa partidas públicas do Chess.com, interpreta PGN, avalia cada posição com Stockfish via UCI e exporta relatórios JSON para futura geração de datasets. Não inclui LLM, fine-tuning nem interface web ainda.

## Instalação

Python 3.10+ (recomendado 3.12). Execute na raiz do repositório, após copiar os arquivos do ZIP.

### Linux Mint / Ubuntu

```bash
sudo apt update
sudo apt install stockfish python3-venv
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
```

O TAL detecta `/usr/games/stockfish` automaticamente. Para escolher outra versão, baixe em https://stockfishchess.org/download/ e configure o caminho absoluto em `.env`.

### Windows (PowerShell)

Baixe o Stockfish para Windows x86-64 em https://stockfishchess.org/download/ e extraia, por exemplo, em `C:\TAL-tools\stockfish`. Localize o executável real.

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Se a execução do script estiver bloqueada, use `Set-ExecutionPolicy -Scope Process Bypass` ou execute os comandos Python com `.\.venv\Scripts\python.exe` sem ativar.

## Configuração

Edite o arquivo `.env` (não envie ao Git):

```dotenv
CHESSCOM_USERNAME=seu_nickname
CHESSCOM_CONTACT=seu_email_de_contato
STOCKFISH_PATH=
STOCKFISH_THREADS=2
STOCKFISH_HASH_MB=64
STOCKFISH_DEPTH=14
```

No Windows preencha `STOCKFISH_PATH=C:/TAL-tools/stockfish/NOME_REAL_DO_EXECUTAVEL.exe`. Use barras normais `/` e substitua o nome fictício. No Linux deixe vazio se instalou pelo apt. O email de contato serve para identificar a aplicação no User-Agent; não é credencial e não precisa ser o email da conta. O Chess.com PubAPI é público e somente leitura: não exige chave, token ou senha. Os arquivos mensais podem não refletir imediatamente a última partida. A engine Stockfish é um processo local separado, não uma API HTTP externa.

## Testar e usar

```bash
python -m tal doctor --only stockfish
python -m tal doctor --only chesscom
python -m tal doctor
python -m tal pgn examples/demo.pgn --depth 8 --player DemoWhite
python -m tal games --limit 5
python -m tal analyze --game 1 --depth 12
```

`--game 1` seleciona a partida mais recente na consulta efetuada naquele momento; use o mesmo filtro de modalidade que usou na listagem. A lista pode mudar se novas partidas forem publicadas.

```bash
python -m tal games --time-class rapid --limit 5
python -m tal analyze --time-class rapid --game 2 --depth 14
python -m tal analyze --user outro_nickname --game 1 --depth 10
python -m tal pgn caminho/partida.pgn --player NomeNoPGN
python -m unittest discover -s tests -v
```

## Estrutura

- `tal/chesscom.py`: API pública, User-Agent, retentativas e arquivos mensais em sequência.
- `tal/analysis.py`: engine UCI, FEN, SAN, avaliação de ambos os lados, melhor linha e classificação.
- `tal/settings.py`: configuração e detecção da engine.
- `tal/__main__.py`: CLI e exportação.
- `examples/demo.pgn`: partida de teste fictícia (mate do louco).
- `data/pgn/` e `data/reports/`: gerados automaticamente, ignorados pelo Git.
- `tests/`: testes de API simulada e motor simulado.

## Análise

O motor avalia a posição inicial e cada posição após uma jogada; reaproveita a avaliação como ponto de partida do lance seguinte. Assim uma partida com N meios-lances demanda até N+1 buscas, não 2N. Os resultados dependem da profundidade, versão e configurações do Stockfish. As avaliações são salvas da perspectiva das brancas e de quem jogou. A perda em centipeões é aproximada, truncada em zero e não calculada quando há avaliação de mate. O campo `mate_winner` distingue mate dado e recebido mesmo quando `mate=0`. O resumo usa somente os lances do jogador identificado pelo nickname, ou ambos se não identificado. A classificação é heurística própria (melhor, excelente, bom, imprecisão, erro, erro grave e categorias de mate), não reproduz a precisão do Chess.com e não substitui análise humana.

A versão 1 só suporta xadrez padrão e foi projetada para revisão de partidas encerradas, não assistência durante partidas em andamento. Utilize PGNs locais somente de partidas concluídas.

## Próxima versão

Conectar o relatório JSON ao LLM local via llama.cpp, construir dataset de interpretação técnica e personalidade do TAL, validar as explicações contra as linhas da engine e comparar o modelo-base com QLoRA. Para publicar o projeto, revise as licenças GPL das dependências `chess` e Stockfish e as condições da API do Chess.com. O binário do Stockfish não é distribuído neste ZIP.

Referências: https://support.chess.com/en/articles/9650547-what-is-the-pubapi-and-how-do-i-use-it ; https://python-chess.readthedocs.io/en/stable/engine.html ; https://stockfishchess.org/download/
