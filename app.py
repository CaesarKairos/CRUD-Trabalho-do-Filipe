"""Biblioteca Escolar: CRUD didático com Flask e SQL explícito."""
import os
import sqlite3
from datetime import date, timedelta
from pathlib import Path

from flask import Flask, abort, flash, redirect, render_template, request, url_for

from database import BASE_DIR, close_db, get_db, init_db

app = Flask(__name__)
app.config.update(
    SECRET_KEY=os.environ.get('SECRET_KEY', 'biblioteca-escolar-desenvolvimento-local'),
    DATABASE=str(BASE_DIR / 'biblioteca.db'),
)
app.teardown_appcontext(close_db)


@app.template_filter('data_br')
def data_br(value):
    return date.fromisoformat(value).strftime('%d/%m/%Y') if value else '—'


def encontrar(sql, registro_id):
    registro = get_db().execute(sql, (registro_id,)).fetchone()
    if registro is None:
        abort(404)
    return registro


def dados_formulario(campos):
    return {campo: request.form.get(campo, '').strip() for campo in campos}


@app.route('/')
def index():
    db = get_db()
    totais = {
        'livros': db.execute('SELECT COUNT(*) FROM livros').fetchone()[0],
        'disponiveis': db.execute('SELECT COUNT(*) FROM livros WHERE disponivel = 1').fetchone()[0],
        'ativos': db.execute("SELECT COUNT(*) FROM emprestimos WHERE status = 'Emprestado'").fetchone()[0],
        'alunos': db.execute('SELECT COUNT(*) FROM alunos').fetchone()[0],
    }
    recentes = db.execute("""
        SELECT e.*, a.nome, l.titulo FROM emprestimos e
        JOIN alunos a ON a.id = e.aluno_id JOIN livros l ON l.id = e.livro_id
        WHERE e.status = 'Emprestado' ORDER BY e.id DESC LIMIT 5
    """).fetchall()
    return render_template('index.html', totais=totais, recentes=recentes)


@app.route('/alunos')
def alunos():
    q = request.args.get('q', '').strip()
    registros = get_db().execute(
        'SELECT * FROM alunos WHERE nome LIKE ? OR matricula LIKE ? ORDER BY nome',
        (f'%{q}%', f'%{q}%'),
    ).fetchall()
    return render_template('alunos/lista.html', alunos=registros, q=q)


@app.route('/alunos/novo', methods=['GET', 'POST'])
@app.route('/alunos/<int:id>/editar', methods=['GET', 'POST'])
def aluno_formulario(id=None):
    aluno = encontrar('SELECT * FROM alunos WHERE id = ?', id) if id else {}
    if request.method == 'POST':
        aluno = dados_formulario(('nome', 'matricula', 'turma'))
        if not all(aluno.values()):
            flash('Preencha os campos obrigatórios.', 'erro')
        else:
            db = get_db()
            try:
                # O contexto faz COMMIT no sucesso e ROLLBACK em caso de erro.
                with db:
                    valores = (aluno['nome'], aluno['matricula'], aluno['turma'])
                    if id:
                        db.execute('UPDATE alunos SET nome = ?, matricula = ?, turma = ? WHERE id = ?', valores + (id,))
                    else:
                        db.execute('INSERT INTO alunos (nome, matricula, turma) VALUES (?, ?, ?)', valores)
                flash('Aluno atualizado com sucesso.' if id else 'Aluno cadastrado com sucesso.', 'sucesso')
                return redirect(url_for('alunos'))
            except sqlite3.IntegrityError:
                flash('Já existe um aluno com esta matrícula.', 'erro')
    return render_template('alunos/formulario.html', aluno=aluno, editando=id is not None)


@app.post('/alunos/<int:id>/excluir')
def aluno_excluir(id):
    encontrar('SELECT id FROM alunos WHERE id = ?', id)
    db = get_db()
    try:
        with db:
            db.execute('DELETE FROM alunos WHERE id = ?', (id,))
        flash('Aluno excluído com sucesso.', 'sucesso')
    except sqlite3.IntegrityError:
        flash('Não é possível excluir este registro porque existem empréstimos associados.', 'erro')
    return redirect(url_for('alunos'))


@app.route('/livros')
def livros():
    q = request.args.get('q', '').strip()
    disponiveis = request.args.get('disponiveis') == '1'
    registros = get_db().execute("""
        SELECT * FROM livros WHERE (titulo LIKE ? OR autor LIKE ?)
        AND (? = 0 OR disponivel = 1) ORDER BY titulo
    """, (f'%{q}%', f'%{q}%', int(disponiveis))).fetchall()
    return render_template('livros/lista.html', livros=registros, q=q, disponiveis=disponiveis)


@app.route('/livros/novo', methods=['GET', 'POST'])
@app.route('/livros/<int:id>/editar', methods=['GET', 'POST'])
def livro_formulario(id=None):
    livro = encontrar('SELECT * FROM livros WHERE id = ?', id) if id else {}
    if request.method == 'POST':
        livro = dados_formulario(('titulo', 'autor', 'isbn', 'ano_publicacao'))
        erro = None
        ano = None
        if not livro['titulo'] or not livro['autor']:
            erro = 'Preencha os campos obrigatórios.'
        elif livro['ano_publicacao']:
            try:
                ano = int(livro['ano_publicacao'])
                if not 1 <= ano <= date.today().year:
                    raise ValueError
            except ValueError:
                erro = 'Informe um ano de publicação válido, entre 1 e o ano atual.'
        if erro:
            flash(erro, 'erro')
        else:
            db = get_db()
            with db:
                valores = (livro['titulo'], livro['autor'], livro['isbn'] or None, ano)
                if id:
                    db.execute('UPDATE livros SET titulo = ?, autor = ?, isbn = ?, ano_publicacao = ? WHERE id = ?', valores + (id,))
                else:
                    db.execute('INSERT INTO livros (titulo, autor, isbn, ano_publicacao) VALUES (?, ?, ?, ?)', valores)
            flash('Livro atualizado com sucesso.' if id else 'Livro cadastrado com sucesso.', 'sucesso')
            return redirect(url_for('livros'))
    return render_template('livros/formulario.html', livro=livro, editando=id is not None, ano_atual=date.today().year)


@app.post('/livros/<int:id>/excluir')
def livro_excluir(id):
    encontrar('SELECT id FROM livros WHERE id = ?', id)
    db = get_db()
    try:
        with db:
            db.execute('DELETE FROM livros WHERE id = ?', (id,))
        flash('Livro excluído com sucesso.', 'sucesso')
    except sqlite3.IntegrityError:
        flash('Não é possível excluir este registro porque existem empréstimos associados.', 'erro')
    return redirect(url_for('livros'))


@app.route('/emprestimos')
def emprestimos():
    registros = get_db().execute("""
        SELECT e.*, a.nome, l.titulo FROM emprestimos e
        JOIN alunos a ON a.id = e.aluno_id JOIN livros l ON l.id = e.livro_id
        WHERE e.status = 'Emprestado' ORDER BY e.data_devolucao_prevista, e.id
    """).fetchall()
    return render_template('emprestimos/lista.html', emprestimos=registros)


@app.route('/emprestimos/novo', methods=['GET', 'POST'])
def emprestimo_formulario():
    db = get_db()
    dados = {'data_emprestimo': date.today().isoformat(),
             'data_devolucao_prevista': (date.today() + timedelta(days=14)).isoformat()}
    if request.method == 'POST':
        dados = dados_formulario(('aluno_id', 'livro_id', 'data_emprestimo', 'data_devolucao_prevista'))
        try:
            if not all(dados.values()):
                raise ValueError('Preencha os campos obrigatórios.')
            try:
                inicio = date.fromisoformat(dados['data_emprestimo'])
                prevista = date.fromisoformat(dados['data_devolucao_prevista'])
                aluno_id, livro_id = int(dados['aluno_id']), int(dados['livro_id'])
            except ValueError:
                raise ValueError('Informe um aluno, um livro e datas válidas.')
            if inicio > date.today():
                raise ValueError('A data do empréstimo não pode estar no futuro.')
            if prevista < inicio:
                raise ValueError('A devolução prevista não pode ser anterior ao empréstimo.')
            with db:
                # Bloqueia escritas concorrentes até concluir esta transação.
                db.execute('BEGIN IMMEDIATE')
                if not db.execute('SELECT id FROM alunos WHERE id = ?', (aluno_id,)).fetchone():
                    raise ValueError('Selecione um aluno cadastrado.')
                livro = db.execute('SELECT disponivel FROM livros WHERE id = ?', (livro_id,)).fetchone()
                if livro is None or not livro['disponivel']:
                    raise ValueError('Este livro não está disponível para empréstimo.')
                db.execute("""
                    INSERT INTO emprestimos (aluno_id, livro_id, data_emprestimo,
                        data_devolucao_prevista, status) VALUES (?, ?, ?, ?, 'Emprestado')
                """, (aluno_id, livro_id, inicio.isoformat(), prevista.isoformat()))
                db.execute('UPDATE livros SET disponivel = 0 WHERE id = ?', (livro_id,))
            flash('Empréstimo registrado com sucesso.', 'sucesso')
            return redirect(url_for('emprestimos'))
        except ValueError as erro:
            flash(str(erro), 'erro')
        except sqlite3.IntegrityError:
            flash('Não foi possível registrar: confira o aluno e a disponibilidade do livro.', 'erro')
    return render_template('emprestimos/formulario.html', dados=dados,
                           alunos=db.execute('SELECT * FROM alunos ORDER BY nome').fetchall(),
                           livros=db.execute('SELECT * FROM livros WHERE disponivel = 1 ORDER BY titulo').fetchall(),
                           hoje=date.today().isoformat())


@app.post('/emprestimos/<int:id>/devolver')
def emprestimo_devolver(id):
    db = get_db()
    with db:
        db.execute('BEGIN IMMEDIATE')
        emprestimo = encontrar('SELECT * FROM emprestimos WHERE id = ?', id)
        if emprestimo['status'] == 'Devolvido':
            flash('Este empréstimo já foi devolvido.', 'erro')
        else:
            db.execute("UPDATE emprestimos SET data_devolucao = ?, status = 'Devolvido' WHERE id = ?",
                       (date.today().isoformat(), id))
            db.execute('UPDATE livros SET disponivel = 1 WHERE id = ?', (emprestimo['livro_id'],))
            flash('Devolução registrada com sucesso.', 'sucesso')
    return redirect(url_for('emprestimos'))


@app.route('/historico')
def historico():
    q = request.args.get('q', '').strip()
    registros = get_db().execute("""
        SELECT e.*, a.nome, l.titulo FROM emprestimos e
        JOIN alunos a ON a.id = e.aluno_id JOIN livros l ON l.id = e.livro_id
        WHERE a.nome LIKE ? OR l.titulo LIKE ? ORDER BY e.id DESC
    """, (f'%{q}%', f'%{q}%')).fetchall()
    return render_template('historico.html', emprestimos=registros, q=q)


@app.errorhandler(sqlite3.Error)
def erro_banco(erro):
    get_db().rollback()
    app.logger.exception('Erro ao acessar o SQLite')
    return render_template('erro.html', titulo='Não foi possível concluir',
                           mensagem='O banco de dados não pôde concluir a operação. Tente novamente.'), 500


@app.errorhandler(404)
def nao_encontrado(erro):
    return render_template('erro.html', titulo='Página não encontrada',
                           mensagem='O endereço ou registro solicitado não existe.'), 404


@app.cli.command('init-db')
def criar_banco():
    """Cria as tabelas sem apagar registros e sem inserir exemplos."""
    init_db()
    print('Estrutura do banco criada. Os registros existentes foram preservados.')


if __name__ == '__main__':
    novo_banco = not Path(app.config['DATABASE']).exists()
    with app.app_context():
        init_db(with_seed=novo_banco)
    app.run(host='127.0.0.1', port=5000, debug=False)
