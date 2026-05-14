from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
import os

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

DB = 'budgetku.db'

def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.executescript('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT, category TEXT, amount REAL,
            date TEXT, note TEXT
        );
        CREATE TABLE IF NOT EXISTS budgets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT, amount REAL, month TEXT
        );
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT, type TEXT
        );
    ''')
    # Default categories
    cursor = conn.execute("SELECT COUNT(*) FROM categories")
    if cursor.fetchone()[0] == 0:
        defaults = [
            ('Makan','expense'),('Transport','expense'),('Belanja','expense'),
            ('Hiburan','expense'),('Tagihan','expense'),('Kesehatan','expense'),
            ('Gaji','income'),('Freelance','income'),('Lainnya','expense')
        ]
        conn.executemany("INSERT INTO categories (name,type) VALUES (?,?)", defaults)
    conn.commit()
    conn.close()

init_db()

@app.route('/transactions', methods=['GET'])
def get_transactions():
    month = request.args.get('month', '')
    conn = get_db()
    if month:
        rows = conn.execute("SELECT * FROM transactions WHERE date LIKE ? ORDER BY date DESC", (month+'%',)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM transactions ORDER BY date DESC").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route('/transactions', methods=['POST'])
def add_transaction():
    d = request.json
    conn = get_db()
    conn.execute("INSERT INTO transactions (type,category,amount,date,note) VALUES (?,?,?,?,?)",
        (d['type'], d['category'], d['amount'], d['date'], d.get('note','')))
    conn.commit()
    conn.close()
    return jsonify({'status': 'ok'})

@app.route('/transactions/<int:id>', methods=['DELETE'])
def delete_transaction(id):
    conn = get_db()
    conn.execute("DELETE FROM transactions WHERE id=?", (id,))
    conn.commit()
    conn.close()
    return jsonify({'status': 'ok'})

@app.route('/summary', methods=['GET'])
def get_summary():
    month = request.args.get('month', '')
    conn = get_db()
    where = "WHERE date LIKE ?" if month else ""
    params = (month+'%',) if month else ()
    rows = conn.execute(f"SELECT * FROM transactions {where}", params).fetchall()
    total_income = sum(r['amount'] for r in rows if r['type'] == 'income')
    total_expense = sum(r['amount'] for r in rows if r['type'] == 'expense')
    exp_by_cat = {}
    for r in rows:
        if r['type'] == 'expense':
            exp_by_cat[r['category']] = exp_by_cat.get(r['category'], 0) + r['amount']
    conn.close()
    return jsonify({
        'total_income': total_income,
        'total_expense': total_expense,
        'balance': total_income - total_expense,
        'expense_by_category': [{'category': k, 'total': v} for k, v in exp_by_cat.items()]
    })

@app.route('/categories', methods=['GET'])
def get_categories():
    conn = get_db()
    rows = conn.execute("SELECT * FROM categories").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route('/budgets', methods=['GET'])
def get_budgets():
    month = request.args.get('month', '')
    conn = get_db()
    if month:
        rows = conn.execute("SELECT * FROM budgets WHERE month=?", (month,)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM budgets").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route('/budgets', methods=['POST'])
def set_budget():
    d = request.json
    conn = get_db()
    existing = conn.execute("SELECT id FROM budgets WHERE category=? AND month=?",
        (d['category'], d['month'])).fetchone()
    if existing:
        conn.execute("UPDATE budgets SET amount=? WHERE id=?", (d['amount'], existing['id']))
    else:
        conn.execute("INSERT INTO budgets (category,amount,month) VALUES (?,?,?)",
            (d['category'], d['amount'], d['month']))
    conn.commit()
    conn.close()
    return jsonify({'status': 'ok'})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')