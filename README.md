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
