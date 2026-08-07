#!/usr/bin/env python3
"""
Casa Campestre - servidor de pre-pedidos de pizza.

Cada pedido enviado pelo formulario e gravado de DUAS formas ao mesmo tempo:
  1) No banco SQLite  ->  pedidos.db      (fonte principal, consultavel)
  2) Num backup JSON  ->  pedidos_backup.json  (copia de seguranca legivel)

Paginas servidas:
  /                -> index.html   (formulario de pre-pedido)
  /obrigado.html   -> agradecimento com resumo do pedido
  /pedidos.html    -> listagem de todos os pedidos (pede um token)

API:
  POST /api/pedidos              -> salva um pedido (usado pelo formulario)
  GET  /api/pedidos?token=XXXX   -> lista os pedidos em JSON (protegido por token)

Como rodar:
    python server.py
E abrir no navegador:  http://localhost:8000

Configuracao opcional (variaveis de ambiente):
    ADMIN_TOKEN  -> token da pagina de listagem (padrao: casa-campestre-2026)
    PORT         -> porta do servidor          (padrao: 8000)
"""

import os
import json
import sqlite3
import datetime
import threading
from pathlib import Path

from flask import Flask, request, jsonify, send_from_directory

BASE_DIR = Path(__file__).resolve().parent

# Pasta onde os dados sao gravados. Em producao (Docker) apontamos DATA_DIR
# para um volume, para que pedidos.db e pedidos_backup.json fiquem acessiveis
# fora do container. Sem a variavel, grava na propria pasta do projeto.
DATA_DIR = Path(os.environ.get("DATA_DIR", BASE_DIR))
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DATA_DIR / "pedidos.db"
BACKUP_PATH = DATA_DIR / "pedidos_backup.json"

ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN", "casa-campestre-2026")
# Token separado (mais restrito) para APAGAR pedidos - acao destrutiva.
DELETE_TOKEN = os.environ.get("DELETE_TOKEN", "casa-campestre-remover-2026")
PORT = int(os.environ.get("PORT", "8000"))

# Protege a escrita do backup JSON quando ha varias requisicoes ao mesmo tempo.
_backup_lock = threading.Lock()

app = Flask(__name__, static_folder=None)


# ----------------------------------------------------------------------------
# Banco de dados
# ----------------------------------------------------------------------------
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Cria a tabela (se ainda nao existir) e garante o arquivo de backup."""
    with get_db() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS pedidos (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                nome        TEXT    NOT NULL,
                mesa        TEXT,
                telefone    TEXT,
                observacoes TEXT,
                itens_json  TEXT    NOT NULL,
                total       REAL    NOT NULL,
                criado_em   TEXT    NOT NULL
            )
            """
        )
    if not BACKUP_PATH.exists():
        BACKUP_PATH.write_text("[]", encoding="utf-8")


def _read_backup():
    try:
        data = json.loads(BACKUP_PATH.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def append_backup(record):
    """Acrescenta um pedido ao JSON de backup (le tudo, adiciona, regrava)."""
    with _backup_lock:
        data = _read_backup()
        data.append(record)
        BACKUP_PATH.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )


def remove_backup(pedido_id):
    """Remove um pedido do JSON de backup pelo id."""
    with _backup_lock:
        data = [r for r in _read_backup() if r.get("id") != pedido_id]
        BACKUP_PATH.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )


# ----------------------------------------------------------------------------
# Paginas (arquivos estaticos)
# ----------------------------------------------------------------------------
@app.route("/")
def index():
    return send_from_directory(BASE_DIR, "index.html")


@app.route("/obrigado.html")
def obrigado():
    return send_from_directory(BASE_DIR, "obrigado.html")


@app.route("/pedidos.html")
@app.route("/pedidos")
def pedidos_page():
    return send_from_directory(BASE_DIR, "pedidos.html")


@app.route("/img/<path:filename>")
def img(filename):
    return send_from_directory(BASE_DIR / "img", filename)


# ----------------------------------------------------------------------------
# API
# ----------------------------------------------------------------------------
@app.route("/api/pedidos", methods=["POST"])
def criar_pedido():
    data = request.get_json(silent=True) or {}

    nome = (data.get("name") or "").strip()
    itens = data.get("items") or []
    if not nome or not isinstance(itens, list) or len(itens) == 0:
        return (
            jsonify({"ok": False, "error": "Nome e ao menos um item sao obrigatorios."}),
            400,
        )

    mesa = (data.get("table") or "").strip()
    telefone = (data.get("phone") or "").strip()
    observacoes = (data.get("notes") or "").strip()
    try:
        total = float(data.get("total") or 0)
    except (TypeError, ValueError):
        total = 0.0
    criado_em = data.get("submittedAt") or datetime.datetime.now().isoformat()
    itens_json = json.dumps(itens, ensure_ascii=False)

    # 1) grava no SQLite
    with get_db() as conn:
        cur = conn.execute(
            "INSERT INTO pedidos "
            "(nome, mesa, telefone, observacoes, itens_json, total, criado_em) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (nome, mesa, telefone, observacoes, itens_json, total, criado_em),
        )
        pedido_id = cur.lastrowid

    # 2) grava no backup JSON
    append_backup(
        {
            "id": pedido_id,
            "nome": nome,
            "mesa": mesa,
            "telefone": telefone,
            "observacoes": observacoes,
            "itens": itens,
            "total": total,
            "criado_em": criado_em,
        }
    )

    return jsonify({"ok": True, "id": pedido_id})


@app.route("/api/pedidos", methods=["GET"])
def listar_pedidos():
    token = request.args.get("token") or request.headers.get("X-Admin-Token")
    if token != ADMIN_TOKEN:
        return jsonify({"ok": False, "error": "Token invalido."}), 401

    with get_db() as conn:
        rows = conn.execute("SELECT * FROM pedidos ORDER BY id DESC").fetchall()

    pedidos = [
        {
            "id": r["id"],
            "nome": r["nome"],
            "mesa": r["mesa"],
            "telefone": r["telefone"],
            "observacoes": r["observacoes"],
            "itens": json.loads(r["itens_json"]),
            "total": r["total"],
            "criado_em": r["criado_em"],
        }
        for r in rows
    ]
    return jsonify({"ok": True, "total_pedidos": len(pedidos), "pedidos": pedidos})


@app.route("/api/pedidos/<int:pedido_id>", methods=["DELETE"])
def remover_pedido(pedido_id):
    # A remocao usa um token proprio (DELETE_TOKEN), diferente do de listagem.
    token = request.args.get("token") or request.headers.get("X-Delete-Token")
    if token != DELETE_TOKEN:
        return jsonify({"ok": False, "error": "Token de remocao invalido."}), 401

    with get_db() as conn:
        cur = conn.execute("DELETE FROM pedidos WHERE id = ?", (pedido_id,))
        apagados = cur.rowcount

    if apagados == 0:
        return jsonify({"ok": False, "error": "Pedido nao encontrado."}), 404

    remove_backup(pedido_id)
    return jsonify({"ok": True, "id": pedido_id})


# Inicializa o banco assim que o modulo carrega, para funcionar tanto com
# 'python server.py' (dev) quanto com gunicorn (producao).
init_db()


if __name__ == "__main__":
    print("Casa Campestre - servidor de pre-pedidos")
    print(f"  Formulario:    http://localhost:{PORT}/")
    print(f"  Pedidos:       http://localhost:{PORT}/pedidos.html?token={ADMIN_TOKEN}")
    print(f"  Token remover: {DELETE_TOKEN}")
    print(f"  SQLite:        {DB_PATH}")
    print(f"  Backup JSON:   {BACKUP_PATH}")
    app.run(host="0.0.0.0", port=PORT, debug=False)
