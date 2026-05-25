from fastapi import FastAPI, Depends, HTTPException, status, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse, PlainTextResponse
from fastapi.templating import Jinja2Templates
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session, select
from typing import Annotated, Optional
from datetime import datetime, date, timedelta

# NOVO - TASK-11: Uvoz za slanje pravih e-mailova
from fastapi_mail import ConnectionConfig, FastMail, MessageSchema, MessageType

# Uvoz tvojih lokalnih modula za bazu i autentifikaciju
from database import engine, get_session, create_db_and_tables, ensure_schema
import models
import auth

app = FastAPI(title="Tenis Rezervacije v1.0")

# Postavljanje Jinja2 predložaka za HTML stranice
templates = Jinja2Templates(directory="templates")


# ================================================================
# TASK-11: KONFIGURACIJA ZA PRAVO SLANJE E-MAILA (SMTP)
# ================================================================
# Prilagodite ove podatke Vašem SMTP poslužitelju (npr. Gmail, Mailtrap, Outlook...)
mail_conf = ConnectionConfig(
    MAIL_USERNAME="luka0kurtovic@gmail.com",       # npr. tvoj e-mail ili Mailtrap korisničko ime
    MAIL_PASSWORD="qtjshwdyuwyifdby",  # npr. Gmail App Password ili Mailtrap lozinka
    MAIL_FROM="luka0kurtovic@gmail.com",
    MAIL_PORT=587,                                 # TLS port (najčešće 587, ili 465 za SSL)
    MAIL_SERVER="smtp.gmail.com",                # npr. smtp.gmail.com ili sandbox.smtp.mailtrap.io
    MAIL_STARTTLS=True,
    MAIL_SSL_TLS=False,
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True
)


@app.on_event("startup")
def on_startup():
    create_db_and_tables()
    ensure_schema()
    
    with Session(engine) as session:
        # 1. STVARANJE ADMINA (ako ne postoji)
        admin_user = session.exec(select(models.User).where(models.User.email == "admin@gmail.com")).first()
        if not admin_user:
            admin_user = models.User(
                username="admin",
                email="admin@gmail.com",
                hashed_password=auth.hash_password("admin"),
                is_admin=True
            )
            session.add(admin_user)
            print("🚀 Početni ADMIN račun uspješno stvoren!")

        # 2. STVARANJE OBIČNOG KORISNIKA (ako ne postoji)
        regular_user = session.exec(select(models.User).where(models.User.email == "korisnik@gmail.com")).first()
        if not regular_user:
            regular_user = models.User(
                username="korisnik",
                email="luka0kurtovic@gmail.com",
                hashed_password=auth.hash_password("korisnik"),
                is_admin=False
            )
            session.add(regular_user)
            print("🚀 Početni KORISNIK račun uspješno stvoren!")

        # 3. STVARANJE POČETNOG TERENA (ako tablica terena nema niti jedan zapis)
        if not session.exec(select(models.Court)).first():
            court = models.Court(
                name="Centralni teren",
                surface_type="zemlja",
                is_active=True,
                open_hour=8,
                close_hour=22
            )
            session.add(court)
            print("🎾 Početni TENISKI TEREN uspješno stvoren!")

        # Spremi sve promjene u bazu odjednom
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
    """Početna (Landing) stranica."""
    return templates.TemplateResponse(request=request, name="index.html")

@app.get("/signup", response_class=HTMLResponse)
def signup_page(request: Request):
    """Stranica za registraciju novih korisnika."""
    return templates.TemplateResponse(request=request, name="signup.html")

@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    """Stranica za prijavu korisnika."""
    return templates.TemplateResponse(request=request, name="login.html")

@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(
    request: Request, 
    username: str = "Gost", 
    email: str = "nepoznato", 
    is_admin: bool = False,
    user_id: Optional[int] = None
):
    """Glavna upravljačka ploča nakon uspješne prijave."""
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
    """Obrada registracije i provjera jedinstvenosti korisničkog imena."""
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
    
    return HTMLResponse(
        "<p style='color:green;'>Registracija uspješna! Idemo na prijavu...</p>"
        "<script>setTimeout(() => { window.location.href = '/login'; }, 1000);</script>"
    )

@app.post("/token")
def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()], 
    session: Session = Depends(get_session)
):
    """Provjera vjerodajnica i prijava korisnika uz preusmjeravanje."""
    statement = select(models.User).where(models.User.username == form_data.username)
    user = session.exec(statement).first()
    
    if not user or not auth.verify_password(form_data.password, user.hashed_password):
        return HTMLResponse(
            "<p style='color:red; background:#fee; padding:10px;'>Pogrešno ime ili lozinka!</p>", 
            status_code=401
        )
    
    target_url = (
        f"/dashboard?username={user.username}&email={user.email}"
        f"&is_admin={user.is_admin}&user_id={user.id}"
    )
    
    return HTMLResponse(f"<script>window.location.href='{target_url}';</script>")

@app.get("/logout")
def logout():
    """Odjava korisnika."""
    return RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)


# ================================================================
# REZERVACIJE: PROCESUIRANJE I ASINKRONO SLANJE PRAVOG E-MAILA
# ================================================================
@app.post("/reservations/submit")
async def create_reservation_from_form(
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
    Prihvaća zahtjev s frontenda, validira preklapanja, upisuje u bazu
    te asinkrono šalje e-mail potvrdu korisniku.
    """
    try:
        start_dt = datetime.fromisoformat(start_time)
        end_dt = datetime.fromisoformat(end_time)
    except ValueError:
        return PlainTextResponse("Nevažeći format datuma i vremena!", status_code=400)

    user = session.get(models.User, user_id)
    if not user:
        return PlainTextResponse("Korisnik nije pronađen u bazi.", status_code=404)

    court = session.get(models.Court, court_id)
    if not court:
        return PlainTextResponse("Teren nije pronađen u bazi.", status_code=404)

    if start_dt >= end_dt:
        return PlainTextResponse("Krajnje vrijeme mora biti nakon početnog vremena.", status_code=400)

    if start_dt < datetime.utcnow():
        return PlainTextResponse("Nije moguće rezervirati termin u prošlosti.", status_code=400)

    # Validacija preklapanja termina (TASK-06)
    overlapping_reservation = session.exec(
        select(models.Reservation).where(
            models.Reservation.court_id == court_id,
            models.Reservation.status == models.ReservationStatus.active,
            models.Reservation.start_time < end_dt,
            models.Reservation.end_time > start_dt
        )
    ).first()

    if overlapping_reservation:
        return PlainTextResponse("Ovaj termin je u međuvremenu već rezerviran!", status_code=409)

    # 1. Kreiranje i spremanje rezervacije u bazu (POPRAVLJENO: commit se izvršava odmah ovdje)
    new_reservation = models.Reservation(
        start_time=start_dt,
        end_time=end_dt,
        user_id=user_id,
        court_id=court_id,
        status=models.ReservationStatus.active
    )
    session.add(new_reservation)
    session.commit()

    # Formatiranje datuma i vremena za slanje u e-mailu
    prikaz_vremena = f"{start_dt.strftime('%H:%M')} - {end_dt.strftime('%H:%M')}"
    prikaz_datuma = start_dt.strftime('%d.%m.%Y')

    # 2. TASK-11: Slanje profesionalno oblikovane HTML e-mail poruke korisniku
    try:
        html_sadrzaj = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #e0e0e0; border-radius: 8px;">
                    <h2 style="color: #2e7d32; border-bottom: 2px solid #2e7d32; padding-bottom: 10px;">🎾 Potvrda Rezervacije — TenisMaster</h2>
                    <p>Pozdrav <strong>{user.username}</strong>,</p>
                    <p>Uspješno ste rezervirali termin putem našeg sustava. Detalji rezervacije nalaze se u nastavku:</p>
                    <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
                        <tr>
                            <td style="padding: 8px; border-bottom: 1px solid #ddd; font-weight: bold;">Teren:</td>
                            <td style="padding: 8px; border-bottom: 1px solid #ddd;">{court.name} ({court.surface_type})</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px; border-bottom: 1px solid #ddd; font-weight: bold;">Datum:</td>
                            <td style="padding: 8px; border-bottom: 1px solid #ddd;">{prikaz_datuma}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px; border-bottom: 1px solid #ddd; font-weight: bold;">Vrijeme:</td>
                            <td style="padding: 8px; border-bottom: 1px solid #ddd;">{prikaz_vremena} h</td>
                        </tr>
                    </table>
                    <p style="background: #f9f9f9; padding: 10px; border-left: 4px solid #2e7d32; font-size: 0.9em;">
                        Ukoliko želite otkazati termin, molimo Vas da to učinite unutar korisničkog sučelja (Dashboard) na vrijeme.
                    </p>
                    <p style="margin-top: 30px; font-size: 0.85em; color: #777;">Ova poruka je generirana automatski, molimo ne odgovarajte na nju.</p>
                </div>
            </body>
        </html>
        """

        poruka = MessageSchema(
            subject="🎾 Potvrda rezervacije - TenisMaster",
            recipients=[user.email],  # Šalje se na stvarnu e-mail adresu registriranog korisnika
            body=html_sadrzaj,
            subtype=MessageType.html
        )

        fm = FastMail(mail_conf)
        await fm.send_message(poruka)  # Pokretanje asinkronog slanja u pozadini
        email_status_msg = f"E-mail potvrda je poslana na {user.email}"
    except Exception as e:
        print(f"Greška pri slanju e-maila: {e}")
        email_status_msg = "Rezervacija je osigurana, no e-mail potvrda trenutno nije mogla biti odaslana."

    # Vraćamo OK status i tekst poruke koji JS prikazuje unutar modala uspjeha
    return PlainTextResponse(f"OK|{email_status_msg}", status_code=200)


# --- POMOĆNA LOGIKA: Generiranje 1-satnih slotova (TASK-09 Radno vrijeme) ---

def get_free_slots(
    court_id: int,
    target_date: date,
    session: Session,
    slot_duration_minutes: int = 60,
) -> list[dict]:
    """Generira vremenske slotove prateći individualno radno vrijeme terena."""
    court = session.get(models.Court, court_id)
    if not court:
        return []

    day_start = datetime(target_date.year, target_date.month, target_date.day, court.open_hour, 0)
    day_end   = datetime(target_date.year, target_date.month, target_date.day, court.close_hour, 0)
    slot_delta = timedelta(minutes=slot_duration_minutes)

    stmt = select(models.Reservation).where(
        models.Reservation.court_id == court_id,
        models.Reservation.status   == models.ReservationStatus.active,
        models.Reservation.start_time >= day_start,
        models.Reservation.start_time <  day_end,
    )
    existing: list[models.Reservation] = session.exec(stmt).all()

    slots = []
    current = day_start
    while current + slot_delta <= day_end:
        slot_end = current + slot_delta
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
    date_filter: Optional[str] = None,
    court_filter: Optional[int] = None,
    session: Session     = Depends(get_session),
):
    """Prikazuje slobodne i zauzete rasporede prema odabranom datumu i terenu."""
    courts = session.exec(
        select(models.Court)
        .where(models.Court.is_active == True)
        .order_by(models.Court.id)
    ).all()

    if date_filter:
        try:
            target_date = date.fromisoformat(date_filter)
        except ValueError:
            target_date = date.today()
    else:
        target_date = date.today()

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

# --- ADMIN: UPRAVLJANJE TERENIMA ---

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
    open_hour: int = Form(...),
    close_hour: int = Form(...),
    is_active: Optional[str] = Form(None),
    session: Session = Depends(get_session)
):
    require_admin(user_id, session)
    new_court = models.Court(
        name=name,
        surface_type=surface_type,
        open_hour=open_hour,
        close_hour=close_hour,
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
    open_hour: int = Form(...),
    close_hour: int = Form(...),
    is_active: Optional[str] = Form(None),
    session: Session = Depends(get_session)
):
    require_admin(user_id, session)
    court = session.get(models.Court, court_id)
    if not court:
        raise HTTPException(status_code=404, detail="Court not found.")
    court.name = name
    court.surface_type = surface_type
    court.open_hour = open_hour
    court.close_hour = close_hour
    court.is_active = bool(is_active)
    session.add(court)
    session.commit()
    return RedirectResponse(
        url=f"/admin/courts?user_id={user_id}",
        status_code=status.HTTP_303_SEE_OTHER
    )

# --- ADMIN: PREGLED I OTKAZIVANJE REZERVACIJA ---

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