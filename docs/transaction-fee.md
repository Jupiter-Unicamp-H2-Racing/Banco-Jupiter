# Tarifa transacional

## Regra implementada

- Valores monetários são inteiros em centavos.
- As primeiras `monthly_free_transfers_limit` transferências concluídas no mês-calendário UTC não pagam tarifa.
- Depois da franquia, a tarifa é de 50 centavos (R$ 0,50), exceto quando o saldo da origem imediatamente antes da transferência é >= 100000 centavos.
- A origem paga `amount + fee_amount`; o destino recebe somente `amount`.
- A contagem é calculada pelos registros persistidos em `transaction`, então a mudança de mês é automática.
- A origem e o destino são bloqueados com `SELECT ... FOR UPDATE` em ordem crescente de ID; a transferência, o crédito, o débito e o registro são confirmados em um commit.

## Banco

Para uma instalação nova, a inicialização usa `database/database.sql`.

Para um banco já existente, aplique a migração aditiva a partir da raiz do repositório:

```bash
psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f database/migrations/001_transaction_fee.sql
```

A migração cria as tabelas de contas e transferências se ainda não existirem; não apaga tabelas nem registros existentes. Antes de aplicar em produção, valide backup, permissões e eventuais conflitos de nomes de constraints/índices.

As contas precisam existir antes de transferir e pertencem a um cliente **ativo**. Crie-as pela API (valores em centavos):

```bash
# 1. cadastrar o cliente (nasce em pending_kyc) e ativá-lo
curl -X POST http://localhost:3000/customers -H 'Content-Type: application/json' -H 'INTERNAL-TOKEN: default_token' \
  -d '{"name":"Ana","email":"ana@exemplo.com","document_number":"529.982.247-25","birthdate":"1990-01-01"}'
curl -X PUT http://localhost:3000/customers/<customer_key> -H 'Content-Type: application/json' -H 'INTERNAL-TOKEN: default_token' \
  -d '{"status":"active"}'

# 2. abrir a conta (initial_balance é opcional e padrão 0)
curl -X POST http://localhost:3000/accounts -H 'Content-Type: application/json' -H 'INTERNAL-TOKEN: default_token' \
  -d '{"customer_key":"<customer_key>","initial_balance":200000}'
```

Para um banco que já tinha contas, a migração `database/migrations/003_account_customer.sql` exige que cada conta seja associada a um cliente antes de rodar.

## Requisição

```bash
curl -X POST 'http://localhost:3000/accounts/<source_account_key>/transactions' \
  -H 'Content-Type: application/json' \
  -H 'INTERNAL-TOKEN: default_token' \
  -d '{"destination_account_key":"<destination_account_key>","amount":10000}'
```

`amount: 10000` representa R$ 100,00. A resposta HTTP 201 tem `transaction_key`, `amount`, `fee_amount` e `is_fee_exempt`.

## Testes

Os testes puros da política de tarifa ficam em `tests/unit/test_transaction_fee_policy.py`. Os cenários reais de bloqueio concorrente devem ser executados com PostgreSQL; SQLite não comprova `SELECT FOR UPDATE`.
