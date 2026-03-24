## 3) Class dijagram

**Pitanje:** Od čega se sustav sastoji i kako su entiteti povezani?

**Objašnjenje (sažeto):**
- Korisnik ima više rezervacija; Admin je specijalizirani korisnik (nasljeđivanje).
- Rezervacija se veže na jedan Termin; Termin pripada jednom Terenu i definiran je vremenom unutar radnog vremena.
- Teren ima definirano radno vrijeme (jedan teren – više pravila radnog vremena).
- Validacija kolizije sprječava dvostruku rezervaciju.

PlantUML Kod:  
'''
@startuml
class Korisnik {
  +id: UUID
  +ime: String
  +email: String
  +hashedLozinka: String
}

class Admin {
  +privilegije: String
}

class Teren {
  +id: UUID
  +naziv: String
  +podloga: String
  +status: StatusTeren
}

class RadnoVrijeme {
  +id: UUID
  +pocetak: Time
  +kraj: Time
}

class Termin {
  +id: UUID
  +datum: Date
  +pocetak: Time
  +kraj: Time
  +status: StatusTermina
}

class Rezervacija {
  +id: UUID
  +status: StatusRezervacije
  +createdAt: DateTime
}

enum StatusTeren {
  aktivan
  neaktivan
  u_odrzavanju
}

enum StatusTermina {
  slobodan
  zauzet
  otkazan
}

enum StatusRezervacije {
  aktivna
  otkazana
  istekla
}

Admin --|> Korisnik
Korisnik "1" --> "0..*" Rezervacija : kreira
Rezervacija "1" --> "1" Termin
Termin "1" --> "1" Teren
Teren "1" --> "1..*" RadnoVrijeme
Admin "1" --> "0..*" Teren : upravlja
@enduml
'''
