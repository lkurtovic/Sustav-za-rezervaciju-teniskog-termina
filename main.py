from fastapi import FastAPI, Depends, HTTPException, status, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
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