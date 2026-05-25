import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool
from datetime import datetime, timedelta, date
from fastapi import HTTPException

# Uvoz aplikacije, baze i modela
from main import app, get_session, require_admin, get_free_slots
import models
import auth

# Setup konfiguracija za testnu bazu u memoriji (SQLite :memory:)
DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    DATABASE_URL, 
    connect_args={"check_same_thread": False}, 
    poolclass=StaticPool
)

@pytest.fixture(name="session")
def session_fixture():
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    SQLModel.metadata.drop_all(engine)

@pytest.fixture(name="client")
def client_fixture(session: Session):
    def get_session_override():
        return session
    app.dependency_overrides[get_session] = get_session_override
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


# ==============================================================================
# 🔥 🔥 🔥 10 UNIT TESTOVA (TESTIRANJE ČISTE LOGIKE BEZ HTTP KLIJENTA) 🔥 🔥 🔥
# ==============================================================================

# --- Grupa 1: Testovi za funkciju require_admin (Pravila pristupa) ---

def test_unit_require_admin_success(session: Session):
    """UNIT TEST 1: require_admin dopušta pristup ako je korisnik admin."""
    admin = models.User(username="adm", email="a@t.com", hashed_password="p", is_admin=True)
    session.add(admin)
    session.commit()
    
    result = require_admin(user_id=admin.id, session=session)
    assert result.id == admin.id


def test_unit_require_admin_raises_401_for_missing_id(session: Session):
    """UNIT TEST 2: require_admin baca 401 ako user_id nije proslijeđen (None)."""
    with pytest.raises(HTTPException) as exc_info:
        require_admin(user_id=None, session=session)
    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Missing admin user."


def test_unit_require_admin_raises_403_for_regular_user(session: Session):
    """UNIT TEST 3: require_admin baca 403 ako korisnik u bazi nije administrator."""
    user = models.User(username="usr", email="u@t.com", hashed_password="p", is_admin=False)
    session.add(user)
    session.commit()
    
    with pytest.raises(HTTPException) as exc_info:
        require_admin(user_id=user.id, session=session)
    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "Admin access required."


def test_unit_require_admin_raises_403_if_user_not_found(session: Session):
    """UNIT TEST 4: require_admin baca 403 ako korisnik uopće ne postoji u bazi podataka."""
    with pytest.raises(HTTPException) as exc_info:
        require_admin(user_id=999, session=session)
    assert exc_info.value.status_code == 403


# --- Grupa 2: Testovi za funkciju get_free_slots (Radno vrijeme i slotovi) ---

def test_unit_get_free_slots_returns_empty_for_invalid_court(session: Session):
    """UNIT TEST 5: get_free_slots vraća praznu lista ako teren s tim ID-jem ne postoji."""
    slots = get_free_slots(court_id=999, target_date=date.today(), session=session)
    assert slots == []


def test_unit_get_free_slots_generates_correct_number_of_slots(session: Session):
    """UNIT TEST 6: Provjera generiranja ispravnog broja slotova na temelju radnog vremena terena."""
    court = models.Court(name="T1", surface_type="zemlja", is_active=True, open_hour=8, close_hour=10)
    session.add(court)
    session.commit()
    
    slots = get_free_slots(court_id=court.id, target_date=date.today(), session=session)
    assert len(slots) == 2  # Jedan slot 08:00-09:00, drugi 09:00-10:00
    assert slots[0]["free"] is True
    assert slots[1]["free"] is True


def test_unit_get_free_slots_marks_taken_slot_correctly(session: Session):
    """UNIT TEST 7: Ako u bazi postoji aktivna rezervacija, taj slot mora biti označen kao 'free: False'."""
    court = models.Court(name="T1", surface_type="zemlja", is_active=True, open_hour=8, close_hour=10)
    user = models.User(username="u", email="e@t.com", hashed_password="p", is_admin=False)
    session.add(court)
    session.add(user)
    session.commit()
    
    danas = date.today()
    start_res = datetime(danas.year, danas.month, danas.day, 8, 0)
    end_res = datetime(danas.year, danas.month, danas.day, 9, 0)
    
    res = models.Reservation(start_time=start_res, end_time=end_res, user_id=user.id, court_id=court.id, status=models.ReservationStatus.active)
    session.add(res)
    session.commit()
    
    slots = get_free_slots(court_id=court.id, target_date=danas, session=session)
    assert slots[0]["free"] is False  # Prvi slot (8-9h) je zauzet
    assert slots[1]["free"] is True   # Drugi slot (9-10h) je slobodan


# --- Grupa 3: Testovi za auth.py modul (Autentifikacija i Lozinke) ---

def test_unit_password_hashing():
    """UNIT TEST 8: Provjera da funkcija za hashiranje uspješno pretvara obični tekst u hash."""
    plain_password = "mojalozinka123"
    hashed = auth.hash_password(plain_password)
    assert hashed != plain_password
    assert len(hashed) > 0


def test_unit_password_verification_success():
    """UNIT TEST 9: Provjera da verifikacija lozinke prolazi za ispravan par čiste i hashirane lozinke."""
    plain_password = "superTajno"
    hashed = auth.hash_password(plain_password)
    assert auth.verify_password(plain_password, hashed) is True


def test_unit_password_verification_failure():
    """UNIT TEST 10: Provjera da verifikacija lozinke pada ako se proslijedi kriva lozinka."""
    plain_password = "ispravnaLozinka"
    hashed = auth.hash_password(plain_password)
    assert auth.verify_password("pogresnaLozinka", hashed) is False


# ==============================================================================
# 🔗 🔗 🔗 2 INTEGRACIJSKA TESTA (SIMULACIJA HTTP ZAHTJEVA KROZ KLIJENTA) 🔗 🔗 🔗
# ==============================================================================

def test_integration_admin_route_access_denied_for_regular_user(client: TestClient, session: Session):
    """INTEGRACIJSKI TEST 1: Provjera da običan korisnik dobiva 403 Forbidden pri HTTP pristupu admin ruti."""
    regular_user = models.User(username="leababic", email="lea@test.com", hashed_password="hashed_pwd", is_admin=False)
    session.add(regular_user)
    session.commit()

    response = client.get(f"/admin/courts?user_id={regular_user.id}")
    assert response.status_code == 403
    assert response.json()["detail"] == "Admin access required."


def test_integration_reservation_overlap_validation(client: TestClient, session: Session):
    """INTEGRACIJSKI TEST 2: Testira HTTP /reservations/submit rutu i provjerava blokira li se preklapanje (409 Conflict)."""
    user = models.User(username="igrac1", email="igrac1@test.com", hashed_password="pwd", is_admin=False)
    court = models.Court(name="Teren 1", surface_type="zemlja", is_active=True, open_hour=8, close_hour=22)
    session.add(user)
    session.add(court)
    session.commit()

    sutra = datetime.utcnow() + timedelta(days=1)
    start_1 = datetime(sutra.year, sutra.month, sutra.day, 12, 0)
    end_1 = datetime(sutra.year, sutra.month, sutra.day, 13, 0)

    existing_res = models.Reservation(start_time=start_1, end_time=end_1, user_id=user.id, court_id=court.id, status=models.ReservationStatus.active)
    session.add(existing_res)
    session.commit()

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
    assert response.status_code == 409
    assert "Ovaj termin je u međuvremenu već rezerviran!" in response.text