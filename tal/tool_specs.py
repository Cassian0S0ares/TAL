"""Schemas shared by the tool dispatcher and model client."""
MAX_LINE = 8


def schema(name, description, properties=None, required=()):
    props = {
        'position': {'type': 'string', 'enum': ['before', 'after'], 'description': 'Antes/depois do lance selecionado; padrão before.'},
        'line': {'type': 'array', 'items': {'type': 'string'}, 'maxItems': MAX_LINE,
                 'description': 'Sequência SAN hipotética a partir dessa posição; padrão vazia.'},
    }
    props.update(properties or {})
    return {'type': 'function', 'function': {'name': name, 'description': description,
            'parameters': {'type': 'object', 'properties': props, 'required': list(required),
                           'additionalProperties': False}}}


SQUARE = {'type': 'string', 'pattern': '^[a-h][1-8]$'}
MOVE = {'type': 'string', 'description': 'Movimento em notação SAN, ex. dxc4 ou O-O-O.'}
TOOLS = [
    schema('get_board', 'Retorna peças, casas, FEN e estado do tabuleiro.'),
    schema('inspect_square', 'Identifica a peça em uma casa.', {'square': SQUARE}, ('square',)),
    schema('get_legal_moves', 'Lista movimentos legais do lado que joga.'),
    schema('get_attackers', 'Lista ataques geométricos de ambas as cores a uma casa; não garante captura legal.', {'square': SQUARE}, ('square',)),
    schema('simulate_move', 'Simula uma jogada SAN legal e retorna os efeitos.', {'move': MOVE}, ('move',)),
    schema('analyze_position', 'Consulta Stockfish, com avaliação da perspectiva do jogador selecionado e variante principal.'),
    schema('compare_moves', 'Simula duas alternativas legais e avalia cada posição resultante com Stockfish, na mesma perspectiva.', {'move_a': MOVE, 'move_b': MOVE}, ('move_a', 'move_b')),
    schema('validate_sequence', 'Confere legalidade de uma sequência SAN, não prova que seja forçada.', {'moves': {'type': 'array', 'items': MOVE, 'minItems': 1, 'maxItems': MAX_LINE}}, ('moves',)),
]
SCHEMAS = {t['function']['name']: t['function']['parameters'] for t in TOOLS}
