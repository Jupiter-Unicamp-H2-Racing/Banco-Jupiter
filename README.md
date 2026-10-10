**# Banco Jupiter (bootcamp-base-api)**



API bancária mínima em Python (FastAPI + PostgreSQL + SQLAlchemy). Cadastra **\*\*clientes\*\***, abre **\*\*contas\*\*** vinculadas a clientes ativos, move dinheiro entre contas com **\*\*transações\*\*** que respeitam saldo e **\*\*tarifa\*\***, e devolve o **\*\*extrato\*\*** paginado de cada conta.



> **\*\*Aviso de entrega (13/10):\*\*** o repositório precisa estar **\*\*público\*\*** na entrega. Veja o [checklist]\(#entrega-repositório-público-em-1310) no fim deste arquivo.



## Sumário**



- [O que o sistema faz]\(#o-que-o-sistema-faz)

- [Como subir]\(#como-subir)

- [Autenticação e variáveis de ambiente]\(#autenticação-e-variáveis-de-ambiente)

- [Rotas]\(#rotas)

- [Como testar]\(#como-testar)

- [Camadas]\(#camadas)

- [Decisões de modelagem]\(#decisões-de-modelagem)

- [Entrega: repositório público em 13/10]\(#entrega-repositório-público-em-1310)



## O que o sistema faz**



| Conceito | Regra |

|---|---|

| **\*\*Cliente\*\*** | Nasce em `pending_kyc`. Exige CPF válido (dígitos verificadores), e-mail e CPF únicos, idade entre 18 e 80 anos. O status só pode sair de `pending_kyc` **\*\*uma vez\*\***, para `active`, `blocked` ou `inactive`; depois disso é final (`409`). |

| **\*\*Conta\*\*** | Sempre vinculada a um cliente, e só clientes `active` abrem conta (`422` caso contrário). Pode nascer com `initial_balance` (padrão `0`). |

| **\*\*Transação\*\*** | Transferência de uma conta de origem para outra de destino. A origem paga `amount + tarifa`, o destino recebe só `amount`. Rejeita saldo insuficiente, conta inexistente e transferência para a própria conta. |

| **\*\*Extrato\*\*** | Lista paginada das transações em que a conta é origem (`debit`) ou destino (`credit`), da mais nova para a mais antiga, com filtro opcional por período. |



Todo valor monetário é **\*\*inteiro em centavos\*\***: `10000` = R$ 100,00.



### Regra da tarifa**



1\. Cada conta tem uma **\*\*franquia mensal\*\*** de transferências gratuitas (`monthly_free_transfers_limit`, padrão **\*\*5\*\***).

2\. A contagem considera as transferências em que a conta foi **\*\*origem\*\*** no **\*\*mês-calendário UTC\*\*** corrente, lidas da tabela `transaction` (a virada do mês é automática, não há contador para zerar).

3\. Dentro da franquia: tarifa **\*\*0\*\***.

4\. Esgotada a franquia: tarifa de **\*\*50 centavos (R$ 0,50)\*\***, **\*\*exceto\*\*** se o saldo da origem *\*imediatamente antes\** da transferência for **\*\*≥ 100000 centavos (R$ 1.000,00)\*\***; nesse caso a tarifa é 0.

5\. A origem precisa ter `saldo >= amount + tarifa`; senão, `422` (`QIT002002`).

6\. A tarifa cobrada (inclusive `0`) fica gravada em `transaction.fee_amount`. Ela é descontada da origem e **\*\*não é creditada a nenhuma conta\*\***.



A regra mora em `src/utils/transaction_fee.py`; o detalhe está em `docs/transaction-fee.md`.



## Como executar o projeto do zero

### 1. Pré-requisitos

Você precisa de Git, Docker Engine, Docker Compose e Python 3.11+ para rodar os testes.

Confira as ferramentas no terminal:

```bash
git --version
docker --version
docker compose version
python3 --version
```

### 2. Baixar o projeto

Clone o repositório e entre na pasta que contém `docker-compose.yml`:

```bash
git clone <url-do-repositório>
cd bootcamp-base-api
ls
```

Troque `<url-do-repositório>` pela URL real do projeto no GitHub. Se o projeto já estiver clonado, basta entrar na pasta correta.

### 3. Construir e iniciar a API e o banco

Na raiz do projeto, execute:

```bash
docker compose up --build -d
docker compose ps
```

`--build` reconstrói a imagem da API e `-d` mantém os serviços em segundo plano. Aguarde o PostgreSQL ficar saudável e a API iniciar.

Para acompanhar os logs da API:

```bash
docker compose logs -f api
```

Pressione `Ctrl+C` para sair da visualização dos logs; isso não encerra os containers.

### 4. Confirmar que a API está funcionando

A porta padrão da API é `3000`:

```bash
curl -i http://localhost:3000/health_check
curl http://localhost:3000/
```

`/health_check` deve retornar HTTP `204` sem corpo. `/` deve retornar um JSON com a identificação do serviço.

Se a porta estiver ocupada, configure `API_PORT` no `.env` conforme o `.env.example` e use a mesma porta nos comandos seguintes.

### 5. Parar e reiniciar

```bash
docker compose down
docker compose up -d
```

`docker compose down` não remove o volume persistente do banco. Evite `docker compose down -v` se quiser preservar os dados, pois a opção `-v` remove os volumes associados.

## Autenticação e variáveis de ambiente**



Toda rota, **\*\*exceto `GET /` e `GET /health_check`\*\***, exige o header:



```

INTERNAL-TOKEN: default_token

```



O valor esperado vem da variável `INTERNAL_TOKEN`. Sem o header, ou com valor errado, a resposta é `403` com código `QIT000002`. O middleware roda antes do roteamento: até uma rota inexistente responde `403` sem token (e `404` com token).



Variáveis do `.env.example`:



| Variável | Padrão | Para que serve |

|---|---|---|

| `APP_ENV` | `local` | `local`/`test`/`production`. Muda o nível do log (`DEBUG` aparece em `local` e `test`). |

| `SERVICE_NAME` | `bootcamp-api` | Nome do serviço, exibido no log e em `GET /`. |

| `DATABASE_URL` | `postgresql+psycopg2://bootcamp:bootcamp@localhost:5432/bootcamp` | Conexão com o banco, usada **\*\*fora\*\*** do Docker (testes, acesso direto). Dentro do compose a API usa `...@db:5432/...` e ignora este valor. **\*\*Obrigatória.\*\*** |

| `INTERNAL_TOKEN` | `default_token` | Valor aceito no header `INTERNAL-TOKEN`. **\*\*Obrigatória.\*\*** A API não sobe sem ela. |

| `SERVER_LOCALHOST` | `0.0.0.0` | Host onde os testes procuram a API. |

| `BANKSLIP_API_URL` | `http\://localhost:8080` | Endereço da API de boletos (connector em `src/connectors/`). |

| `BANKSLIP_API_INTERNAL_TOKEN` | `default_token` | Token que a API de boletos exige. |

| `BANKSLIP_API_TIMEOUT` | `5` | Segundos de espera pela API de boletos. |

| `API_PORT` | `3000` (comentada) | Porta da API na sua máquina; os testes também a leem. |

| `DB_PORT` | `5432` (comentada) | Porta do banco na sua máquina. |



> O `.env` nunca vai para o Git (está no `.gitignore`); só o `.env.example`, que contém apenas valores de exemplo.



## Rotas**



Todos os exemplos assumem a API em `localhost:3000`. Defina uma vez:



```bash

H='INTERNAL-TOKEN: default_token'

J='Content-Type: application/json'

B=http\://localhost:3000

```



| Método | Rota | Sucesso | Função |

|---|---|---|---|

| GET | `/` | 200 | Identifica o serviço (pública) |

| GET | `/health_check` | 204 | Saúde (pública) |

| POST | `/customers` | 201 | Cadastra cliente em `pending_kyc` |

| GET | `/customers` | 200 | Lista paginada com filtros |

| GET | `/customers/{customer_key}` | 200 | Detalhe + histórico de status |

| PUT | `/customers/{customer_key}` | 202 | Define o status (só a partir de `pending_kyc`) |

| POST | `/accounts` | 201 | Abre conta para cliente ativo |

| GET | `/accounts/{account_key}` | 200 | Saldo e dono da conta |

| POST | `/accounts/{account_key}/transactions` | 201 | Transfere da conta da URL para outra |

| GET | `/accounts/{account_key}/transactions` | 200 | Extrato paginado |



Erros têm sempre o formato `{"title","description","translation","code"}`.



### Clientes**



```bash

\# Cadastrar (201 -> {"customer_key": "..."})

curl -X POST $B/customers -H "$H" -H "$J" \\

  -d '{"name":"Maria Silva","email":"maria@example.com","document_number":"529.982.247-25","birthdate":"1990-05-20"}'



\# Ativar (202). Troque \<customer_key> pela chave devolvida acima

curl -X PUT $B/customers/\<customer_key> -H "$H" -H "$J" -d '{"status":"active"}'



\# Detalhe (200): inclui status_events, o histórico de mudanças de status

curl $B/customers/\<customer_key> -H "$H"



\# Listar (200). Filtros: status (repetível), name, email, document_number,

\# birthdate_from, birthdate_to; limit (1-100, padrão 10) e page (padrão 1)

curl "$B/customers?status=active&limit=10&page=1" -H "$H"

```



Resposta da listagem: `{"data":[...],"limit":10,"page":1,"is_last_page":false}`.



### Contas**



```bash

\# Abrir conta com R$ 5.000,00 (201 -> {"account_key": "..."}); initial_balance é opcional

curl -X POST $B/accounts -H "$H" -H "$J" \\

  -d '{"customer_key":"\<customer_key>","initial_balance":500000}'



\# Consultar (200 -> account_key, balance em centavos, customer_key, tier)

curl $B/accounts/\<account_key> -H "$H"

```



### Transações e extrato**



```bash

\# Transferir R$ 100,00 (201)

curl -X POST $B/accounts/\<conta_origem>/transactions -H "$H" -H "$J" \\

  -d '{"destination_account_key":"\<conta_destino>","amount":10000}'

\# -> {"transaction_key":"...","amount":10000,"fee_amount":0,"is_fee_exempt":true}



\# Extrato (200). Parâmetros opcionais: limit (1-100, padrão 20), page (padrão 1),

\# start_date e end_date (YYYY-MM-DD, UTC, ambas inclusivas)

curl "$B/accounts/\<account_key>/transactions?limit=20&page=1&start_date=2026-10-01&end_date=2026-10-31" -H "$H"

\# -> {"items":[{"transaction_key","direction":"debit|credit","amount","fee_amount",

\#               "counterparty_account_key","created_at"}],

\#     "pagination":{"total_items":6,"page":1,"limit":20}}

```



No extrato, `fee_amount` só aparece diferente de zero em `debit`; o `credit` mostra sempre `0`.



### Erros mais comuns**



| HTTP | Código | Quando |

|---|---|---|

| 400 | `QIT000001` | Corpo ou query fora do schema (ex.: `amount` decimal, `limit=101`) |

| 400 | `QIT000010` | `birthdate_from` depois de `birthdate_to` |

| 403 | `QIT000002` | Header `INTERNAL-TOKEN` ausente ou errado |

| 404 | `QIT001001` / `QIT002001` | Cliente / conta não encontrado |

| 404 | `QIT000404` | Rota inexistente (inclui `/docs`) |

| 409 | `QIT001002` | Cliente já saiu de `pending_kyc` |

| 409 | `QIT001004` / `QIT001005` | CPF / e-mail já cadastrado |

| 422 | `QIT001003` | CPF com formato válido, mas inexistente |

| 422 | `QIT001006` / `QIT001008` | Menor de 18 / maior de 80 anos |

| 422 | `QIT001009` | Cliente não está `active` ao abrir conta |

| 422 | `QIT002002` | Saldo insuficiente para `amount + tarifa` |

| 422 | `QIT002003` | Transferência para a própria conta |

| 422 | `QIT002004` / `QIT002005` | Data de extrato inexistente / `start_date` > `end_date` |



## Como testar

Você pode testar o sistema manualmente com `curl` e executar a suíte automatizada com `pytest`.

### 1. Preparar o ambiente

Os testes de integração acessam a API e o PostgreSQL iniciados pelo Docker. Na raiz do projeto:

```bash
docker compose up -d
docker compose ps
```

Crie um ambiente virtual para instalar as dependências de teste sem alterar o Python do sistema:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements-dev.txt
```

Se o comando `python3 -m venv .venv` falhar no Ubuntu, instale o pacote `python3-venv` correspondente à versão do Python e tente novamente.

### 2. Executar todos os testes

Com o ambiente virtual ativado e na raiz do projeto:

```bash
PYTHONPATH=src:. pytest -v
```

O parâmetro `-v` mostra o resultado de cada teste. Para uma saída mais compacta:

```bash
PYTHONPATH=src:. pytest
```

O prefixo `PYTHONPATH=src:.` é necessário porque os testes importam módulos que ficam dentro de `src/`.

### 3. Executar testes específicos

Somente testes unitários (não dependem da API nem do banco em execução):

```bash
PYTHONPATH=src:. pytest tests/unit -v
```

Somente testes de integração (dependem da API e do banco):

```bash
PYTHONPATH=src:. pytest tests/integration -v
```

Um arquivo específico:

```bash
PYTHONPATH=src:. pytest tests/integration/test_transaction_statement.py -v
```

Se o caminho do exemplo não existir na sua versão, confira os arquivos disponíveis em `tests/`.

### 4. Testar as rotas manualmente

Defina estas variáveis no terminal em que fará os testes:

```bash
B=http://localhost:3000
H='INTERNAL-TOKEN: default_token'
J='Content-Type: application/json'
```

**Testar a autenticação:** sem token, a rota protegida deve responder `403`; com o token padrão, deve responder com sucesso:

```bash
curl -i "$B/customers"
curl -i "$B/customers" -H "$H"
```

**Cadastrar um cliente:** a resposta esperada é HTTP `201`, com um `customer_key`. O CPF abaixo é um exemplo válido para teste. Use um e-mail diferente a cada nova execução se o banco mantiver os dados anteriores.

```bash
curl -i -X POST "$B/customers" -H "$H" -H "$J" \
  -d '{"name":"Maria Silva","email":"maria@example.com","document_number":"529.982.247-25","birthdate":"1990-05-20"}'
```

Copie o `customer_key` retornado e substitua o marcador no comando de ativação:

```bash
curl -i -X PUT "$B/customers/<customer_key>" -H "$H" -H "$J" \
  -d '{"status":"active"}'
```

**Abrir uma conta:** só clientes ativos podem abrir contas. Substitua `<customer_key>` pela chave real. O saldo inicial é em centavos: `500000` equivale a R$ 5.000,00.

```bash
curl -i -X POST "$B/accounts" -H "$H" -H "$J" \
  -d '{"customer_key":"<customer_key>","initial_balance":500000}'
```

Guarde o `account_key` retornado. Para testar uma transferência, você precisa de duas contas existentes: uma de origem e outra de destino.

**Transferir dinheiro:** `amount` também é informado em centavos; `10000` equivale a R$ 100,00.

```bash
curl -i -X POST "$B/accounts/<conta_origem>/transactions" -H "$H" -H "$J" \
  -d '{"destination_account_key":"<conta_destino>","amount":10000}'
```

**Consultar saldo e extrato:**

```bash
curl -i "$B/accounts/<account_key>" -H "$H"
curl -i "$B/accounts/<account_key>/transactions?limit=20&page=1" -H "$H"
```

Substitua todos os marcadores entre `< >` pelas chaves reais devolvidas pela API. Não inclua os caracteres `<` e `>` literalmente.

### 5. Conferir cenários de erro

Além dos casos de sucesso, confira se a API rejeita operações inválidas:

- Token ausente ou incorreto: HTTP `403`.
- Cliente ou conta inexistente: HTTP `404`.
- Abertura de conta para cliente não ativo: HTTP `422`.
- Transferência para a própria conta: HTTP `422`.
- Saldo insuficiente para valor mais tarifa: HTTP `422`.
- Corpo inválido ou valor monetário decimal: HTTP `400`.

Confira tanto o status HTTP quanto o código no JSON de erro.

### 6. Diagnosticar falhas nos testes

Se algum teste falhar:

1. Leia o traceback completo, começando pela primeira exceção relevante.
2. Confirme que `docker compose ps` mostra os serviços necessários em execução.
3. Consulte os logs: `docker compose logs --tail=100 api db`.
4. Confira se `DATABASE_URL`, `SERVER_LOCALHOST`, `API_PORT` e `INTERNAL_TOKEN` correspondem ao ambiente local.
5. Rode novamente apenas o teste que falhou para facilitar o diagnóstico.

A quantidade de testes pode mudar com a evolução do projeto; considere o resultado da execução atual como referência.

**Atenção — banco de testes:** os testes de integração podem executar `DROP SCHEMA public CASCADE` e recriar as tabelas. Rode-os somente contra um banco descartável de desenvolvimento/teste. Nunca aponte `DATABASE_URL` para um banco com dados que deseja preservar.

## Camadas**



Dentro de `src/`. A requisição atravessa as camadas na ordem em que aparecem abaixo.



| Camada | Decide |

|---|---|

| **\*\*`app.py`\*\*** | Monta a aplicação: a **\*\*ordem dos middlewares\*\***, qual endereço aponta para qual método de resource, e que a documentação interativa fica desligada. Valida as variáveis obrigatórias na subida. |

| **\*\*`middlewares/`\*\*** | O que acontece em **\*\*toda\*\*** requisição, antes e depois da rota: `internal_token` (quem pode entrar), `session_manager` (a sessão de banco nasce no começo e sofre `rollback`/`close` no fim, **\*\*nunca `commit`\*\***), `request_logger` (log de entrada/saída) e `request_context` (o `request_id` que acompanha o log). |

| **\*\*`schemas/`\*\*** | Se o **\*\*formato\*\*** do que chegou é aceitável. Arquivos JSON Schema (corpo dos `POST`/`PUT` e query strings dos `GET`), aplicados pelo `utils/schema_handler.py`. Falha vira `400 QIT000001`. |

| **\*\*`resources/`\*\*** | A tradução **\*\*HTTP ↔ aplicação\*\***: valida a entrada pelo schema, chama o controller e escolhe o status de sucesso (201, 202...). Não tem regra de negócio. |

| **\*\*`controllers/`\*\*** | As **\*\*regras de negócio\*\*** (idade, CPF, status final, saldo, tarifa) e a **\*\*fronteira da transação de banco\*\***: são o único lugar que dá `commit`, na última linha antes do `return`. Cada controller abre o contexto de banco ao ser construído. |

| **\*\*`repositories/`\*\*** | **\*\*Como\*\*** os dados são lidos e gravados: toda consulta SQLAlchemy mora aqui, inclusive o `SELECT ... FOR UPDATE`. Não decide regra, só busca e persiste. |

| **\*\*`models/`\*\*** | O formato das **\*\*tabelas\*\*** no SQLAlchemy: colunas, chaves e `CHECK` constraints (saldo ≥ 0, valor > 0, origem ≠ destino). |

| **\*\*`dtos/`\*\*** | O formato da **\*\*saída\*\***: o que de cada entidade sai na resposta JSON (por exemplo, `AccountDTO` não expõe IDs internos). |

| **\*\*`database/database.sql`\*\*** | O **\*\*schema inicial\*\*** (tabelas, constraints, índices e os quatro status de cliente). Roda quando o container do banco é criado. |



Apoio: `errors/` (exceções com código e tradução, mais o tradutor erro → JSON), `utils/` (`transaction_fee.py`, `document_number.py`, `schema_handler.py`, logger), `database/migrations/` (migrações aditivas **\*\*para bancos que já existem\*\***, aplicadas manualmente com `psql`; instalações novas não precisam delas) e `connectors/` (cliente HTTP da API de boletos; nenhuma rota atual o usa).



## Decisões de modelagem**



**\*\*Dinheiro em centavos, `BIGINT`.\*\*** `balance`, `amount` e `fee_amount` são inteiros. Não há ponto flutuante em nenhum ponto do caminho: o schema JSON recusa `amount` decimal (`1.5` → `400`) e exige `amount >= 1`. Constraints no banco reforçam: `balance >= 0`, `amount > 0`, `fee_amount >= 0`.



**\*\*O saldo mora em `account.balance`.\*\*** É uma coluna mantida, não um valor calculado somando o extrato: a leitura é direta, e o débito/crédito acontece sob lock, na mesma transação que insere a linha em `transaction`. O custo é haver duas representações do dinheiro (a coluna e o histórico) que só se mantêm coerentes porque o commit é único. Consequência a conhecer: o `initial_balance` entra direto no saldo, **\*\*sem\*\*** linha em `transaction`, então o extrato não reconstrói esse valor inicial.



**\*\*Travamento com `SELECT ... FOR UPDATE`.\*\*** Em uma transferência, origem e destino são travados **\*\*em ordem crescente de `id`\*\***, independentemente de quem é quem. Assim `A→B` e `B→A` simultâneas não se travam mutuamente (sem deadlock). As linhas são relidas com `populate_existing()` depois do lock, e a contagem da franquia e o cálculo do saldo acontecem **\*\*depois\*\*** de travar, então duas transferências concorrentes não enxergam o mesmo saldo antigo. Débito, crédito e registro são confirmados em **\*\*um único `commit`\*\***; qualquer exceção faz `rollback`. Os testes de integração incluem cenários concorrentes (conservação do dinheiro e impossibilidade de estourar o saldo).



**\*\*Histórico de status em tabela própria.\*\*** `customer.status_id` guarda o status **\*\*atual\*\***; cada mudança (inclusive a criação) acrescenta uma linha em `customer_status_event` com `event_datetime`, nunca altera nem apaga as anteriores. O `GET /customers/{key}` devolve esse histórico em `status_events`. Que o histórico é só de inserção é uma convenção do código, não um bloqueio do banco. Os status moram em `customer_status` (`pending_kyc`, `active`, `blocked`, `inactive`).



**\*\*Identificadores públicos separados dos internos.\*\*** Chaves de API são UUIDs (`customer_key`, `account_key`, `transaction_key`); as chaves primárias numéricas nunca saem na resposta. É por elas, porém, que se define a ordem de lock.



## Entrega: repositório público em 13/10**



Na entrega de **\*\*13/10\*\***, o repositório precisa estar **\*\*público\*\***. Antes de enviar:



1\. No GitHub, em *\*Settings → General → Danger Zone → Change visibility\**, deixe como **\*\*Public\*\***.

2\. Abra a URL do repositório numa **\*\*janela anônima\*\*** (sem login). Se o código aparece, está público.

3\. Confirme que nada sensível foi versionado: `git ls-files | grep -E '(^|/)\\.env$'` não deve listar nada (só `.env.example` é versionado, e ele contém apenas valores de exemplo).

4\. Confirme que o `README.md` e o `docker compose up` funcionam a partir de um clone novo.
