import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool
from datetime import datetime, timedelta

# Uvoz aplikacije, baze i modela
from main import app, get_session
import models

# Setup konfiguracija za testnu bazu u memoriji (SQLite :memory:)
# Koristi StaticPool kako bi omogućio dijeljenje iste in-memory baze među nitima
DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    DATABASE_URL, 
    connect_args={"check_same_thread": False}, 
    poolclass=StaticPool
)

# Definicija "fixture-a" koji priprema bazu podataka za svaki test i čisti je nakon testa
@pytest.fixture(name="session")
def session_fixture():
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    SQLModel.metadata.drop_all(engine)

# Fixture koji mijenja pravu bazu u FastAPI aplikaciji s testnom in-memory bazom
@pytest.fixture(name="client")
def client_fixture(session: Session):
    def get_session_override():
        return session
    
    # Premošćivanje ovisnosti (Dependency Override)
    app.dependency_overrides[get_session] = get_session_override
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


# ==============================================================================
# 1. TESTOVI ZA PRAVA PRISTUPA (ADMIN ZAŠTITA)
# ==============================================================================

def test_admin_route_access_denied_for_regular_user(client: TestClient, session: Session):
    """Provjera da običan korisnik (is_admin=False) dobiva 403 Forbidden pri pristupu admin ruti."""
    # Kreiramo običnog korisnika u testnoj bazi
    regular_user = models.User(
        username="leababic",
        email="lea@test.com",
        hashed_password="hashed_pwd",
        is_admin=False
    )
    session.add(regular_user)
    session.commit()
    session.refresh(regular_user)

    # Pokušavamo pristupiti ruti za pregled terena s ID-jem običnog korisnika
    response = client.get(f"/admin/courts?user_id={regular_user.id}")
    
    assert response.status_code == 403
    assert response.json()["detail"] == "Admin access required."


def test_admin_route_access_granted_for_admin(client: TestClient, session: Session):
    """Provjera da administrator (is_admin=True) može uspješno pristupiti admin ruti."""
    # Kreiramo admin korisnika u testnoj bazi
    admin_user = models.User(
        username="admin_luka",
        email="luka@admin.com",
        hashed_password="hashed_pwd",
        is_admin=True
    )
    session.add(admin_user)
    session.commit()
    session.refresh(admin_user)

    response = client.get(f"/admin/courts?user_id={admin_user.id}")
    
    # Očekujemo 200 OK jer korisnik ima administratorska prava
    assert response.status_code == 200


# ==============================================================================
# 2. TESTOVI ZA VALIDACIJU TERMINA (PREKLAPANJE REZERVACIJA)
# ==============================================================================

def test_reservation_overlap_validation(client: TestClient, session: Session):
    """Testira integracijski proces sprječavanja preklapanja termina (TASK-06)."""
    # 1. Priprema podataka: Korisnik i Teren
    user = models.User(username="igrac1", email="igrac1@test.com", hashed_password="pwd", is_admin=False)
    court = models.Court(name="Teren 1", surface_type="zemlja", is_active=True, open_hour=8, close_hour=22)
    session.add(user)
    session.add(court)
    session.commit()
    session.refresh(user)
    session.refresh(court)

    # Vremena za prvu rezervaciju: sutra od 12:00 do 13:00
    sutra = datetime.utcnow() + timedelta(days=1)
    start_1 = datetime(sutra.year, sutra.month, sutra.day, 12, 0)
    end_1 = datetime(sutra.year, sutra.month, sutra.day, 13, 0)

    # 2. Ubacujemo prvu aktivnu rezervaciju izravno u bazu
    existing_res = models.Reservation(
        start_time=start_1,
        end_time=end_1,
        user_id=user.id,
        court_id=court.id,
        status=models.ReservationStatus.active
    )
    session.add(existing_res)
    session.commit()

    # 3. Pokušavamo poslati zahtjev preko POST forme za novi termin koji se PREKLAPA (npr. 12:30 - 13:30)
    start_overlap = datetime(sutra.year, sutra.month, sutra.day, 12, 30).isoformat()
    end_overlap = datetime(sutra.year, sutra.month, sutra.day, 13, 30).isoformat()

    form_data = {
        "user_id": user.id,
        "court_id": court.id,
        "start_time": start_overlap,
        "end_time": end_overlap,
        "username": user.username,
        "email": user.email,
        "is_admin": "false"
    }

    response = client.post("/reservations/submit", data=form_data)

    # Očekujemo HTTP 409 Conflict status jer se termini preklapaju
    assert response.status_code == 409
    assert "Ovaj termin je u međuvremenu već rezerviran!" in response.text


def test_successful_reservation_when_no_overlap(client: TestClient, session: Session):
    """Provjera uspješne rezervacije kada nema preklapanja u rasporedu."""
    user = models.User(username="igrac2", email="igrac2@test.com", hashed_password="pwd", is_admin=False)
    court = models.Court(name="Teren 2", surface_type="trava", is_active=True, open_hour=8, close_hour=22)
    session.add(user)
    session.add(court)
    session.commit()
    session.refresh(user)
    session.refresh(court)

    sutra = datetime.utcnow() + timedelta(days=1)
    # Termin od 15:00 do 16:00 (slobodan)
    start_slobodno = datetime(sutra.year, sutra.month, sutra.day, 15, 0).isoformat()
    end_slobodno = datetime(sutra.year, sutra.month, sutra.day, 16, 0).isoformat()

    form_data = {
        "user_id": user.id,
        "court_id": court.id,
        "start_time": start_slobodno,
        "end_time": end_slobodno,
        "username": user.username,
        "email": user.email,
        "is_admin": "false"
    }

    response = client.post("/reservations/submit", data=form_data)

    # Očekujemo HTTP 200 OK jer termin ne smeta nikome
    assert response.status_code == 200
    assert "OK" in response.text