# Guia de Contribuicao e Desenvolvimento

Este documento reune os procedimentos para configuracao do ambiente de desenvolvimento, execucao de testes e padroes de engenharia do Bike Shop ERP.

---

## 1. Ambiente de Desenvolvimento

### Pre-requisitos
- Docker e Docker Compose instalados.
- Python 3.12+ (caso deseje rodar ferramental localmente fora de containers).

### Configuracao Inicial
Execute o script correspondente a sua plataforma:

```bash
# Linux / macOS
./bin/setup

# Windows
bin\setup.bat
```

O comando realiza a copia do `.env.example` para `.env`, o build da imagem Docker da aplicacao web e a execucao das migracoes do Django.

---

## 2. Testes e Qualidade de Codigo

Toda contribuicao de codigo deve passar pela suite de testes e respeitar as regras do linter antes de ser submetida.

### Execucao da Suite de Testes Headless
Utilize o script padronizado:

```bash
# Linux / macOS
./bin/test

# Windows
bin\test.bat
```

O script executa em sequencia:
1. Verificacao de regras de lint com `ruff check .`
2. Checagem de formatacao com `ruff format --check .`
3. Suite de testes unitarios e integrados com `pytest`

### Execucao Manual via Ambiente Local
Caso utilize ambiente virtual (`.venv`):

```bash
# Linter e Formatador
ruff check .
ruff format .

# Suite Pytest
pytest
```

---

## 3. Padroes de Codigo

- **Single Responsibility Principle:** Cada modulo e funcao deve possuir responsabilidade unica e bem delimitada.
- **Tamanho de Funcoes:** Manter entre 4 e 20 linhas.
- **Tamanho de Arquivos:** Manter abaixo de 500 linhas.
- **Tipagem Explicita:** Obrigatoria em todas as assinaturas de funcoes e metodos. Proibido o uso de `any` ou dicionarios genericos sem tipagem.
- **Emojis:** Expressamente proibido o uso de emojis em codigo, documentacao, commits, logs ou interface.
- **Comentarios:** Documente a motivacao de negocio e restricoes de dominio (por que foi feito), evitando parafrasear a sintaxe do codigo.

---

## 4. Convencoes de Commit

Adotamos a convencao de **Conventional Commits** exclusivamente em lingua inglesa:

- `feat(scope): add new capability`
- `fix(scope): correct identified bug or regression`
- `docs(scope): update documentation or specifications`
- `refactor(scope): restructure code without changing behavior`
- `test(scope): add or improve test coverage`
