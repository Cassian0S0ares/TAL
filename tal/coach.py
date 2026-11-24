from pathlib import Path
from .context import context, critical_moves, find_move, load_report
from .llm import LocalLLM

PROMPT = Path(__file__).parent / 'prompts' / 'coach.txt'


def ask(client, report, question, selected=None):
    if not question.strip() or len(question) > 500:
        raise ValueError('Pergunta deve ter entre 1 e 500 caracteres.')
    messages = [{'role': 'system', 'content': PROMPT.read_text(encoding='utf-8')},
                {'role': 'user', 'content': 'Dados do relatório pós-partida:\n' + context(report, selected) + '\nPergunta: ' + question}]
    return client.complete(messages)


def show_answer(client, report, question, selected=None):
    print('TAL está analisando...', flush=True)
    answer, finish = ask(client, report, question, selected)
    print('\nTAL:', answer)
    if finish == 'length':
        print('[Aviso] Resposta atingiu o limite de tokens.')


def choose(report, value):
    parts = value.split()
    if len(parts) != 2 or parts[1] not in ('white', 'black', 'brancas', 'pretas'):
        raise ValueError('Use /lance 13 black ou /lance 13 pretas.')
    color = {'brancas': 'white', 'pretas': 'black'}.get(parts[1], parts[1])
    return find_move(report, int(parts[0]), color)


def run_chat(path=None):
    path, report = load_report(path)
    client = LocalLLM()
    client.doctor()
    print(f'TAL Coach | {path.name}\n/lance 13 pretas | /criticos | /geral | /sair')
    print('Cada pergunta é independente. Selecione um lance para fixar o contexto.')
    selected = None
    while True:
        try:
            q = input('\nVocê: ').strip()
        except EOFError:
            break
        if q == '/sair':
            break
        try:
            if q == '/geral':
                selected = None
                print('Contexto geral restaurado.')
            elif q == '/criticos':
                for r in critical_moves(report, 5):
                    print(r['move_number'], r['color'], r['played_san'], r['classification'], r['centipawn_loss'])
            elif q.startswith('/lance '):
                selected = choose(report, q[7:])
                print(f'Lance selecionado: {selected["played_san"]}')
                show_answer(client, report, 'Explique esse lance e a alternativa do motor.', selected)
            elif q:
                show_answer(client, report, q, selected)
        except (ValueError, RuntimeError) as e:
            print(f'ERRO: {e}')
