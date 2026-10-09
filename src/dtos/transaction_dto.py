class TransactionDTO:
    @staticmethod
    def obj_to_dict(transaction, is_fee_exempt: bool) -> dict:
        return {
            "transaction_key": transaction.transaction_key,
            "amount": transaction.amount,
            "fee_amount": transaction.fee_amount,
            "is_fee_exempt": is_fee_exempt,
        }
