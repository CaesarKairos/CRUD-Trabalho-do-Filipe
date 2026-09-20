-- Executado somente quando o banco é criado pela primeira vez.
BEGIN;
INSERT INTO alunos (nome, matricula, turma) VALUES
    ('Ana Souza', '2026001', '1º A'),
    ('Bruno Lima', '2026002', '2º B'),
    ('Clara Santos', '2026003', '3º A');

INSERT INTO livros (titulo, autor, isbn, ano_publicacao) VALUES
    ('Dom Casmurro', 'Machado de Assis', NULL, 1899),
    ('O Pequeno Príncipe', 'Antoine de Saint-Exupéry', NULL, 1943),
    ('A Hora da Estrela', 'Clarice Lispector', NULL, 1977),
    ('O Cortiço', 'Aluísio Azevedo', NULL, 1890),
    ('Vidas Secas', 'Graciliano Ramos', NULL, 1938);

INSERT INTO emprestimos (aluno_id, livro_id, data_emprestimo,
    data_devolucao_prevista, data_devolucao, status)
VALUES (1, 1, date('now', 'localtime', '-20 days'),
    date('now', 'localtime', '-6 days'), date('now', 'localtime', '-8 days'), 'Devolvido');

INSERT INTO emprestimos (aluno_id, livro_id, data_emprestimo, data_devolucao_prevista)
VALUES (2, 2, date('now', 'localtime', '-2 days'), date('now', 'localtime', '+12 days'));
UPDATE livros SET disponivel = 0 WHERE id = 2;
COMMIT;
