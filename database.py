"""Conexão SQLite e inicialização, sem ORM."""
import sqlite3
from pathlib import Path

from flask import current_app, g

BASE_DIR = Path(__file__).resolve().parent


def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(current_app.config['DATABASE'], timeout=10)
        g.db.row_factory = sqlite3.Row
        # Precisa ser ativado em CADA conexão.
        g.db.execute('PRAGMA foreign_keys = ON')
    return g.db


def close_db(error=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()


def init_db(with_seed=False):
    db = get_db()
    db.executescript((BASE_DIR / 'schema.sql').read_text(encoding='utf-8'))
    if with_seed:
        try:
            db.executescript((BASE_DIR / 'seed.sql').read_text(encoding='utf-8'))
        except sqlite3.Error:
            db.rollback()
            raise
