PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS alunos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL CHECK (length(trim(nome)) > 0),
    matricula TEXT NOT NULL UNIQUE CHECK (length(trim(matricula)) > 0),
    turma TEXT NOT NULL CHECK (length(trim(turma)) > 0)
);

CREATE TABLE IF NOT EXISTS livros (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    titulo TEXT NOT NULL CHECK (length(trim(titulo)) > 0),
    autor TEXT NOT NULL CHECK (length(trim(autor)) > 0),
    isbn TEXT,
    ano_publicacao INTEGER CHECK (ano_publicacao BETWEEN 1 AND 9999),
    disponivel INTEGER NOT NULL DEFAULT 1 CHECK (disponivel IN (0, 1))
);

CREATE TABLE IF NOT EXISTS emprestimos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    aluno_id INTEGER NOT NULL,
    livro_id INTEGER NOT NULL,
    data_emprestimo DATE NOT NULL,
    data_devolucao_prevista DATE NOT NULL,
    data_devolucao DATE,
    status TEXT NOT NULL DEFAULT 'Emprestado'
        CHECK (status IN ('Emprestado', 'Devolvido')),
    FOREIGN KEY (aluno_id) REFERENCES alunos(id) ON DELETE RESTRICT,
    FOREIGN KEY (livro_id) REFERENCES livros(id) ON DELETE RESTRICT,
    CHECK (data_devolucao_prevista >= data_emprestimo),
    CHECK (data_devolucao IS NULL OR data_devolucao >= data_emprestimo),
    CHECK ((status = 'Emprestado' AND data_devolucao IS NULL)
        OR (status = 'Devolvido' AND data_devolucao IS NOT NULL))
);

-- Um livro pode ter muitos empréstimos históricos, mas apenas um ativo.
CREATE UNIQUE INDEX IF NOT EXISTS um_emprestimo_ativo_por_livro
    ON emprestimos(livro_id) WHERE status = 'Emprestado';
