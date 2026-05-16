from fastapi import FastAPI, Depends, HTTPException, status, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse, PlainTextResponse
from fastapi.templating import Jinja2Templates
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session, select
from typing import Annotated, Optional
from datetime import datetime

# Uvoz tvojih modula
from database import engine, get_session, create_db_and_tables, ensure_schema
import models
import auth

app = FastAPI(title="Tenis Rezervacije v1.0")

# Postavljanje Jinja2 predložaka
templates = Jinja2Templates(directory="templates")

@app.on_event("startup")
def on_startup():
    create_db_and_tables()
    ensure_schema()
    with Session(engine) as session:
        if not session.exec(select(models.Court)).first():
            court = models.Court(
                name="Centralni teren",
                surface_type="zemlja",
                is_active=True
            )
            session.add(court)
            session.commit()

def require_admin(user_id: Optional[int], session: Session) -> models.User:
    if user_id is None:
        raise HTTPException(status_code=401, detail="Missing admin user.")
    user = session.get(models.User, user_id)
    if not user or not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required.")
    return user

# --- STRANICE (GET Rute) ---

@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    """Landing page."""
    return templates.TemplateResponse(request=request, name="index.html")

@app.get("/signup", response_class=HTMLResponse)
def signup_page(request: Request):
    """Stranica za registraciju."""
    return templates.TemplateResponse(request=request, name="signup.html")

@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    """Stranica za prijavu."""
    return templates.TemplateResponse(request=request, name="login.html")

@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(
    request: Request, 
    username: str = "Gost", 
    email: str = "nepoznato", 
    is_admin: bool = False,
    user_id: Optional[int] = None
):
    """
    Glavna stranica nakon prijave.
    Prima podatke o korisniku i prikazuje ih.
    """
    return templates.TemplateResponse(
        request=request, 
        name="dashboard.html", 
        context={
            "request": request, 
            "username": username, 
            "email": email, 
            "is_admin": is_admin,
            "user_id": user_id
        }
    )

# --- LOGIKA I OBRADA (POST Rute) ---

@app.post("/register")
def register(user_data: models.UserCreate, session: Session = Depends(get_session)):
    """FZ-03: Registracija i preusmjeravanje na login."""
    statement = select(models.User).where(models.User.username == user_data.username)
    if session.exec(statement).first():
        return HTMLResponse(
            "<p style='color:red; background:#fee; padding:10px;'>Korisničko ime je zauzeto!</p>", 
            status_code=400
        )
    
    new_user = models.User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=auth.hash_password(user_data.password),
        is_admin=False
    )
    session.add(new_user)
    session.commit()
    
    # Automatski prebaci na login nakon 1 sekunde
    return HTMLResponse(
        "<p style='color:green;'>Registracija uspješna! Idemo na prijavu...</p>"
        "<script>setTimeout(() => { window.location.href = '/login'; }, 1000);</script>"
    )

@app.post("/token")
def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()], 
    session: Session = Depends(get_session)
):
    """FZ-04: Prijava i preusmjeravanje na Dashboard s podacima."""
    statement = select(models.User).where(models.User.username == form_data.username)
    user = session.exec(statement).first()
    
    if not user or not auth.verify_password(form_data.password, user.hashed_password):
        return HTMLResponse(
            "<p style='color:red; background:#fee; padding:10px;'>Pogrešno ime ili lozinka!</p>", 
            status_code=401
        )
    
    # Generiranje URL-a s parametrima za prikaz na dashboardu
    # (Kasnije ćemo ovo zamijeniti sigurnijim Cookie/JWT sustavom)
    target_url = (
        f"/dashboard?username={user.username}&email={user.email}"
        f"&is_admin={user.is_admin}&user_id={user.id}"
    )
    
    return HTMLResponse(f"<script>window.location.href='{target_url}';</script>")

# --- POMOĆNE RUTE ---

@app.get("/logout")
def logout():
    """Vraća korisnika na početnu."""
    return RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)

# --- REZERVACIJE ---

@app.post("/reservations")
def create_reservation(
    reservation_data: models.ReservationCreate,
    session: Session = Depends(get_session)
):
    """
    TASK-05: Kreiranje rezervacije
    TASK-06: Validacija preklapanja termina
    """

    # Provjera postoji li korisnik
    user = session.get(models.User, reservation_data.user_id)
    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found."
        )

    # Provjera postoji li teren
    court = session.get(models.Court, reservation_data.court_id)
    if not court:
        raise HTTPException(
            status_code=404,
            detail="Court not found."
        )

    # Provjera vremena
    if reservation_data.start_time >= reservation_data.end_time:
        raise HTTPException(
            status_code=400,
            detail="End time must be after start time."
        )

    # Ne dopuštaj rezervacije u prošlosti
    if reservation_data.start_time < datetime.utcnow():
        raise HTTPException(
            status_code=400,
            detail="Cannot reserve a past time slot."
        )

    # TASK-06: Provjera preklapanja termina
    overlapping_reservation = session.exec(
        select(models.Reservation).where(
            models.Reservation.court_id == reservation_data.court_id,
            models.Reservation.status == models.ReservationStatus.active,
            models.Reservation.start_time < reservation_data.end_time,
            models.Reservation.end_time > reservation_data.start_time
        )
    ).first()

    # Ako postoji preklapanje -> zabrani rezervaciju
    if overlapping_reservation:
        raise HTTPException(
            status_code=409,
            detail="This time slot is already reserved."
        )

    # Kreiranje rezervacije
    new_reservation = models.Reservation(
        start_time=reservation_data.start_time,
        end_time=reservation_data.end_time,
        user_id=reservation_data.user_id,
        court_id=reservation_data.court_id,
        status=models.ReservationStatus.active
    )

    session.add(new_reservation)
    session.commit()
    session.refresh(new_reservation)

    return {
        "message": "Reservation created successfully.",
        "reservation": new_reservation
    }


@app.post("/reservations/submit")
def create_reservation_from_form(
    user_id: int = Form(...),
    court_id: int = Form(...),
    start_time: str = Form(...),
    end_time: str = Form(...),
    username: str = Form("Gost"),
    email: str = Form("nepoznato"),
    is_admin: bool = Form(False),
    session: Session = Depends(get_session)
):
    """
    Prihvaća zahtjev za rezervaciju direktno s frontenda,
    izvršava validaciju i vraća tekstualni status za JS modal.
    """
    # Pretvaranje stringova iz HTML-a natrag u datetime objekte
    try:
        start_dt = datetime.fromisoformat(start_time)
        end_dt = datetime.fromisoformat(end_time)
    except ValueError:
        return PlainTextResponse("Nevažeći format datuma i vremena!", status_code=400)

    # 1. Provjera postoji li korisnik
    user = session.get(models.User, user_id)
    if not user:
        return PlainTextResponse("Korisnik nije pronađen u bazi.", status_code=404)

    # 2. Provjera postoji li teren
    court = session.get(models.Court, court_id)
    if not court:
        return PlainTextResponse("Teren nije pronađen u bazi.", status_code=404)

    # 3. Provjera vremena
    if start_dt >= end_dt:
        return PlainTextResponse("Krajnje vrijeme mora biti nakon početnog vremena.", status_code=400)

    # 4. Ne dopuštaj rezervacije u prošlosti
    if start_dt < datetime.utcnow():
        return PlainTextResponse("Nije moguće rezervirati termin u prošlosti.", status_code=400)

    # 5. Provjera preklapanja termina
    overlapping_reservation = session.exec(
        select(models.Reservation).where(
            models.Reservation.court_id == court_id,
            models.Reservation.status == models.ReservationStatus.active,
            models.Reservation.start_time < end_dt,
            models.Reservation.end_time > start_dt
        )
    ).first()

    # AKO JE ZAUZETO: Vraćamo grešku 409 što JS odmah prepoznaje i ispisuje upozorenje
    if overlapping_reservation:
        return PlainTextResponse("Ovaj termin je u međuvremenu već rezerviran!", status_code=409)

    # 6. Kreiranje rezervacije u bazi
    new_reservation = models.Reservation(
        start_time=start_dt,
        end_time=end_dt,
        user_id=user_id,
        court_id=court_id,
        status=models.ReservationStatus.active
    )

    session.add(new_reservation)
    session.commit()

    # AKO JE USPJEŠNO: Vraćamo čisti "OK" sa statusom 200, što aktivira zeleni prozorčić na svijetli dio modala!
    return PlainTextResponse("OK", status_code=200)
# --- ADMIN: TERENI ---

@app.get("/admin/courts", response_class=HTMLResponse)
def admin_courts(
    request: Request,
    user_id: Optional[int] = None,
    session: Session = Depends(get_session)
):
    admin_user = require_admin(user_id, session)
    courts = session.exec(select(models.Court).order_by(models.Court.id)).all()
    return templates.TemplateResponse(
        request=request,
        name="admin_courts.html",
        context={
            "request": request,
            "courts": courts,
            "user_id": admin_user.id,
            "admin_user": admin_user,
        }
    )

@app.post("/admin/courts")
def create_court(
    user_id: int = Form(...),
    name: str = Form(...),
    surface_type: str = Form(...),
    is_active: Optional[str] = Form(None),
    session: Session = Depends(get_session)
):
    require_admin(user_id, session)
    new_court = models.Court(
        name=name,
        surface_type=surface_type,
        is_active=bool(is_active)
    )
    session.add(new_court)
    session.commit()
    return RedirectResponse(
        url=f"/admin/courts?user_id={user_id}",
        status_code=status.HTTP_303_SEE_OTHER
    )

@app.get("/admin/courts/{court_id}/edit", response_class=HTMLResponse)
def edit_court_page(
    request: Request,
    court_id: int,
    user_id: Optional[int] = None,
    session: Session = Depends(get_session)
):
    admin_user = require_admin(user_id, session)
    court = session.get(models.Court, court_id)
    if not court:
        raise HTTPException(status_code=404, detail="Court not found.")
    return templates.TemplateResponse(
        request=request,
        name="admin_edit_court.html",
        context={
            "request": request,
            "court": court,
            "user_id": user_id,
            "admin_user": admin_user,
        }
    )

@app.post("/admin/courts/{court_id}/edit")
def update_court(
    court_id: int,
    user_id: int = Form(...),
    name: str = Form(...),
    surface_type: str = Form(...),
    is_active: Optional[str] = Form(None),
    session: Session = Depends(get_session)
):
    require_admin(user_id, session)
    court = session.get(models.Court, court_id)
    if not court:
        raise HTTPException(status_code=404, detail="Court not found.")
    court.name = name
    court.surface_type = surface_type
    court.is_active = bool(is_active)
    session.add(court)
    session.commit()
    return RedirectResponse(
        url=f"/admin/courts?user_id={user_id}",
        status_code=status.HTTP_303_SEE_OTHER
    )

# --- ADMIN: REZERVACIJE ---

@app.get("/admin/reservations", response_class=HTMLResponse)
def admin_reservations(
    request: Request,
    user_id: Optional[int] = None,
    session: Session = Depends(get_session)
):
    admin_user = require_admin(user_id, session)
    statement = (
        select(models.Reservation, models.User, models.Court)
        .join(models.User, models.Reservation.user_id == models.User.id)
        .join(models.Court, models.Reservation.court_id == models.Court.id)
        .order_by(models.Reservation.start_time)
    )
    rows = session.exec(statement).all()
    reservations = []
    for reservation, user, court in rows:
        status_value = (
            reservation.status.value
            if reservation.status is not None
            else models.ReservationStatus.active.value
        )
        reservations.append(
            {
                "reservation": reservation,
                "user": user,
                "court": court,
                "status": status_value,
            }
        )
    return templates.TemplateResponse(
        request=request,
        name="admin_reservations.html",
        context={
            "request": request,
            "reservations": reservations,
            "user_id": user_id,
            "admin_user": admin_user,
        }
    )

@app.post("/admin/reservations/{reservation_id}/cancel")
def cancel_reservation(
    reservation_id: int,
    user_id: int = Form(...),
    session: Session = Depends(get_session)
):
    require_admin(user_id, session)
    reservation = session.get(models.Reservation, reservation_id)
    if not reservation:
        raise HTTPException(status_code=404, detail="Reservation not found.")
    if reservation.status != models.ReservationStatus.cancelled:
        reservation.status = models.ReservationStatus.cancelled
        reservation.cancelled_at = datetime.utcnow()
        session.add(reservation)
        session.commit()
    return RedirectResponse(
        url=f"/admin/reservations?user_id={user_id}",
        status_code=status.HTTP_303_SEE_OTHER
    )

    # ================================================================
# ANTE GALIĆ — TASK-03, TASK-04 | FZ-01, FZ-02
# Dodaj ove rute u main.py
# ================================================================


from typing import Optional
from datetime import datetime, date, timedelta

# ----------------------------------------------------------------
# POMOĆNA FUNKCIJA: Generira listu slobodnih 1-satnih termina
# za određeni dan i teren (TASK-03 / FZ-01)
# ----------------------------------------------------------------

def get_free_slots(
    court_id: int,
    target_date: date,
    session: Session,
    slot_duration_minutes: int = 60,
    open_hour: int = 8,
    close_hour: int = 22,
) -> list[dict]:
    """
    FZ-01 / TASK-03:
    Generira sve moguće termine (slotove) za zadani datum i teren,
    a zatim izbacuje one koji se preklapaju s postojećim rezervacijama.

    Vraća listu rječnika oblika:
        {"start": datetime, "end": datetime, "free": bool}
    """
    # --- Postavljanje granica radnog vremena ---
    day_start = datetime(target_date.year, target_date.month, target_date.day, open_hour, 0)
    day_end   = datetime(target_date.year, target_date.month, target_date.day, close_hour, 0)
    slot_delta = timedelta(minutes=slot_duration_minutes)

    # --- Dohvati sve aktivne rezervacije za taj teren i datum ---
    stmt = select(models.Reservation).where(
        models.Reservation.court_id == court_id,
        models.Reservation.status   == models.ReservationStatus.active,
        models.Reservation.start_time >= day_start,
        models.Reservation.start_time <  day_end,
    )
    existing: list[models.Reservation] = session.exec(stmt).all()

    # --- Generiraj sve slotove i označi slobodne/zauzete ---
    slots = []
    current = day_start
    while current + slot_delta <= day_end:
        slot_end = current + slot_delta
        # Provjeri preklapanje s postojećim rezervacijama
        is_taken = any(
            r.start_time < slot_end and r.end_time > current
            for r in existing
        )
        slots.append({
            "start": current,
            "end":   slot_end,
            "free":  not is_taken,
        })
        current = slot_end

    return slots


@app.get("/reservations", response_class=HTMLResponse)
def reservations_page(
    request: Request,
    username: str        = "Gost",
    email: str           = "nepoznato",
    user_id: Optional[int] = None,
    is_admin: bool       = False,
    # Filteri (FZ-02)
    date_filter: Optional[str] = None,   # npr. "2025-06-15"
    court_filter: Optional[int] = None,
    session: Session     = Depends(get_session),
):
    """
    FZ-01: Prikazuje slobodne termine za odabrani datum.
    FZ-02: Podržava filtriranje po datumu i terenu.
    """

    # --- Dohvati sve aktivne terene za filter dropdown ---
    courts = session.exec(
        select(models.Court)
        .where(models.Court.is_active == True)
        .order_by(models.Court.id)
    ).all()

    # --- Odredi datum (zadano: danas) ---
    if date_filter:
        try:
            target_date = date.fromisoformat(date_filter)
        except ValueError:
            target_date = date.today()
    else:
        target_date = date.today()

    # --- Dohvati slotove samo ako je teren odabran ---
    slots        = []
    selected_court = None

    if court_filter and courts:
        selected_court = next((c for c in courts if c.id == court_filter), None)
        if selected_court:
            slots = get_free_slots(court_filter, target_date, session)

    return templates.TemplateResponse(
        request=request,
        name="reservations.html",
        context={
            "request":        request,
            "username":       username,
            "email":          email,
            "user_id":        user_id,
            "is_admin":       is_admin,
            "courts":         courts,
            "slots":          slots,
            "target_date":    target_date.isoformat(),
            "court_filter":   court_filter,
            "selected_court": selected_court,
        },
    )