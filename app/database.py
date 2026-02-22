"""
Database initialisation and session management.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker, DeclarativeBase


class Base(DeclarativeBase):
    pass


_engine = None
_Session = None


def init_db(flask_app):
    """Initialise the database engine and create all tables."""
    global _engine, _Session

    database_url = flask_app.config["SQLALCHEMY_DATABASE_URI"]
    _engine = create_engine(
        database_url,
        connect_args={"check_same_thread": False} if database_url.startswith("sqlite") else {},
    )
    _Session = scoped_session(sessionmaker(bind=_engine))

    # Import models so that their tables are registered on Base.metadata
    import app.models  # noqa: F401

    Base.metadata.create_all(_engine)

    @flask_app.teardown_appcontext
    def shutdown_session(exception=None):
        if _Session is not None:
            _Session.remove()


def get_session():
    """Return the current scoped session."""
    return _Session()
