# Tarifa transacional

## Regra implementada

- Valores monetários são inteiros em centavos.
- As primeiras `monthly_free_transfers_limit` transferências concluídas no mês-calendário UTC não pagam tarifa.
- Depois da franquia, a tarifa é de 250 centavos, exceto quando o saldo da origem imediatamente antes da transferência é >= 100000 centavos.
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

As contas precisam existir na tabela `account` antes de transferir. Exemplo de preparação em ambiente local (valores em centavos):

```sql
INSERT INTO account (account_key, balance)
VALUES
  ('550e8400-e29b-41d4-a716-446655440000', 200000),
  ('550e8400-e29b-41d4-a716-446655440002', 0);
```

## Requisição

```bash
curl -X POST 'http://localhost:3000/accounts/550e8400-e29b-41d4-a716-446655440000/transactions' \
  -H 'Content-Type: application/json' \
  -H 'INTERNAL-TOKEN: default_token' \
  -d '{"destination_account_key":"550e8400-e29b-41d4-a716-446655440002","amount":10000}'
```

`amount: 10000` representa R$ 100,00. A resposta HTTP 201 tem `transaction_key`, `amount`, `fee_amount` e `is_fee_exempt`.

## Testes

Os testes puros da política de tarifa ficam em `tests/unit/test_transaction_fee_policy.py`. Os cenários reais de bloqueio concorrente devem ser executados com PostgreSQL; SQLite não comprova `SELECT FOR UPDATE`.
