from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import psycopg2
import os

app = Flask(__name__)
app.secret_key = 'chave-secreta-gestor-2024'

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

DATABASE_URL = os.environ.get('DATABASE_URL', None)
USE_SQLITE = DATABASE_URL is None

def get_conn():
    if USE_SQLITE:
        import sqlite3
        conn = sqlite3.connect('financas.db')
        conn.row_factory = sqlite3.Row
        return conn, 'sqlite'
    return psycopg2.connect(DATABASE_URL), 'pg'

def ph(sql):
    if USE_SQLITE:
        import re
        return re.sub(r'%s', '?', sql)
    return sql

def init_db():
    conn, tipo = get_conn()
    cursor = conn.cursor()
    auto = 'INTEGER PRIMARY KEY AUTOINCREMENT' if USE_SQLITE else 'SERIAL PRIMARY KEY'
    cursor.execute(f'''CREATE TABLE IF NOT EXISTS usuarios (
        id {auto}, email TEXT UNIQUE, senha TEXT, nome TEXT)''')
    cursor.execute(f'''CREATE TABLE IF NOT EXISTS transacoes (
        id {auto}, user_id INTEGER, valor REAL, tipo TEXT, duvida TEXT)''')
    cursor.execute(f'''CREATE TABLE IF NOT EXISTS configuracoes (
        id {auto}, user_id INTEGER, chave TEXT, valor TEXT,
        UNIQUE(user_id, chave))''')
    cursor.execute(f'''CREATE TABLE IF NOT EXISTS caixinhas (
        id {auto}, user_id INTEGER, nome TEXT, valor REAL)''')
    conn.commit()
    cursor.close()
    conn.close()

init_db()

class User(UserMixin):
    def __init__(self, id, email, nome):
        self.id = id
        self.email = email
        self.nome = nome

@login_manager.user_loader
def load_user(user_id):
    conn, _ = get_conn()
    cursor = conn.cursor()
    cursor.execute(ph('SELECT id, email, nome FROM usuarios WHERE id = %s'), (user_id,))
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    if row:
        return User(row[0], row[1], row[2])
    return None

@app.route('/cadastro', methods=['GET', 'POST'])
def cadastro():
    if request.method == 'POST':
        nome = request.form.get('nome')
        email = request.form.get('email')
        senha = generate_password_hash(request.form.get('senha'))
        try:
            conn, _ = get_conn()
            cursor = conn.cursor()
            cursor.execute(ph('INSERT INTO usuarios (email, senha, nome) VALUES (%s, %s, %s)'), (email, senha, nome))
            conn.commit()
            cursor.close()
            conn.close()
            flash('Conta criada! Faça login.')
            return redirect(url_for('login'))
        except:
            flash('Email já cadastrado!')
    return render_template('cadastro.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        senha = request.form.get('senha')
        conn, _ = get_conn()
        cursor = conn.cursor()
        cursor.execute(ph('SELECT id, email, nome, senha FROM usuarios WHERE email = %s'), (email,))
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        if row and check_password_hash(row[3], senha):
            login_user(User(row[0], row[1], row[2]))
            return redirect(url_for('index'))
        flash('Email ou senha incorretos!')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

def get_salario():
    conn, _ = get_conn()
    cursor = conn.cursor()
    cursor.execute(ph("SELECT valor FROM configuracoes WHERE chave = 'salario' AND user_id = %s"), (current_user.id,))
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    return float(row[0]) if row else 0.0

@app.route('/')
@login_required
def index():
    conn, _ = get_conn()
    cursor = conn.cursor()
    cursor.execute(ph('SELECT * FROM transacoes WHERE user_id = %s ORDER BY id DESC'), (current_user.id,))
    historico = cursor.fetchall()
    cursor.execute(ph('SELECT * FROM caixinhas WHERE user_id = %s ORDER BY id DESC'), (current_user.id,))
    caixinhas = cursor.fetchall()
    cursor.close()
    conn.close()

    salario = get_salario()
    total_gastos = sum(item[2] for item in historico)
    saldo = salario - total_gastos
    total_caixinhas = sum(c[3] for c in caixinhas)
    total_fixa = sum(item[2] for item in historico if item[3] == 'Conta Fixa')
    total_variavel = sum(item[2] for item in historico if item[3] == 'Gasto Variável')
    total_investimento = sum(item[2] for item in historico if item[3] == 'Investimento')

    return render_template('index.html',
                           historico=historico,
                           salario=salario,
                           total_gastos=total_gastos,
                           saldo=saldo,
                           caixinhas=caixinhas,
                           total_caixinhas=total_caixinhas,
                           total_fixa=total_fixa,
                           total_variavel=total_variavel,
                           total_investimento=total_investimento)

@app.route('/salario', methods=['POST'])
@login_required
def salvar_salario():
    valor_raw = request.form.get('salario', '0').replace(',', '.')
    try:
        valor = float(valor_raw)
    except:
        valor = 0.0
    conn, tipo = get_conn()
    cursor = conn.cursor()
    if tipo == 'sqlite':
        cursor.execute('INSERT OR REPLACE INTO configuracoes (user_id, chave, valor) VALUES (?, ?, ?)', (current_user.id, 'salario', valor))
    else:
        cursor.execute("INSERT INTO configuracoes (user_id, chave, valor) VALUES (%s, 'salario', %s) ON CONFLICT (user_id, chave) DO UPDATE SET valor = %s", (current_user.id, valor, valor))
    conn.commit()
    cursor.close()
    conn.close()
    return redirect(url_for('index'))

@app.route('/pergunta', methods=['POST'])
@login_required
def responder():
    valor_raw = request.form.get('valor', '0').replace(',', '.')
    tipo = request.form.get('tipo', 'Outros')
    duvida = request.form.get('duvida', '')
    try:
        valor = float(valor_raw)
    except:
        valor = 0.0
    conn, _ = get_conn()
    cursor = conn.cursor()
    cursor.execute(ph('INSERT INTO transacoes (user_id, valor, tipo, duvida) VALUES (%s, %s, %s, %s)'), (current_user.id, valor, tipo, duvida))
    conn.commit()
    cursor.close()
    conn.close()
    return redirect(url_for('index'))

@app.route('/deletar/<int:id>', methods=['POST'])
@login_required
def deletar(id):
    conn, _ = get_conn()
    cursor = conn.cursor()
    cursor.execute(ph('DELETE FROM transacoes WHERE id = %s AND user_id = %s'), (id, current_user.id))
    conn.commit()
    cursor.close()
    conn.close()
    return redirect(url_for('index'))

@app.route('/caixinha', methods=['POST'])
@login_required
def salvar_caixinha():
    nome = request.form.get('nome', '')
    valor_raw = request.form.get('valor', '0').replace(',', '.')
    try:
        valor = float(valor_raw)
    except:
        valor = 0.0
    conn, _ = get_conn()
    cursor = conn.cursor()
    cursor.execute(ph('INSERT INTO caixinhas (user_id, nome, valor) VALUES (%s, %s, %s)'), (current_user.id, nome, valor))
    conn.commit()
    cursor.close()
    conn.close()
    return redirect(url_for('index'))

@app.route('/deletar_caixinha/<int:id>', methods=['POST'])
@login_required
def deletar_caixinha(id):
    conn, _ = get_conn()
    cursor = conn.cursor()
    cursor.execute(ph('DELETE FROM caixinhas WHERE id = %s AND user_id = %s'), (id, current_user.id))
    conn.commit()
    cursor.close()
    conn.close()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)