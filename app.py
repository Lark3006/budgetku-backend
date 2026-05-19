from flask import Flask, request, jsonify
from flask_cors import CORS
import psycopg2
import psycopg2.extras
import os

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

DATABASE_URL = os.environ.get('DATABASE_URL')

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
    cur.execute("SELECT COUNT(*) FROM categories")
    count = cur.fetchone()[0]
    if count == 0:
        defaults = [
            ('Makan','expense'),('Transport','expense'),('Belanja','expense'),
            ('Hiburan','expense'),('Tagihan','expense'),('Kesehatan','expense'),
            ('Gaji','income'),('Freelance','income'),('Lainnya','expense')
        ]
        cur.executemany("INSERT INTO categories (name,type) VALUES (%s,%s)", defaults)
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
    el