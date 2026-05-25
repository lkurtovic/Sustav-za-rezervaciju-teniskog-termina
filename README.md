# Sustav-za-rezervaciju-teniskog-termina.

## 🚀 Brzo pokretanje projekta unutar Docker kontejnera

Ovaj projekt je u potpunosti kontejneriziran pomoću **Dockera**. To znači da aplikaciju možete pokrenuti na bilo kojem računalu (Windows, Mac, Linux) u svega nekoliko koraka, bez potrebe za lokalnom instalacijom Pythona, virtualnih okruženja (`venv`) ili ručnim instaliranjem paketa.

### 📋 Preduvjeti

Prije nego što započnete, provjerite imate li instalirano sljedeće:
1. **Git** ([Preuzmi Git](https://git-scm.com/))
2. **Docker Desktop** ([Preuzmi Docker](https://www.docker.com/products/docker-desktop/)) - *pazite da je aplikacija pokrenuta prije izvršavanja naredbi*.

---

### 🛠️ Koraci za pokretanje

Otvorite svoj terminal (PowerShell, CMD ili Terminal na Macu) i izvršite sljedeće naredbe:

#### 1. Kloniranje repozitorija
Preuzmite izvorni kod projekta na svoje računalo i uđite u direktorij projekta:
```bash
git clone https://github.com/lkurtovic/Sustav-za-rezervaciju-teniskog-termina.git
cd Sustav-za-rezervaciju-teniskog-termina
```

#### 2. Izgradnja Docker slike (Build)
Upalite svoj Docker Desktop i u terminalu pokrenite izgradnju. Docker će sam pročitati Vaš Dockerfile, skinuti Python 3.11, instalirati sve pakete iz requirements.txt i zapakirati aplikaciju:
```bash
docker build -t tenis-app .
```

#### 3. Korak: Pokretanje aplikacije (Run)
Pokrenite kontejner:
```bash
docker run -d --name tenis-kontejner -p 8000:8000 tenis-app
```

Otvorite preglednik i odite na:
http://localhost:8000

---

## 📚 API dokumentacija

Ova aplikacija koristi server-side HTML stranice i formularske POST zahtjeve (nema klasičnih JSON REST resursa). Povratni sadržaj je uglavnom HTML ili plain-text poruka, uz česta preusmjeravanja (redirect).

**Bazni URL:** `http://localhost:8000`

### ✅ Javne HTML stranice

- **GET /**
	- Opis: Početna (landing) stranica.
	- Odgovor: HTML.

- **GET /signup**
	- Opis: Stranica za registraciju.
	- Odgovor: HTML.

- **GET /login**
	- Opis: Stranica za prijavu.
	- Odgovor: HTML.

- **GET /dashboard**
	- Opis: Upravljačka ploča nakon prijave.
	- Query parametri: `username` (string), `email` (string), `is_admin` (bool), `user_id` (int).
	- Odgovor: HTML.

- **GET /logout**
	- Opis: Odjava korisnika.
	- Odgovor: Redirect (302) na `/`.

### 🔐 Autentifikacija

- **POST /register**
	- Opis: Registracija novog korisnika.
	- Body (JSON):
		- `username` (string)
		- `email` (string)
		- `password` (string)
	- Odgovor: HTML poruka uspjeha i JS preusmjeravanje na `/login`.
	- Greške: `400` ako je korisničko ime zauzeto.

- **POST /token**
	- Opis: Prijava korisnika (form-encoded).
	- Body (application/x-www-form-urlencoded):
		- `username` (string)
		- `password` (string)
	- Odgovor: HTML s JS preusmjeravanjem na `/dashboard` (s query parametrima korisnika).
	- Greške: `401` ako su vjerodajnice neispravne.

### 🎾 Rezervacije

- **GET /reservations**
	- Opis: Pregled slobodnih termina po datumu i terenu.
	- Query parametri:
		- `username` (string)
		- `email` (string)
		- `user_id` (int)
		- `is_admin` (bool)
		- `date_filter` (string, format `YYYY-MM-DD`)
		- `court_filter` (int)
	- Odgovor: HTML s prikazom slotova.

- **POST /reservations/submit**
	- Opis: Kreiranje rezervacije iz forme; radi validaciju preklapanja i šalje e-mail potvrdu.
	- Body (multipart/form-data):
		- `user_id` (int)
		- `court_id` (int)
		- `start_time` (string, ISO 8601 npr. `2026-05-25T12:00:00`)
		- `end_time` (string, ISO 8601)
		- `username` (string)
		- `email` (string)
		- `is_admin` (bool)
	- Odgovor: `text/plain` u formatu `OK|<poruka>`.
	- Greške:
		- `400` neispravan format datuma/vremena ili kraj prije početka
		- `400` pokušaj rezervacije u prošlosti
		- `404` korisnik ili teren ne postoje
		- `409` termin se preklapa s postojećom rezervacijom

### 🛠️ Admin rute (zahtijevaju admin `user_id`)

> Admin provjera se radi preko `user_id` parametra; nema JWT/sesija. Ako `user_id` nedostaje dobiva se `401`, a ako korisnik nije admin `403`.

- **GET /admin/courts**
	- Opis: Pregled i upravljanje terenima.
	- Query parametri: `user_id` (int).
	- Odgovor: HTML.

- **POST /admin/courts**
	- Opis: Kreiranje novog terena.
	- Body (form-data):
		- `user_id` (int)
		- `name` (string)
		- `surface_type` (string)
		- `open_hour` (int, 0-23)
		- `close_hour` (int, 0-23)
		- `is_active` (optional)
	- Odgovor: Redirect (303) na `/admin/courts`.

- **GET /admin/courts/{court_id}/edit**
	- Opis: Forma za uređivanje terena.
	- Query parametri: `user_id` (int).
	- Odgovor: HTML.

- **POST /admin/courts/{court_id}/edit**
	- Opis: Spremanje izmjena terena.
	- Body (form-data):
		- `user_id` (int)
		- `name` (string)
		- `surface_type` (string)
		- `open_hour` (int, 0-23)
		- `close_hour` (int, 0-23)
		- `is_active` (optional)
	- Odgovor: Redirect (303) na `/admin/courts`.

- **GET /admin/reservations**
	- Opis: Pregled svih rezervacija.
	- Query parametri: `user_id` (int).
	- Odgovor: HTML.

- **POST /admin/reservations/{reservation_id}/cancel**
	- Opis: Otkazivanje rezervacije (postavlja status na `cancelled`).
	- Body (form-data): `user_id` (int).
	- Odgovor: Redirect (303) na `/admin/reservations`.
