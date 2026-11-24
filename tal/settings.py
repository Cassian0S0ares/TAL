import os
import shutil
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / '.env')
DATA = ROOT / 'data'

def username(value=None):
    name = (value or os.getenv('CHESSCOM_USERNAME', '')).strip().lower()
    if not name or not all(c.isascii() and (c.isalnum() or c in '_-') for c in name):
        raise ValueError('Defina CHESSCOM_USERNAME no .env ou passe --user com um nome válido.')
    return name

def engine_path():
    configured = os.getenv('STOCKFISH_PATH', '').strip()
    if configured:
        p = Path(configured).expanduser()
        if not p.is_absolute():
            p = ROOT / p
        if p.is_file():
            return str(p)
        found = shutil.which(configured)
        if found:
            return found
        raise FileNotFoundError(f'STOCKFISH_PATH não encontrado: {configured}')
    for candidate in (shutil.which('stockfish'), '/usr/games/stockfish', '/usr/bin/stockfish'):
        if candidate and Path(candidate).is_file():
            return str(candidate)
    raise FileNotFoundError('Stockfish não encontrado. Instale a engine ou configure STOCKFISH_PATH no .env.')

def positive_int(key, default):
    v = int(os.getenv(key, str(default)))
    if v < 1:
        raise ValueError(f'{key} deve ser maior que zero.')
    return v
