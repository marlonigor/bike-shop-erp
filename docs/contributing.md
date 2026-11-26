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

### Verificacao Completa e Headless
Utilize o script padronizado:

```bash
# Linux / macOS
bash bin/check

# Windows
bin\check.bat
```

O comando para na primeira falha e executa:
1. Build da imagem de desenvolvimento.
2. Tipagem estrita com mypy 2.4.1 e django-stubs 6.1.2 (ambos MIT).
3. Verificacao de configuracao com `python manage.py check`.
4. Lint e formatacao com Ruff.
5. Suite de testes unitarios, integrados e de navegador com pytest.

O mypy verifica todos os modulos de aplicacao de `core`, `catalog`, `customers`,
`sales`, `services` e `stock`, incluindo modelos, formularios, views, admin e comandos.
Tambem verifica `bikeshop` e o ponto de entrada `manage.py`.
Migrations geradas e arquivos de testes nao entram na analise estatica; os testes
continuam obrigatorios na execucao completa. A configuracao `mypy.ini` ativa
`strict`, proibe `Any` explicito e tipos desconhecidos de imports sem contrato.
`typings/decouple.pyi` descreve a API usada do python-decouple 3.8, que nao fornece
tipos. Nenhum valor de configuracao ou credencial e acessado por esse contrato.

A cobertura de aplicacao usa `.coveragerc`, com suporte ao greenlet do Playwright.
Arquivos de testes e migrations geradas ficam fora dessa medicao; nenhum teste
e desativado. Para medir, acrescente os argumentos `--cov` dos modulos desejados
ao comando de verificacao completa.

`bin/test` e `bin\\test.bat` permanecem como atalhos de lint, formatacao e pytest
para diagnosticos rapidos. Eles nao substituem `bin/check` antes da publicacao.

### Hooks Locais e CI

O setup ativa os hooks de Git. Em um checkout existente, execute uma vez:

```bash
# Linux / macOS / Git Bash
bash bin/install-hooks

# Windows
bin\install-hooks.bat
```

O instalador configura somente este repositorio e pode ser repetido. Se houver
outro `core.hooksPath`, ele interrompe a ativacao para preservar os hooks existentes.
O hook `pre-commit` executa `bin/check`; o `pre-push` executa a mesma verificacao e
a varredura de segredos. Docker precisa estar disponivel. No Windows, Git Bash
e necessario para a execucao dos hooks. Falhas bloqueiam a acao, sem alterar arquivos.

O CI chama `bash bin/check` e a mesma varredura nas branches `main`, `codex/**`
e nas pull requests para `main`. Ativar protecoes de branch no GitHub e uma
configuracao externa; estes scripts nao alteram essas protecoes.

### Testes E2E de Navegador
Os cenarios de navegador tambem rodam pelo comando padronizado `bin\\test.bat` ou
`./bin/test`. Eles usam Playwright 1.58.0 (Apache-2.0) e Chromium headless,
instalados na imagem Docker durante o build. Cada teste abre uma pagina limpa e usa
o servidor de teste isolado do Django, sem depender da massa de demonstracao local.

### Varredura de Segredos Antes do Push
Antes de publicar uma branch, execute a varredura completa do historico Git:

```bash
# Linux / macOS
./bin/scan-secrets

# Windows
bin\scan-secrets.bat
```

O script usa a imagem Docker fixada `ghcr.io/gitleaks/gitleaks:v8.30.1`, sob licenca MIT, e oculta possiveis segredos na saida. A varredura falha se encontrar uma credencial potencial; investigue e remova a origem antes do push. Nao use excecoes para ocultar credenciais reais.

### Massa de Demonstracao Local
Para popular o banco local com clientes, produtos, estoque, vendas e ordens de servico ficticias, execute:

```bash
docker compose run --rm web python manage.py seed_demo_data
```

O comando usa nomes, SKUs e e-mails com o marcador `[DEMO]` ou o dominio `example.test`. Ele nao remove dados existentes e pode ser executado novamente sem duplicar sua propria massa.

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
