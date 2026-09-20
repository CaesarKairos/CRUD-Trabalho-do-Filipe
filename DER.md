# Diagrama Entidade-Relacionamento

```mermaid
erDiagram
    ALUNOS ||--o{ EMPRESTIMOS : realiza
    LIVROS ||--o{ EMPRESTIMOS : possui

    ALUNOS {
        INTEGER id PK "AUTOINCREMENT"
        TEXT nome "NOT NULL"
        TEXT matricula UK "NOT NULL, UNIQUE"
        TEXT turma "NOT NULL"
    }
    LIVROS {
        INTEGER id PK "AUTOINCREMENT"
        TEXT titulo "NOT NULL"
        TEXT autor "NOT NULL"
        TEXT isbn "Opcional"
        INTEGER ano_publicacao "Opcional"
        INTEGER disponivel "NOT NULL, DEFAULT 1"
    }
    EMPRESTIMOS {
        INTEGER id PK "AUTOINCREMENT"
        INTEGER aluno_id FK "NOT NULL"
        INTEGER livro_id FK "NOT NULL"
        DATE data_emprestimo "NOT NULL"
        DATE data_devolucao_prevista "NOT NULL"
        DATE data_devolucao "Opcional enquanto ativo"
        TEXT status "NOT NULL, DEFAULT Emprestado"
    }
```

- Um aluno realiza **zero ou muitos empréstimos**. Cada empréstimo pertence a **exatamente um aluno**.
- Um livro possui **zero ou muitos empréstimos ao longo do tempo**. Cada empréstimo refere-se a **exatamente um livro**.
- Cada registro de livro representa **um exemplar físico**. Exemplares do mesmo título podem ter o mesmo ISBN; por isso ISBN não é UNIQUE.
- `aluno_id` referencia `alunos.id`; `livro_id` referencia `livros.id`.
- Não há cópias do nome do aluno ou título do livro em empréstimos: as consultas usam JOIN.
- Um índice UNIQUE parcial permite apenas um empréstimo com status `Emprestado` por livro.
- As FKs usam `ON DELETE RESTRICT`: nem mesmo o histórico devolvido é apagado por exclusão de aluno ou livro.

O Mermaid pode ser visualizado em leitores Markdown compatíveis. A definição SQL completa está em [schema.sql](schema.sql).
