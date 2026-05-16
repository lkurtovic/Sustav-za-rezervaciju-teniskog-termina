# Koristimo službenu i laganu Python sliku
FROM python:3.11-slim

# Postavljamo radni direktorij unutar kontejnera
WORKDIR /app

# Sprječavamo Python da piše .pyc datoteke i omogućavamo trenutačni ispis logova
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Kopiramo datoteku s paketima i instaliramo ih
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Kopiramo cijeli projekt u kontejner
COPY . .

# Otvaramo port 8000 na kojem radi FastAPI
EXPOSE 8000

# Pokrećemo Uvicorn server pri startu kontejnera
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]