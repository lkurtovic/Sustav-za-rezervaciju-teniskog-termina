from fastapi import FastAPI, Depends, HTTPException, status, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session, select
from typing import Annotated

# Uvoz tvojih modula
from database import engine, get_session
import models
import auth

app = FastAPI(title="Tenis Rezervacije v1.0")

# Postavljanje Jinja2 predložaka
templates = Jinja2Templates(directory="templates")

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
    is_admin: bool = False
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
            "is_admin": is_admin
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
    target_url = f"/dashboard?username={user.username}&email={user.email}&is_admin={user.is_admin}"
    
    return HTMLResponse(f"<script>window.location.href='{target_url}';</script>")

# --- POMOĆNE RUTE ---

@app.get("/logout")
def logout():
    """Vraća korisnika na početnu."""
    return RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)