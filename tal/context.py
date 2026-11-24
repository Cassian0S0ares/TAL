"""Select compact factual evidence from a TAL v1 report."""
import json
from pathlib import Path
from .settings import DATA


def load_report(path=None):
    if path is None:
        paths = sorted((DATA / 'reports').glob('*.json'), key=lambda p: (p.stat().st_mtime_ns, p.name))
        if not paths:
            raise ValueError('Nenhum relatório encontrado. Execute python -m tal analyze primeiro.')
        path = paths[-1]
    path = Path(path)
    data = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(data, dict) or data.get('schema_version') != 1 or not data.get('moves'):
        raise ValueError('Relatório TAL v1 inválido ou sem lances.')
    return path, data


def find_move(report, number, color):
    for row in report['moves']:
        if row['move_number'] == number and row['color'] == color:
            return row
    raise ValueError(f'Lance {number} ({color}) não encontrado.')


def critical_moves(report, limit=3):
    rows = report['moves']
    if report.get('player_color'):
        rows = [r for r in rows if r.get('is_player')]
    def severity(r):
        return (r.get('classification') in ('permite_mate', 'perde_mate_forcado'), r.get('centipawn_loss') or 0)
    return sorted(rows, key=severity, reverse=True)[:limit]


def facts(row):
    # FEN plus legal engine lines are evidence, not proof of a natural-language explanation.
    keys = ('move_number', 'color', 'played_san', 'best_san', 'before_mover_pov', 'after_mover_pov', 'centipawn_loss', 'classification', 'fen_before', 'best_line_san', 'reply_line_san')
    result = {k: row.get(k) for k in keys}
    if row.get('fen_before'):
        from .vision import vision_facts
        result['vision'] = vision_facts(row)
    else:
        result['vision'] = {'status': 'indisponível: relatório sem FEN'}
    return result


def context(report, selected=None):
    h = report.get('headers', {})
    obj = {'white': str(h.get('White', ''))[:80], 'black': str(h.get('Black', ''))[:80],
           'result': h.get('Result'), 'player_color': report.get('player_color'),
           'engine': report.get('engine'), 'depth': report.get('depth'), 'summary': report.get('summary')}
    obj['moves'] = [facts(selected)] if selected is not None else [facts(r) for r in critical_moves(report, 2)]
    return json.dumps(obj, ensure_ascii=False, separators=(',', ':'))
