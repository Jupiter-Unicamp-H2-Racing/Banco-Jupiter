from abc import ABCMeta

from sqlalchemy.orm import Session

from utils.logger import get_logger


class BaseController(metaclass=ABCMeta):
    def __init__(self, session: Session, class_name: str) -> None:
        self.session = session
        self.logger = get_logger(class_name)
