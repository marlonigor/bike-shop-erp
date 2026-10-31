# Bike Shop ERP

Sistema de gestao integrada para lojas de bicicletas com oficina mecanica e frente de caixa (PDV).

---

## O Problema que Resolvemos

Lojas de bicicletas com oficina enfrentam desafios diarios de operacao:
- Falta de controle sobre pecas fisicas aplicadas em manutencoes versus servicos de mao de obra cobrados.
- Furos de inventario decorrentes de vendas simultaneas no balcao e saidas de pecas para a bancada mecanica.
- Falta de rastreabilidade do historico de reparos de cada bicicleta e status dos orcamentos para os clientes.

O **Bike Shop ERP** centraliza o fluxo operacional em uma interface rapida e confiavel, garantindo controle estrito de estoque multideposito, maquina de estados para ordens de servico e vendas ageis no caixa.

---

## Publico-Alvo

- **Oficinas Mecanicas de Bicicletas:** Gerenciamento do ciclo de vida da manutencao (orcamento, aprovacao, manutencao, conclusao e entrega).
- **Lojas de Varejo / Balcao:** Venda direta no PDV com busca veloz de produtos e atualizacao imediata de estoque.
- **Gestores de Estoque:** Monitoramento de saldos, alertas de reposicao e controle por depositos independentes.

---

## Inicio Rapido (Quick Start)

### 1. Inicializacao do Ambiente

Execute o script de setup automatizado de acordo com o seu sistema operacional:

**Linux / macOS:**
```bash
./bin/setup
```

**Windows:**
```cmd
bin\setup.bat
```

O script configura o arquivo de ambiente `.env`, constroi os containers Docker, sobe o PostgreSQL e aplica as migracoes do banco.

### 2. Iniciar a Aplicacao

```bash
docker compose up
```

Acesse o sistema no navegador em `http://localhost:8000`.

### 3. Criar Usuario Administrador

Para acessar a area administrativa e cadastrar os primeiros registros:

```bash
docker compose run --rm web python manage.py createsuperuser
```

---

## Casos de Uso Principais

### 1. Gestao de Ordens de Servico (Oficina)
- Registro da bicicleta (marca, modelo, numero de quadro e queixa do cliente).
- Adicao de pecas fisicas e servicos imateriais de mao de obra com calculo automatico de subtotais e descontos.
- Maquina de estados auditada: `DRAFT` (Orcamento) -> `APPROVED` (Aprovada) -> `IN_PROGRESS` (Em Manutencao) -> `COMPLETED` (Concluida com baixa de estoque) -> `DELIVERED` (Entregue).

### 2. Frente de Caixa e PDV
- Busca dinamica de produtos por nome ou SKU.
- Selecao do deposito de saida com validacao de saldo em tempo real.
- Registro transacional da venda com garantia de atomicidade.

### 3. Estoque Multideposito
- Segregacao de estoques por localizacao (ex: Deposito Balcao, Deposito Oficina).
- Registro auditado de entradas, saidas e ajustes.
- Restricoes no banco de dados impedindo saldo negativo.

### 4. Gestao Unificada de Clientes e Catalogo
- Cadastro de clientes vinculado ao historico de compras e ordens de servico.
- Classificacao de itens de catalogo entre produtos fisicos (controlados por estoque) e servicos.

---

## Documentacao Tecnica e Contribuicao

Detalhes sobre arquitetura de software, suite de testes automatizados e diretrizes de desenvolvimento estao documentados em:

- [Arquitetura e Engenharia de Software](docs/architecture.md)
- [Guia de Contribuicao e Testes](docs/contributing.md)
