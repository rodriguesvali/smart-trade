from collections.abc import Generator
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.orm import Session, sessionmaker


def get_session(request: Request) -> Generator[Session]:
    session_factory: sessionmaker[Session] = request.app.state.db_session_factory
    with session_factory() as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]

