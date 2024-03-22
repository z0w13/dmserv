from sqlalchemy import Engine, create_engine
from .models import Base


def create(url: str) -> Engine:
    engine = create_engine(url, echo=False)
    Base.metadata.create_all(engine)

    return engine
