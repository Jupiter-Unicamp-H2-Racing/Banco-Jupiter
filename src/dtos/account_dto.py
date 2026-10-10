from models.account import Account


class AccountDTO:
    @staticmethod
    def only_obj_key(account: Account) -> dict:
        return {"account_key": account.account_key.strip()}

    @staticmethod
    def obj_to_dict(account: Account) -> dict:
        return {
            "account_key": account.account_key.strip(),
            "balance": account.balance,
            "customer_key": account.customer.customer_key.strip(),
            "tier": account.tier_code,
        }
