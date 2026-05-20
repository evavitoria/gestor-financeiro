from flask import Flask, render_template, request, redirect, url_for
import sqlite3

app = Flask(__name__)

def init_db():
    conn = sqlite3.connect('financas.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transacoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
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
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT,
            valor REAL
        )
    ''')
    conn.commit()
    conn.close()

init_db()

def get_salario():
    conn = sqlite3.connect('financas.db')
    cursor = conn.cursor()
    cursor.execute("SELECT valor FROM configuracoes WHERE chave = 'salario'")
    row = cursor.fetchone()
    conn.close()
    return float(row[0]) if row else 0.0

@app.route('/')
def index():
    conn = sqlite3.connect('financas.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM transacoes ORDER BY id DESC')
    historico = cursor.fetchall()
    cursor.execute('SELECT * FROM caixinhas ORDER BY id DESC')
    caixinhas = cursor.fetchall()
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
    conn = sqlite3.connect('financas.db')
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO configuracoes (chave, valor) VALUES ('salario', ?)", (valor,))
    conn.commit()
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
    conn = sqlite3.connect('financas.db')
    cursor = conn.cursor()
    cursor.execute('INSERT INTO transacoes (valor, tipo, duvida) VALUES (?, ?, ?)',
                   (valor, tipo, duvida))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

@app.route('/deletar/<int:id>', methods=['POST'])
def deletar(id):
    conn = sqlite3.connect('financas.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM transacoes WHERE id = ?', (id,))
    conn.commit()
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
    conn = sqlite3.connect('financas.db')
    cursor = conn.cursor()
    cursor.execute('INSERT INTO caixinhas (nome, valor) VALUES (?, ?)', (nome, valor))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

@app.route('/deletar_caixinha/<int:id>', methods=['POST'])
def deletar_caixinha(id):
    conn = sqlite3.connect('financas.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM caixinhas WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)