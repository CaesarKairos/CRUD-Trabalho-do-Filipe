# Biblioteca Escolar

Projeto escolar de **Modelagem de Dados e CRUD**. Organiza livros e alunos, registra empréstimos e devoluções e mantém o histórico de leituras. A interface em português usa fundo creme, cores vibrantes, bordas pretas e sombras rígidas no estilo neo-brutalista.

## Tecnologias

- Python 3.10 ou superior, Flask e Jinja2.
- SQLite pelo módulo `sqlite3` da biblioteca padrão, com SQL explícito e parametrizado.
- HTML5, CSS3 e JavaScript puro apenas para confirmar exclusões.
- Sem ORM, login, frameworks frontend ou serviços externos.

## Instalação e execução

Abra o terminal na pasta deste projeto:

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

No PowerShell, também é possível usar `.\.venv\Scripts\Activate.ps1`. Se a ativação estiver bloqueada, execute diretamente:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe app.py
```

No Linux/macOS, a ativação é `source .venv/bin/activate`.

Acesse **http://127.0.0.1:5000**. Use `Ctrl+C` no terminal para encerrar.

O banco `biblioteca.db` fica ao lado de `app.py`, independentemente da pasta de onde o Python for executado. Ao executar `python app.py` sem esse arquivo, o sistema cria as tabelas e carrega `seed.sql` com 3 alunos, 5 livros, 1 empréstimo ativo e 1 devolvido. As datas dos exemplos são relativas ao dia da criação. Inicializações posteriores preservam os dados e não repetem os exemplos.

### Criar um banco vazio

Antes da primeira execução, use:

```powershell
python -m flask --app app init-db
python app.py
```

O comando `init-db` cria as tabelas, sem exemplos e sem apagar registros existentes. `schema.sql` também pode ser executado em um editor SQLite para criar a estrutura do zero. `seed.sql` destina-se a um banco recém-criado e vazio; não deve ser reaplicado a um banco já preenchido.

Para recomeçar a demonstração, encerre o servidor, **renomeie `biblioteca.db` para guardar uma cópia** e execute `python app.py`. Não é necessário recriar o banco a cada apresentação.

## Funcionalidades

- **Início:** totais de livros, disponíveis, empréstimos ativos e alunos; últimos empréstimos ativos.
- **Alunos:** cadastrar, listar, pesquisar por nome/matrícula, editar e excluir quando não há vínculos.
- **Livros:** cadastrar, listar, pesquisar por título/autor, filtrar disponíveis, editar e excluir quando não há vínculos.
- **Empréstimos:** selecionar aluno e livro disponível, informar datas e registrar devolução com a data de hoje.
- **Histórico:** consultar empréstimos ativos e devolvidos com pesquisa por aluno ou livro.

## Modelo de Dados

```text
ALUNOS (1) ───── (N) EMPRESTIMOS (N) ───── (1) LIVROS
```

O diagrama com atributos está em [DER.md](DER.md).

| Tabela | Campos e restrições |
| --- | --- |
| alunos | `id`: INTEGER, PK, AUTOINCREMENT; `nome`: TEXT NOT NULL; `matricula`: TEXT NOT NULL UNIQUE; `turma`: TEXT NOT NULL |
| livros | `id`: INTEGER, PK, AUTOINCREMENT; `titulo` e `autor`: TEXT NOT NULL; `isbn`: TEXT opcional; `ano_publicacao`: INTEGER opcional; `disponivel`: INTEGER NOT NULL DEFAULT 1 |
| emprestimos | `id`: INTEGER, PK, AUTOINCREMENT; `aluno_id` e `livro_id`: INTEGER NOT NULL, FK; `data_emprestimo` e `data_devolucao_prevista`: DATE NOT NULL; `data_devolucao`: DATE opcional; `status`: TEXT NOT NULL DEFAULT 'Emprestado' |

- **PK (Primary Key):** identifica cada registro. `id` é a chave primária das três tabelas.
- **FK (Foreign Key):** vincula registros. `emprestimos.aluno_id → alunos.id` e `emprestimos.livro_id → livros.id`.
- **NOT NULL:** impede valores nulos. O backend também rejeita campos obrigatórios vazios ou contendo apenas espaços.
- **UNIQUE:** impede matrícula duplicada. Um índice UNIQUE parcial também impede dois empréstimos ativos do mesmo livro.
- **CHECK:** restringe disponibilidade a 0/1, status a Emprestado/Devolvido e verifica coerência das datas e do status da devolução.
- **AUTOINCREMENT:** gera automaticamente identificadores inteiros.

Um aluno pode ter vários empréstimos; um livro pode ser emprestado várias vezes, em momentos diferentes. Cada linha de `livros` representa um exemplar físico, de modo que ISBN não é único. Nomes de alunos e títulos não são duplicados em `emprestimos`: são obtidos por **JOIN**. Ao editar um nome/título, o histórico exibe seu valor atualizado.

No SQLite, os campos declarados DATE são armazenados neste projeto como texto ISO `AAAA-MM-DD`. O backend usa `date.fromisoformat` para validar as datas e a interface as mostra como `DD/MM/AAAA`.

### Consistência e regras

`PRAGMA foreign_keys = ON` é executado em **cada conexão**. Alunos e livros com qualquer empréstimo associado, inclusive devolvido, não podem ser excluídos. Não há exclusão em cascata.

O empréstimo usa `BEGIN IMMEDIATE`, verifica a disponibilidade, insere o registro e atualiza o livro na **mesma transação**. A devolução também atualiza empréstimo e livro em uma transação. O contexto `with db:` faz commit no sucesso e rollback em caso de falha. A disponibilidade é controlada pelo fluxo de empréstimo/devolução, não pelo formulário de edição do livro.

A devolução mantém o empréstimo. Repetir uma devolução antiga não libera indevidamente um livro que tenha sido emprestado novamente. As regras de sincronização devem ser usadas pelas rotas da aplicação; alterações manuais diretamente no arquivo SQLite podem desalinhar a disponibilidade.

O backend valida campos obrigatórios, matrícula única, ano entre 1 e o ano atual, existência do aluno/livro, disponibilidade e datas. A data do empréstimo não pode ser futura, e a previsão não pode ser anterior ao empréstimo. ISBN é opcional, sem validação de dígito verificador.

## Onde está o CRUD?

| Operação | Demonstração | SQL |
| --- | --- | --- |
| CREATE | Cadastrar aluno/livro ou registrar empréstimo | `INSERT INTO ... VALUES (?, ...)` |
| READ | Listagens, filtros e histórico | `SELECT`, `WHERE`, `JOIN` |
| UPDATE | Editar aluno/livro ou devolver empréstimo | `UPDATE ... SET ... WHERE id = ?` |
| DELETE | Excluir aluno/livro sem empréstimos | `DELETE FROM ... WHERE id = ?` |

Os `?` recebem parâmetros separadamente, sem concatenar dados do usuário no SQL. O Jinja2 escapa os valores exibidos no HTML. Toda alteração usa POST, e a confirmação de exclusão usa `window.confirm`.

## Estrutura

```text
app.py                       Rotas, validações e operações SQL
database.py                  Conexão e criação do banco
schema.sql                   Tabelas, PKs, FKs e restrições
seed.sql                     Exemplos iniciais
biblioteca.db                Banco local gerado na primeira execução
requirements.txt             Dependência Flask
DER.md                       Diagrama Mermaid e cardinalidades
templates/
    base.html                Layout e mensagens flash
    index.html               Dashboard
    alunos/                  Lista e formulário
    livros/                  Lista e formulário
    emprestimos/             Lista e formulário
    historico.html           Histórico com JOIN
    erro.html                Página de erro
static/css/style.css         Identidade visual e responsividade
static/js/main.js            Confirmação de exclusão
tests/test_app.py            Testes de integração
```

## Rotas

| Método | Rota | Função |
| --- | --- | --- |
| GET | `/` | Dashboard |
| GET | `/alunos` | Listagem e pesquisa |
| GET / POST | `/alunos/novo` | Cadastro |
| GET / POST | `/alunos/<id>/editar` | Edição |
| POST | `/alunos/<id>/excluir` | Exclusão |
| GET | `/livros` | Listagem e filtros |
| GET / POST | `/livros/novo` | Cadastro |
| GET / POST | `/livros/<id>/editar` | Edição |
| POST | `/livros/<id>/excluir` | Exclusão |
| GET | `/emprestimos` | Empréstimos ativos |
| GET / POST | `/emprestimos/novo` | Novo empréstimo |
| POST | `/emprestimos/<id>/devolver` | Devolução |
| GET | `/historico` | Histórico pesquisável |

## Roteiro manual para testar e apresentar

1. Em **Alunos → Cadastrar aluno**, cadastre um aluno com matrícula inédita.
2. Clique em **Editar**, altere nome, matrícula e turma e confira a listagem.
3. Em **Livros → Cadastrar livro**, informe título e autor; ISBN/ano são opcionais.
4. Edite o título ou autor e confira o resultado.
5. Em **Empréstimos → Novo empréstimo**, escolha o aluno e o livro criados e informe as datas.
6. Em **Livros**, confira o badge **Emprestado** e verifique que o livro não aparece no filtro **Apenas disponíveis**.
7. Abra outro formulário de empréstimo: o livro emprestado não estará disponível. Os testes automatizados também enviam um POST direto para confirmar que o backend bloqueia a tentativa.
8. Em **Empréstimos**, clique em **Registrar devolução**.
9. Confira que o livro voltou a **Disponível** e aparece no filtro.
10. Em **Histórico**, pesquise pelo aluno/livro e confira status **Devolvido** e data de devolução.
11. Tente excluir esse aluno/livro: o sistema informa que existem empréstimos associados. Cadastre outro aluno/livro sem vínculos e exclua-o; teste também cancelar a confirmação.
12. Tente salvar campos obrigatórios vazios. O HTML bloqueia; os testes automatizados enviam os dados vazios diretamente ao backend para verificar sua validação independente.

Adicionalmente, tente repetir uma matrícula, informar ano inválido, datas fora de ordem e pesquisar sem resultados. Para demonstrar PK/FK, abra `schema.sql` e `DER.md`; para JOIN, mostre a rota `historico` em `app.py`.

## Testes automatizados

```powershell
python -m unittest discover -s tests -v
```

Os testes usam apenas `unittest`, cliente HTTP do Flask e SQLite temporário, sem alterar `biblioteca.db`. Cobrem os 12 fluxos acima, validação no servidor, FKs, matrícula única, bloqueio de empréstimo duplicado, devolução repetida, rollback de uma falha simulada, buscas, escape de HTML, páginas e métodos HTTP. A confirmação JavaScript e a aparência visual devem ser verificadas no navegador pelo roteiro manual.

O projeto foi pensado para execução e apresentação **local**, com servidor ligado somente a `127.0.0.1` e depuração desativada.
