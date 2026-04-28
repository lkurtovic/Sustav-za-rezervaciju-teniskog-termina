from sqlmodel import create_engine, SQLModel, Session
from sqlalchemy import text
import models

sqlite_file_name = "database.db"
sqlite_url = f"sqlite:///{sqlite_file_name}"

engine = create_engine(sqlite_url, echo=True)

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

def ensure_schema():
    with engine.begin() as conn:
        columns = {
            row[1]
            for row in conn.execute(text("PRAGMA table_info(reservation)"))
        }
        if not columns:
            return

        if "status" not in columns:
            conn.execute(
                text("ALTER TABLE reservation ADD COLUMN status VARCHAR DEFAULT 'active'")
            )
            conn.execute(text("UPDATE reservation SET status = 'active' WHERE status IS NULL"))

        if "cancelled_at" not in columns:
            conn.execute(
                text("ALTER TABLE reservation ADD COLUMN cancelled_at DATETIME")
            )

# DODAJ OVO: Ova funkcija služi za Dependency Injection u FastAPI-ju
def get_session():
    with Session(engine) as session:
        yield session

if __name__ == "__main__":
    create_db_and_tables()