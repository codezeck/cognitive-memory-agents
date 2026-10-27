
import os
import sqlite3

DB_PATH = os.getenv("DB_PATH", "dados/memorias.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS memorias (
    id            TEXT PRIMARY KEY,
    usuario_id    TEXT NOT NULL,
    texto         TEXT NOT NULL,
    ativa         INTEGER NOT NULL DEFAULT 1,
    criada_em     TEXT NOT NULL,
    atualizada_em TEXT NOT NULL,
    chave         TEXT,
    metadados     TEXT NOT NULL DEFAULT '{}',
    vetor         TEXT NOT NULL DEFAULT '[]'
);

CREATE INDEX IF NOT EXISTS idx_memorias_usuario
ON memorias(usuario_id);

CREATE INDEX IF NOT EXISTS idx_memorias_ativas
ON memorias(usuario_id, ativa);
"""


def conectar(caminho: str | None = None) -> sqlite3.Connection:
    caminho = caminho or DB_PATH

    if caminho != ":memory:":
        os.makedirs(os.path.dirname(caminho) or ".", exist_ok=True)

    con = sqlite3.connect(caminho, check_same_thread=False)
    con.row_factory = sqlite3.Row

    con.executescript(SCHEMA)

    # Atualiza bancos existentes sem apagar as memórias.
    colunas = {
        coluna["name"]
        for coluna in con.execute("PRAGMA table_info(memorias)")
    }

    novas_colunas = {
        "chave": "TEXT",
        "metadados": "TEXT NOT NULL DEFAULT '{}'",
        "vetor": "TEXT NOT NULL DEFAULT '[]'",
    }

    for nome, definicao in novas_colunas.items():
        if nome not in colunas:
            con.execute(
                f"ALTER TABLE memorias ADD COLUMN {nome} {definicao}"
            )

    con.commit()
    return con
