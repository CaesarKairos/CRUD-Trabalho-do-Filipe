"""Testes de integração: HTTP pelo cliente Flask e banco SQLite temporário."""
import sqlite3
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

from app import app
from database import get_db, init_db


class BibliotecaTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.config_anterior = dict(app.config)
        app.config.update(TESTING=True, DATABASE=str(Path(self.temp.name) / 'teste.db'))
        self.client = app.test_client()
        with app.app_context():
            init_db()

    def tearDown(self):
        app.config.update(self.config_anterior)
        self.temp.cleanup()

    def sql(self, consulta, parametros=()):
        with app.app_context():
            return get_db().execute(consulta, parametros).fetchall()

    def post(self, caminho, dados=None):
        resposta = self.client.post(caminho, data=dados, follow_redirects=True)
        self.assertEqual(resposta.status_code, 200)
        return resposta.get_data(as_text=True)

    def cadastros(self):
        self.post('/alunos/novo', {'nome': 'Ana', 'matricula': '001', 'turma': '1 A'})
        self.post('/livros/novo', {'titulo': 'Livro teste', 'autor': 'Autora'})

    def dados_emprestimo(self):
        return {'aluno_id': '1', 'livro_id': '1', 'data_emprestimo': date.today().isoformat(),
                'data_devolucao_prevista': (date.today() + timedelta(days=14)).isoformat()}

    def test_fluxo_completo_crud_emprestimo_devolucao(self):
        self.cadastros()
        self.assertEqual(self.sql('SELECT nome FROM alunos')[0]['nome'], 'Ana')
        self.assertEqual(self.sql('SELECT titulo FROM livros')[0]['titulo'], 'Livro teste')
        self.assertIn('Aluno atualizado com sucesso.', self.post('/alunos/1/editar',
                      {'nome': 'Ana Souza', 'matricula': '002', 'turma': '2 B'}))
        self.assertIn('Livro atualizado com sucesso.', self.post('/livros/1/editar',
                      {'titulo': 'Histórias', 'autor': 'Autor', 'isbn': '123', 'ano_publicacao': '2000'}))
        self.assertEqual(self.sql('SELECT matricula FROM alunos')[0]['matricula'], '002')
        self.assertEqual(self.sql('SELECT titulo FROM livros')[0]['titulo'], 'Histórias')
        self.assertIn('Empréstimo registrado com sucesso.', self.post('/emprestimos/novo', self.dados_emprestimo()))
        self.assertEqual(self.sql('SELECT disponivel FROM livros')[0]['disponivel'], 0)
        self.assertIn('Emprestado', self.client.get('/livros').get_data(as_text=True))
        self.assertNotIn('Histórias', self.client.get('/livros?disponiveis=1').get_data(as_text=True))
        self.assertIn('não está disponível', self.post('/emprestimos/novo', self.dados_emprestimo()))
        self.assertEqual(len(self.sql('SELECT * FROM emprestimos')), 1)
        for caminho in ['/alunos/1/excluir', '/livros/1/excluir']:
            self.assertIn('existem empréstimos associados', self.post(caminho))
        self.assertIn('Devolução registrada com sucesso.', self.post('/emprestimos/1/devolver'))
        self.assertEqual(self.sql('SELECT disponivel FROM livros')[0]['disponivel'], 1)
        emprestimo = self.sql('SELECT * FROM emprestimos')[0]
        self.assertEqual(emprestimo['status'], 'Devolvido')
        self.assertEqual(emprestimo['data_devolucao'], date.today().isoformat())
        historico = self.client.get('/historico').get_data(as_text=True)
        for texto in ['Ana Souza', 'Histórias', 'Devolvido']:
            self.assertIn(texto, historico)
        # Histórico também impede exclusão após a devolução.
        self.assertIn('existem empréstimos associados', self.post('/alunos/1/excluir'))
        self.assertIn('existem empréstimos associados', self.post('/livros/1/excluir'))
        # Reenviar uma devolução antiga não pode liberar um novo empréstimo.
        self.post('/emprestimos/novo', self.dados_emprestimo())
        self.assertIn('já foi devolvido', self.post('/emprestimos/1/devolver'))
        self.assertEqual(self.sql('SELECT disponivel FROM livros')[0]['disponivel'], 0)
        self.assertEqual(len(self.sql('SELECT * FROM emprestimos')), 2)

    def test_exclusao_sem_relacionamentos_e_metodo_http(self):
        self.cadastros()
        for caminho in ['/alunos/1/excluir', '/livros/1/excluir', '/emprestimos/1/devolver']:
            self.assertEqual(self.client.get(caminho).status_code, 405)
        self.assertIn('Aluno excluído com sucesso.', self.post('/alunos/1/excluir'))
        self.assertIn('Livro excluído com sucesso.', self.post('/livros/1/excluir'))
        self.assertFalse(self.sql('SELECT * FROM alunos'))
        self.assertFalse(self.sql('SELECT * FROM livros'))

    def test_validacao_backend_e_matricula_unica(self):
        for caminho, dados in [('/alunos/novo', {'nome': ' ', 'matricula': '1', 'turma': 'A'}),
                               ('/livros/novo', {'titulo': ' ', 'autor': 'A'}),
                               ('/emprestimos/novo', {})]:
            self.assertIn('Preencha os campos obrigatórios.', self.post(caminho, dados))
        self.cadastros()
        self.assertIn('Já existe um aluno', self.post('/alunos/novo', {'nome': 'Outro', 'matricula': '001', 'turma': 'B'}))
        for ano in ['abc', '-1', '1.5', str(date.today().year + 1)]:
            self.assertIn('ano de publicação válido', self.post('/livros/novo', {'titulo': 'X', 'autor': 'Y', 'ano_publicacao': ano}))
        self.assertEqual(len(self.sql('SELECT * FROM alunos')), 1)
        self.assertEqual(len(self.sql('SELECT * FROM livros')), 1)

    def test_datas_ids_invalidos_e_rollback(self):
        self.cadastros()
        for alteracao in [{'data_emprestimo': 'data inválida'}, {'data_devolucao_prevista': '2000-01-01'},
                          {'data_emprestimo': (date.today() + timedelta(days=1)).isoformat()},
                          {'aluno_id': '999'}, {'livro_id': '999'}, {'aluno_id': 'abc'}]:
            self.post('/emprestimos/novo', {**self.dados_emprestimo(), **alteracao})
            self.assertFalse(self.sql('SELECT * FROM emprestimos'))
            self.assertEqual(self.sql('SELECT disponivel FROM livros')[0]['disponivel'], 1)
        # Simula falha na segunda escrita: a primeira deve ser desfeita.
        with app.app_context():
            get_db().execute("""CREATE TRIGGER falha_update BEFORE UPDATE ON livros
                BEGIN SELECT RAISE(ABORT, 'Falha simulada'); END""")
            get_db().commit()
        self.post('/emprestimos/novo', self.dados_emprestimo())
        self.assertFalse(self.sql('SELECT * FROM emprestimos'))
        self.assertEqual(self.sql('SELECT disponivel FROM livros')[0]['disponivel'], 1)

    def test_fk_e_indice_unico_no_banco(self):
        self.cadastros()
        with app.app_context():
            db = get_db()
            self.assertEqual(db.execute('PRAGMA foreign_keys').fetchone()[0], 1)
            with self.assertRaises(sqlite3.IntegrityError), db:
                db.execute("""INSERT INTO emprestimos (aluno_id, livro_id, data_emprestimo, data_devolucao_prevista)
                    VALUES (999, 1, '2026-01-01', '2026-01-15')""")
        self.post('/emprestimos/novo', self.dados_emprestimo())
        with app.app_context():
            db = get_db()
            with self.assertRaises(sqlite3.IntegrityError), db:
                db.execute("""INSERT INTO emprestimos (aluno_id, livro_id, data_emprestimo, data_devolucao_prevista)
                    VALUES (1, 1, '2026-01-01', '2026-01-15')""")

    def test_paginas_pesquisas_seed_e_escape(self):
        with app.app_context():
            init_db(with_seed=True)
            init_db()  # Recriar a estrutura não deve apagar os dados.
        for caminho in ['/', '/alunos', '/alunos/novo', '/alunos/1/editar', '/livros', '/livros/novo',
                        '/livros/1/editar', '/emprestimos', '/emprestimos/novo', '/historico',
                        '/static/css/style.css', '/static/js/main.js']:
            with self.subTest(caminho=caminho):
                with self.client.get(caminho) as resposta:
                    self.assertEqual(resposta.status_code, 200)
        for caminho in ['/alunos/999/editar', '/livros/999/editar', '/nao-existe']:
            self.assertEqual(self.client.get(caminho).status_code, 404)
        self.assertEqual(self.client.post('/emprestimos/999/devolver').status_code, 404)
        for caminho, termo, esperado, ausente in [('/alunos', '2026001', 'Ana Souza', 'Bruno Lima'),
                                                 ('/livros', 'Machado', 'Dom Casmurro', 'Vidas Secas'),
                                                 ('/historico', 'Bruno', 'O Pequeno Príncipe', 'Dom Casmurro')]:
            pagina = self.client.get(caminho, query_string={'q': termo}).get_data(as_text=True)
            self.assertIn(esperado, pagina)
            self.assertNotIn(ausente, pagina)
        pagina = self.client.get('/alunos', query_string={'q': "' OR 1=1 --"}).get_data(as_text=True)
        self.assertNotIn('Ana Souza', pagina)
        pagina = self.post('/alunos/novo', {'nome': '<script>alert(1)</script>', 'matricula': 'X', 'turma': 'A'})
        self.assertNotIn('<script>alert(1)</script>', pagina)
        self.assertIn('&lt;script&gt;', pagina)
        self.assertFalse(self.sql('PRAGMA foreign_key_check'))


if __name__ == '__main__':
    unittest.main()
