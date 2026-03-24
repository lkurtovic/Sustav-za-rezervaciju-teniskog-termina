## 1) Use Case dijagram

**Piranje:** Tko koristi sustav i što želi raditi?

**Objašnjenje (sažeto):**
- Korisnik: Može se registrirati, prijaviti, pregledavati slobodne termine uz filtriranje te vršiti rezervaciju.
- Admin: Nasljeđuje sve funkcije korisnika, ali ima i ovlasti upravljanja resursima (kreiranje i izmjena terena, otkazivanje tuđih rezervacija i definiranje radnog vremena).
- Provjera dostupnosti (<<include>>): Sustav automatski provjerava je li termin slobodan kod svakog pokušaja rezervacije kako bi se spriječila kolizija.
- Dodatne opcije (<<extend>>): Korisnik može opcionalno platiti online ili primiti e-mail potvrdu nakon uspješne rezervacije.

PlantUML Kod:  

```plantuml
@startuml
left to right direction
skinparam packageStyle rectangle

actor "Korisnik" as K
actor "Admin" as A

rectangle "Sustav za rezervaciju terena" {
  (Pregled slobodnih termina) as UC1
  (Filtriranje termina) as UC2
  (Registracija korisnika) as UC3
  (Prijava korisnika) as UC4
  (Rezervacija termina) as UC5
  (Provjera dostupnosti) as UC6 <<include>>
  
  (Online plaćanje) as UC_Pay <<extend>>
  (Slanje potvrde na e-mail) as UC_Mail <<extend>>

  (Kreiranje novog terena) as UC7
  (Izmjena podataka o terenu) as UC8
  (Otkazivanje rezervacije) as UC9
  (Definiranje radnog vremena) as UC10
}

K --> UC1
K --> UC2
K --> UC3
K --> UC4
K --> UC5

' Include veza - provjera se uvijek vrši
UC5 ..> UC6 : <<include>>

' Extend veze - opcionalne radnje nakon rezervacije
UC_Pay ..> UC5 : <<extend>>
UC_Mail ..> UC5 : <<extend>>

' Admin nasljeđuje osnovne akcije i ima svoje specifične
A --|> K
A --> UC7
A --> UC8
A --> UC9
A --> UC10

@enduml
```

## 2) Sequence dijagram

**Pitanje:** Kako teče proces rezervacije termina korak po korak?

**Objašnjenje (sažeto):**
- Korisnik u sučelju (UI) odabire željeni termin.
- UI šalje zahtjev API-ju za rezervaciju.
- API provjerava u bazi je li termin dostupan.
- Ako je termin slobodan, rezervacija se sprema u bazu i korisnik dobiva potvrdu.
- Ako je termin zauzet, korisniku se prikazuje greška.

**PlantUML kod:**

```plantuml
@startuml
actor Korisnik
participant UI
participant API
participant Baza

Korisnik -> UI : odabir termina
UI -> API : zahtjev za rezervaciju
API -> Baza : provjera dostupnosti

alt termin slobodan
    API -> Baza : spremi rezervaciju
    API --> UI : potvrda
else termin zauzet
    API --> UI : greška
end
@enduml
```


## 3) Class dijagram

**Pitanje:** Od čega se sustav sastoji i kako su entiteti povezani?

**Objašnjenje (sažeto):**
- Korisnik ima više rezervacija; Admin je specijalizirani korisnik (nasljeđivanje).
- Rezervacija se veže na jedan Termin; Termin pripada jednom Terenu i definiran je vremenom unutar radnog vremena.
- Teren ima definirano radno vrijeme (jedan teren – više pravila radnog vremena).
- Validacija kolizije sprječava dvostruku rezervaciju.

PlantUML Kod:  

```plantuml
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
```
