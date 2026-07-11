#v2
from flask import Flask, request, jsonify
from flask_cors import CORS
import psycopg2
import psycopg2.extras
import os
from datetime import date

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

DATABASE_URL = "postgresql://postgres.fabxhpucydlthhmgugum:MaulBudget26@aws-1-ap-southeast-1.pooler.supabase.com:5432/postgres"
def get_db():
    conn = psycopg2.connect(DATABASE_URL)
    return conn

def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id SERIAL PRIMARY KEY,
            type TEXT, category TEXT, amount REAL,
            date TEXT, note TEXT
        );
    ''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS budgets (
            id SERIAL PRIMARY KEY,
            category TEXT, amount REAL, month TEXT
        );
    ''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS categories (
            id SERIAL PRIMARY KEY,
            name TEXT, type TEXT
        );
    ''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS savings_goals (
            id SERIAL PRIMARY KEY,
            name TEXT, target_amount REAL, current_amount REAL DEFAULT 0,
            created_at TEXT
        );
    ''')
    cur.execute("SELECT COUNT(*) FROM categories")
    count = cur.fetchone()[0]
    if count == 0:
        defaults = [
            ('Makan','expense'),('Transport','expense'),('Belanja','expense'),
            ('Hiburan','expense'),('Tagihan','expense'),('Kesehatan','expense'),
            ('Gaji','income'),('Freelance','income'),('Tabungan','expense'),('Lainnya','expense')
        ]
        cur.executemany("INSERT INTO categories (name,type) VALUES (%s,%s)", defaults)
    else:
        cur.execute("SELECT COUNT(*) FROM categories WHERE name=%s", ('Tabungan',))
        if cur.fetchone()[0] == 0:
            cur.execute("INSERT INTO categories (name,type) VALUES (%s,%s)", ('Tabungan','expense'))
    conn.commit()
    cur.close()
    conn.close()

try:
    init_db()
except Exception as e:
    print(f"Database init error: {e}")

@app.route('/transactions', methods=['GET'])
def get_transactions():
    month = request.args.get('month', '')
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    if month:
        cur.execute("SELECT * FROM transactions WHERE date LIKE %s ORDER BY date DESC", (month+'%',))
    else:
        cur.execute("SELECT * FROM transactions ORDER BY date DESC")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route('/transactions', methods=['POST'])
def add_transaction():
    d = request.json
    conn = get_db()
    cur = conn.cursor()
    cur.execute("INSERT INTO transactions (type,category,amount,date,note) VALUES (%s,%s,%s,%s,%s)",
        (d['type'], d['category'], d['amount'], d['date'], d.get('note','')))
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({'status': 'ok'})

@app.route('/transactions/<int:id>', methods=['DELETE'])
def delete_transaction(id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM transactions WHERE id=%s", (id,))
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({'status': 'ok'})

@app.route('/summary', methods=['GET'])
def get_summary():
    month = request.args.get('month', '')
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    if month:
        cur.execute("SELECT * FROM transactions WHERE date LIKE %s", (month+'%',))
    else:
        cur.execute("SELECT * FROM transactions")
    rows = cur.fetchall()
    total_income = sum(r['amount'] for r in rows if r['type'] == 'income')
    total_expense = sum(r['amount'] for r in rows if r['type'] == 'expense')
    exp_by_cat = {}
    for r in rows:
        if r['type'] == 'expense':
            exp_by_cat[r['category']] = exp_by_cat.get(r['category'], 0) + r['amount']
    cur.close()
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
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT * FROM categories")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route('/budgets', methods=['GET'])
def get_budgets():
    month = request.args.get('month', '')
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    if month:
        cur.execute("SELECT * FROM budgets WHERE month=%s", (month,))
    else:
        cur.execute("SELECT * FROM budgets")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route('/budgets', methods=['POST'])
def set_budget():
    d = request.json
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT id FROM budgets WHERE category=%s AND month=%s", (d['category'], d['month']))
    existing = cur.fetchone()
    if existing:
        cur.execute("UPDATE budgets SET amount=%s WHERE id=%s", (d['amount'], existing['id']))
    else:
        cur.execute("INSERT INTO budgets (category,amount,month) VALUES (%s,%s,%s)",
            (d['category'], d['amount'], d['month']))
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({'status': 'ok'})

# ===== Tabungan (Savings Goals) =====

@app.route('/savings', methods=['GET'])
def get_savings():
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT * FROM savings_goals ORDER BY id DESC")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route('/savings', methods=['POST'])
def add_savings_goal():
    d = request.json
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO savings_goals (name, target_amount, current_amount, created_at) VALUES (%s,%s,%s,%s)",
        (d['name'], d['target_amount'], 0, date.today().isoformat())
    )
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({'status': 'ok'})

@app.route('/savings/<int:id>/deposit', methods=['POST'])
def deposit_savings(id):
    d = request.json
    amount = d['amount']
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT * FROM savings_goals WHERE id=%s", (id,))
    goal = cur.fetchone()
    if not goal:
        cur.close()
        conn.close()
        return jsonify({'error': 'Goal not found'}), 404

    cur.execute(
        "UPDATE savings_goals SET current_amount = current_amount + %s WHERE id=%s",
        (amount, id)
    )
    cur.execute(
        "INSERT INTO transactions (type,category,amount,date,note) VALUES (%s,%s,%s,%s,%s)",
        ('expense', 'Tabungan', amount, date.today().isoformat(), f"Nabung: {goal['name']}")
    )
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({'status': 'ok'})

@app.route('/savings/<int:id>', methods=['DELETE'])
def delete_savings_goal(id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM savings_goals WHERE id=%s", (id,))
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({'status': 'ok'})

if __name__ == '__main__':  
    app.run(debug=True, host='0.0.0.0')