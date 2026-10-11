class TransactionDTO:
    @staticmethod
    def obj_to_dict(transaction, is_fee_exempt: bool) -> dict:
        return {
            "transaction_key": transaction.transaction_key,
            "amount": transaction.amount,
            "fee_amount": transaction.fee_amount,
            "is_fee_exempt": is_fee_exempt,
        }

    @staticmethod
    def list_to_dict(rows: list, account_id: int, page: int, limit: int, total_items: int) -> dict:
        items = []
        for transaction, counterparty_key in rows:
            is_debit = transaction.source_account_id == account_id
            is_fee_credit = getattr(transaction, "fee_account_id", None) == account_id
            items.append({
                "transaction_key": transaction.transaction_key.strip(),
                "direction": "debit" if is_debit else "credit",
                "amount": transaction.fee_amount if is_fee_credit else transaction.amount,
                "fee_amount": transaction.fee_amount if is_debit else 0,
                "counterparty_account_key": counterparty_key.strip(),
                "created_at": transaction.created_at.isoformat(),
            })
        return {
            "items": items,
            "pagination": {"total_items": total_items, "page": page, "limit": limit},
        }
