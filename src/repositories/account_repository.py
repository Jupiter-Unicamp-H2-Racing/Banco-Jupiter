from database import Context
from models.account import Account


class AccountRepository:
    def __init__(self, context: Context) -> None:
        self.session = context.db_session

    def get_by_key(self, account_key: str, for_update: bool = False):
        query = self.session.query(Account).filter(Account.account_key == account_key)
        if for_update:
            query = query.with_for_update().populate_existing()
        return query.first()

    def get_by_id_for_update(self, account_id: int):
        return (
            self.session.query(Account)
            .filter(Account.id == account_id)
            .with_for_update()
            .populate_existing()
            .first()
        )

    def update_balance(self, account: Account, new_balance: int) -> None:
        account.balance = new_balance
