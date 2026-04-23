from sqlmodel import SQLModel, Field, Relationship
from typing import List, Optional
from datetime import datetime

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

    reservations: List["Reservation"] = Relationship(back_populates="user")

# Tablica za teniske terene (TASK-01)
class Court(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    surface_type: str  # npr. zemlja, trava
    is_active: bool = Field(default=True)

    reservations: List["Reservation"] = Relationship(back_populates="court")

# Tablica za rezervacije koja povezuje korisnike i terene (TASK-01)
class Reservation(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    start_time: datetime
    end_time: datetime
    
    user_id: int = Field(foreign_key="user.id")
    court_id: int = Field(foreign_key="court.id")

    user: User = Relationship(back_populates="reservations")
    court: Court = Relationship(back_populates="reservations")