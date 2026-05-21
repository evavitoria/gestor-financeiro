from flask import Flask, render_template, request, redirect, url_for
import psycopg2
import os

app = Flask(__name__)

DATABASE_URL = os.environ.get('DATABASE_URL', None)

if DATABASE_URL is None:
    # Roda local com SQLite
    import sqlite3
    USE_SQLITE = True
else:
    USE_SQLITE = False
    
def get_conn():
    return psycopg2.connect(DATABASE_URL)

def init_db():
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transacoes (
            id SERIAL PRIMARY KEY,
            valor REAL,
            tipo TEXT,
            duvida TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS configuracoes (
            chave TEXT PRIMARY KEY,
            valor TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS caixinhas (
            id SERIAL PRIMARY KEY,
            nome TEXT,
            valor REAL
        )
    ''')
    conn.commit()
    cursor.close()
    conn.close()

init_db()

def get_salario():
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT valor FROM configuracoes WHERE chave = 'salario'")
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    return float(row[0]) if row else 0.0

@app.route('/')
def index():
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM transacoes ORDER BY id DESC')
    historico = cursor.fetchall()
    cursor.execute('SELECT * FROM caixinhas ORDER BY id DESC')
    caixinhas = cursor.fetchall()
    cursor.close()
    conn.close()

    salario = get_salario()
    total_gastos = sum(item[1] for item in historico)
    saldo = salario - total_gastos
    total_caixinhas = sum(c[2] for c in caixinhas)
    total_fixa = sum(item[1] for item in historico if item[2] == 'Conta Fixa')
    total_variavel = sum(item[1] for item in historico if item[2] == 'Gasto Variável')
    total_investimento = sum(item[1] for item in historico if item[2] == 'Investimento')

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
def salvar_salario():
    valor_raw = request.form.get('salario', '0').replace(',', '.')
    try:
        valor = float(valor_raw)
    except:
        valor = 0.0
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO configuracoes (chave, valor) VALUES ('salario', %s) ON CONFLICT (chave) DO UPDATE SET valor = %s", (valor, valor))
    conn.commit()
    cursor.close()
    conn.close()
    return redirect(url_for('index'))

@app.route('/pergunta', methods=['POST'])
def responder():
    valor_raw = request.form.get('valor', '0').replace(',', '.')
    tipo = request.form.get('tipo', 'Outros')
    duvida = request.form.get('duvida', '')
    try:
        valor = float(valor_raw)
    except:
        valor = 0.0
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute('INSERT INTO transacoes (valor, tipo, duvida) VALUES (%s, %s, %s)', (valor, tipo, duvida))
    conn.commit()
    cursor.close()
    conn.close()
    return redirect(url_for('index'))

@app.route('/deletar/<int:id>', methods=['POST'])
def deletar(id):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM transacoes WHERE id = %s', (id,))
    conn.commit()
    cursor.close()
    conn.close()
    return redirect(url_for('index'))

@app.route('/caixinha', methods=['POST'])
def salvar_caixinha():
    nome = request.form.get('nome', '')
    valor_raw = request.form.get('valor', '0').replace(',', '.')
    try:
        valor = float(valor_raw)
    except:
        valor = 0.0
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute('INSERT INTO caixinhas (nome, valor) VALUES (%s, %s)', (nome, valor))
    conn.commit()
    cursor.close()
    conn.close()
    return redirect(url_for('index'))

@app.route('/deletar_caixinha/<int:id>', methods=['POST'])
def deletar_caixinha(id):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM caixinhas WHERE id = %s', (id,))
    conn.commit()
    cursor.close()
    conn.close()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)