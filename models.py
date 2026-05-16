from sqlmodel import SQLModel, Field, Relationship
from typing import List, Optional
from datetime import datetime
from enum import Enum

# Osnovni podaci koje dijele svi modeli korisnika
class UserBase(SQLModel):
    username: str = Field(index=True, unique=True)
    email: str = Field(unique=True)

# Model koji se koristi ISKLJUČIVO za registraciju (nema is_admin polja)
class UserCreate(UserBase):
    password: str 

# Model koji predstavlja tablicu u bazi podataka
class User(UserBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    hashed_password: str # NZ-03: Sigurno pohranjivanje lozinki
    is_admin: bool = Field(default=False) # Zadano je False

    # Druga strana relacije se zove 'reservations'
    reservations: List["Reservation"] = Relationship(back_populates="user")

# Tablica za teniske terene (TASK-01 + TASK-09 Radno vrijeme)
class Court(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    surface_type: str  # npr. zemlja, trava
    is_active: bool = Field(default=True)
    open_hour: int = Field(default=8)   # TASK-09: Početak radnog vremena
    close_hour: int = Field(default=22) # TASK-09: Kraj radnog vremena

    # Druga strana relacije se zove 'reservations'
    reservations: List["Reservation"] = Relationship(back_populates="court")

class ReservationStatus(str, Enum):
    active = "active"
    cancelled = "cancelled"
    expired = "expired"

# Tablica za rezervacije koja povezuje korisnike i terene (TASK-01)
class Reservation(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    start_time: datetime
    end_time: datetime
    status: ReservationStatus = Field(default=ReservationStatus.active, index=True)
    cancelled_at: Optional[datetime] = None
    
    user_id: int = Field(foreign_key="user.id")
    court_id: int = Field(foreign_key="court.id")

    # POPRAVLJENO: back_populates sada cilja 'reservations' unutar klase User
    user: User = Relationship(back_populates="reservations")
    
    # POPRAVLJENO: back_populates sada cilja 'reservations' unutar klase Court
    court: Court = Relationship(back_populates="reservations")

# Model za kreiranje rezervacije (TASK-05)
class ReservationCreate(SQLModel):
    start_time: datetime
    end_time: datetime
    user_id: int
    court_id: int