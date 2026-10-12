# Banco Jupiter — Bootcamp Base API

API bancária REST desenvolvida em Python com FastAPI, PostgreSQL e SQLAlchemy. O projeto permite cadastrar e consultar clientes, abrir contas vinculadas a clientes ativos, transferir valores entre contas e consultar extratos paginados.

> **Escopo de segurança:** a API usa um token compartilhado entre serviços. Esse token não identifica individualmente um cliente nem restringe o acesso às contas de acordo com a identidade de cada pessoa. Use a aplicação somente em ambiente controlado; ela não implementa todos os mecanismos de segurança esperados de um banco voltado ao público.

## Conteúdo

- [Funcionalidades e regras de negócio](#funcionalidades-e-regras-de-negócio)
- [Tecnologias e arquitetura](#tecnologias-e-arquitetura)
- [Executar com Docker Compose](#executar-com-docker-compose)
- [Autenticação](#autenticação)
- [Endpoints](#endpoints)
- [Exemplos de requisição](#exemplos-de-requisição)
- [Erros HTTP](#erros-http)
- [Executar os testes](#executar-os-testes)
- [Configuração e segurança](#configuração-e-segurança)

## Funcionalidades e regras de negócio

### Clientes

- Cadastra clientes com nome, e-mail, CPF e data de nascimento.
- Gera uma `customer_key` para identificar o cliente.
- Permite consultar um cliente individualmente e listar clientes com filtros e paginação.
- Registra eventos de alteração de status.
- O cadastro valida o formato e os dígitos verificadores do CPF, a unicidade de CPF e e-mail, a data de nascimento e a faixa etária permitida pelo código atual (18 a 80 anos).
- O e-mail é normalizado para letras minúsculas.
- O status inicial é `pending_kyc`. O endpoint de atualização permite solicitar `active`, `blocked` ou `inactive`; pelas regras atuais, a alteração só é permitida enquanto o cliente estiver em `pending_kyc`.

### Contas

- Somente clientes com status `active` podem abrir contas.
- A conta recebe uma `account_key` e começa com saldo zero.
- A consulta de conta retorna a chave, o saldo, o cliente associado e o tier.

### Transferências

- A transferência é criada em `POST /accounts/{account_key}/transactions`.
- O valor é informado em centavos inteiros: `1000` representa R$ 10,00.
- O valor precisa ser um inteiro positivo, e a conta de origem deve ser diferente da conta de destino.
- Os clientes associados às contas de origem e destino precisam estar ativos.
- O saldo da origem precisa cobrir o valor da transferência e a tarifa aplicável.
- A API aplica a regra de franquia mensal e tarifa implementada no código.
- A chave `Idempotency-Key` é opcional. Quando enviada, permite repetir uma requisição sem criar uma segunda movimentação, desde que a chave seja reutilizada com os mesmos dados relevantes. Reutilizá-la com dados diferentes gera conflito.

### Extrato

- Lista movimentações de uma conta, com paginação e filtros opcionais de data.
- Cada item informa direção (`debit` ou `credit`), valor, tarifa, contraparte e data de criação.

## Tecnologias e arquitetura

- Python 3.11
- FastAPI
- PostgreSQL 16
- SQLAlchemy
- Alembic para migrations
- Docker e Docker Compose
- Pytest e pytest-cov

A aplicação separa responsabilidades em camadas:

| Diretório/camada | Responsabilidade |
|---|---|
| `src/app.py` | Criação da aplicação e registro das rotas e handlers de erro |
| `src/middlewares/` | Token interno, contexto da requisição e logs |
| `src/schemas/` | Validação do formato de corpos e parâmetros de consulta por JSON Schema |
| `src/resources/` | Integração HTTP: recebe requisições e produz respostas |
| `src/controllers/` | Regras de negócio e coordenação dos fluxos |
| `src/repositories/` | Consultas e persistência usando SQLAlchemy |
| `src/models/` | Modelos das entidades e tabelas |
| `src/dtos/` | Conversão dos modelos para estruturas de resposta |
| `database/` e `migrations/` | Configuração do banco e evolução do schema |
| `tests/` | Testes unitários e de integração |

As interfaces Swagger, ReDoc e OpenAPI estão desabilitadas em `src/app.py`. Os formatos de entrada podem ser consultados nos arquivos JSON em `src/schemas/`.

## Executar com Docker Compose

### Pré-requisitos

- Git
- Docker Engine
- Docker Compose v2 (`docker compose`)

### 1. Clonar o repositório

```bash
git clone <URL_DO_REPOSITORIO>
cd Banco-Jupiter
```

Substitua `<URL_DO_REPOSITORIO>` pela URL real do repositório.

### 2. Configurar variáveis de ambiente

O Compose atual define valores padrão para algumas variáveis, inclusive `INTERNAL_TOKEN`. Para personalizar a configuração, crie um arquivo `.env`:

```bash
cp .env.example .env
```

Edite o arquivo e configure pelo menos um `INTERNAL_TOKEN` próprio. Para gerar um valor aleatório:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

Copie o resultado para a linha `INTERNAL_TOKEN=` no `.env`. Não compartilhe esse valor nem versione o arquivo `.env`.

> **Importante:** no `docker-compose.yml` deste projeto, `INTERNAL_TOKEN` possui atualmente o valor padrão `default_token` quando não configurado. Esse padrão é conveniente para desenvolvimento, mas não é seguro para produção. Sempre configure um valor próprio e revise a configuração antes de disponibilizar o serviço em qualquer ambiente compartilhado.

### 3. Construir e iniciar os serviços

```bash
sudo docker compose up -d --build
```

O Compose inicia a API e o PostgreSQL. A inicialização da API executa as migrations do Alembic antes de iniciar o servidor Uvicorn.

Se sua instalação exigir permissões administrativas para Docker, use `sudo` antes dos comandos.

### 4. Verificar os containers

```bash
sudo docker compose ps
```

A API fica disponível em `http://localhost:3000` por padrão. O PostgreSQL é publicado na porta `5432` por padrão. As portas podem ser personalizadas pelas variáveis `API_PORT` e `DB_PORT` do `.env`.

### 5. Verificar a API

A rota raiz retorna a identificação do serviço:

```bash
curl -i http://localhost:3000/
```

A verificação de saúde não exige token e retorna `204 No Content`:

```bash
curl -i http://localhost:3000/health_check
```

### 6. Consultar logs e parar os serviços

```bash
sudo docker compose logs -f api
```

Para parar os containers:

```bash
sudo docker compose down
```

Esse comando não remove o código-fonte. Antes de remover volumes ou recriar o banco, confirme se não há dados que precisem ser preservados.

## Autenticação

Todas as rotas, exceto `GET /` e `GET /health_check`, exigem o cabeçalho `INTERNAL-TOKEN` com o valor configurado em `INTERNAL_TOKEN`:

```http
INTERNAL-TOKEN: SEU_TOKEN_CONFIGURADO
```

Exemplo com `curl`:

```bash
curl -H "INTERNAL-TOKEN: $INTERNAL_TOKEN" \
  http://localhost:3000/customers
```

O middleware compara o token recebido com o valor configurado na API. Como o token é compartilhado, ele autentica o chamador como serviço autorizado, mas não fornece identidade individual de cliente nem autorização por conta.

## Endpoints

Todas as rotas abaixo, exceto `GET /` e `GET /health_check`, exigem `INTERNAL-TOKEN`.

| Método | Rota | Descrição | Sucesso esperado |
|---|---|---|---|
| `GET` | `/` | Identificação do serviço | `200 OK` |
| `GET` | `/health_check` | Verificação de saúde | `204 No Content` |
| `POST` | `/customers` | Cadastra cliente | `201 Created` |
| `GET` | `/customers/{customer_key}` | Consulta cliente e eventos de status | `200 OK` |
| `GET` | `/customers` | Lista clientes com filtros e paginação | `200 OK` |
| `PUT` | `/customers/{customer_key}` | Atualiza status do cliente | `202 Accepted` no código atual |
| `POST` | `/accounts` | Abre conta para cliente ativo | `201 Created` |
| `GET` | `/accounts/{account_key}` | Consulta conta e saldo | `200 OK` |
| `POST` | `/accounts/{account_key}/transactions` | Cria transferência | `201 Created` |
| `GET` | `/accounts/{account_key}/transactions` | Consulta extrato paginado | `200 OK` |

### Parâmetros de consulta

#### `GET /customers`

| Parâmetro | Tipo/formato | Descrição |
|---|---|---|
| `page` | Inteiro positivo; padrão definido pela aplicação | Número da página |
| `limit` | Inteiro entre 1 e 100; padrão definido pela aplicação | Quantidade por página |
| `status` | Repetível: `pending_kyc`, `active`, `blocked`, `inactive` | Filtra por status |
| `name` | Texto | Filtra por nome |
| `email` | Texto | Filtra por e-mail |
| `document_number` | `000.000.000-00` | Filtra por CPF formatado |
| `birthdate_from` | `AAAA-MM-DD` | Data de nascimento inicial |
| `birthdate_to` | `AAAA-MM-DD` | Data de nascimento final |

Exemplo: `GET /customers?status=active&status=pending_kyc&page=1&limit=20`.

A resposta contém `data`, `limit`, `page` e `is_last_page`.

#### `GET /accounts/{account_key}/transactions`

| Parâmetro | Tipo/formato | Descrição |
|---|---|---|
| `page` | Inteiro positivo; padrão definido pela aplicação | Número da página |
| `limit` | Inteiro entre 1 e 100; padrão definido pela aplicação | Quantidade por página |
| `start_date` | `AAAA-MM-DD` | Data inicial do filtro |
| `end_date` | `AAAA-MM-DD` | Data final do filtro |

As datas são inclusivas como dias de calendário. Se as duas forem informadas, `start_date` não pode ser posterior a `end_date`. A resposta contém `items` e `pagination` (`total_items`, `page`, `limit`).

## Exemplos de requisição

Nos exemplos abaixo, substitua `SEU_TOKEN_CONFIGURADO` por um valor igual ao `INTERNAL_TOKEN` configurado no ambiente.

### Cadastrar cliente

```bash
curl -X POST http://localhost:3000/customers \
  -H 'Content-Type: application/json' \
  -H 'INTERNAL-TOKEN: SEU_TOKEN_CONFIGURADO' \
  -d '{
    "name": "Maria da Silva",
    "email": "maria@example.com",
    "document_number": "529.982.247-25",
    "birthdate": "1995-06-15"
  }'
```

A resposta de sucesso contém a chave gerada:

```json
{
  "customer_key": "UUID_DO_CLIENTE"
}
```

O CPF de exemplo é conhecido publicamente e serve apenas para ilustrar o formato; use dados de teste adequados no seu ambiente.

### Consultar cliente

```bash
curl http://localhost:3000/customers/UUID_DO_CLIENTE \
  -H 'INTERNAL-TOKEN: SEU_TOKEN_CONFIGURADO'
```

A resposta inclui `customer_key`, `name`, `email`, `document_number`, `birthdate`, `status` e `status_events`.

### Ativar cliente

```bash
curl -X PUT http://localhost:3000/customers/UUID_DO_CLIENTE \
  -H 'Content-Type: application/json' \
  -H 'INTERNAL-TOKEN: SEU_TOKEN_CONFIGURADO' \
  -d '{"status":"active"}'
```

A operação atual só permite alterar o status de clientes que ainda estão em `pending_kyc`.

### Abrir conta

```bash
curl -X POST http://localhost:3000/accounts \
  -H 'Content-Type: application/json' \
  -H 'INTERNAL-TOKEN: SEU_TOKEN_CONFIGURADO' \
  -d '{"customer_key":"UUID_DO_CLIENTE"}'
```

A resposta contém a `account_key` gerada. Consulte a conta com `GET /accounts/{account_key}`.

### Realizar transferência

```bash
curl -X POST http://localhost:3000/accounts/UUID_DA_CONTA_ORIGEM/transactions \
  -H 'Content-Type: application/json' \
  -H 'INTERNAL-TOKEN: SEU_TOKEN_CONFIGURADO' \
  -H 'Idempotency-Key: transferencia-pedido-001' \
  -d '{
    "destination_account_key": "UUID_DA_CONTA_DESTINO",
    "amount": 1500
  }'
```

O exemplo solicita uma transferência de 1500 centavos (R$ 15,00). A resposta contém `transaction_key`, `amount`, `fee_amount` e `is_fee_exempt`.

Se enviar `Idempotency-Key`, reutilize a mesma chave apenas para repetir a mesma operação. Uma chave já usada com dados diferentes gera conflito.

### Consultar extrato

```bash
curl 'http://localhost:3000/accounts/UUID_DA_CONTA/transactions?page=1&limit=20&start_date=2026-01-01&end_date=2026-01-31' \
  -H 'INTERNAL-TOKEN: SEU_TOKEN_CONFIGURADO'
```

A resposta contém uma lista `items` e os metadados em `pagination`. Cada item apresenta `transaction_key`, `direction`, `amount`, `fee_amount`, `counterparty_account_key` e `created_at`.

## Erros HTTP

Os erros de domínio retornam um objeto JSON com os campos `title`, `description`, `translation` e `code`. Os códigos específicos estão definidos em `src/errors/`.

| HTTP | Situação típica |
|---|---|
| `400 Bad Request` | Corpo ou parâmetros de consulta inválidos |
| `403 Forbidden` | Token interno ausente ou incorreto |
| `404 Not Found` | Cliente, conta ou rota não encontrados |
| `405 Method Not Allowed` | Método HTTP não permitido para a rota |
| `409 Conflict` | CPF/e-mail duplicado, alteração de status incompatível ou conflito de idempotência |
| `422 Unprocessable Entity` | CPF/data inválidos, cliente inativo, saldo insuficiente ou transferência inválida |
| `500 Internal Server Error` | Erro inesperado no servidor |

O código e a descrição específicos dependem da exceção lançada. Consulte `src/errors/base_error.py` e `src/errors/custom_errors.py` para os detalhes completos.

## Executar os testes

A imagem `api` instala as dependências de desenvolvimento e copia os testes para `/tests`. Os testes de integração dependem do banco PostgreSQL e podem recriar o schema; execute-os apenas contra um banco descartável, nunca contra dados importantes.

### 1. Construir e iniciar

```bash
cp .env.example .env
sudo docker compose build api
sudo docker compose up -d
```

Espere os serviços ficarem saudáveis:

```bash
sudo docker compose ps
```

### 2. Executar todos os testes dentro do container

```bash
sudo docker compose exec api python -m pytest /tests -v
```

### 3. Executar com cobertura

```bash
sudo docker compose exec api python -m pytest /tests --cov=/app --cov-report=term-missing
```

### 4. Executar apenas uma categoria ou arquivo

```bash
# Testes de integração
sudo docker compose exec api python -m pytest /tests/integration -v

# Um arquivo específico
sudo docker compose exec api python -m pytest /tests/integration/test_transactions.py -v
```

Se o Docker estiver configurado para exigir privilégios administrativos, acrescente `sudo` aos comandos `docker compose`.

## Configuração e segurança

As principais variáveis utilizadas no Compose estão documentadas em `.env.example`:

| Variável | Finalidade | Padrão no Compose atual |
|---|---|---|
| `APP_ENV` | Ambiente e nível de log | `local` |
| `SERVICE_NAME` | Nome informado pela rota raiz | `bootcamp-api` |
| `INTERNAL_TOKEN` | Token exigido pelo middleware | `default_token` (não seguro para produção) |
| `API_PORT` | Porta publicada da API no host | `3000` |
| `DB_PORT` | Porta publicada do PostgreSQL no host | `5432` |
| `BANKSLIP_API_URL` | URL do serviço externo de boletos | `http://localhost:8080` |
| `BANKSLIP_API_INTERNAL_TOKEN` | Token enviado ao serviço de boletos | `default_token` |
| `BANKSLIP_API_TIMEOUT` | Timeout de chamada ao serviço de boletos | `5` segundos |

O `DATABASE_URL` dentro do Compose aponta para o serviço `db`. Para conexões feitas diretamente da máquina host, o `.env.example` mostra uma URL usando `localhost`.

Boas práticas para a entrega e para o desenvolvimento:

1. Não versione `.env` nem credenciais reais.
2. Configure um `INTERNAL_TOKEN` aleatório e diferente do valor padrão.
3. Não exponha a API diretamente à internet sem adicionar autenticação e autorização adequadas.
4. Não use dados pessoais reais nos testes.
5. Confirme a visibilidade do repositório no GitHub e revise os arquivos versionados antes de entregar.
rviço externo de boletos é configurado por variáveis de ambiente. A disponibilidade desse serviço não é garantida pelo próprio Banco Jupiter.
