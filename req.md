# Projekt: Sustav za rezervaciju teniskog termina

## Članovi tima
- Luka Kurtović  
- Ante Galić  
- Ivo Janković  
- Lucian Vranković  
- Lea Babić  

## GitHub repozitorij
- Link: https://github.com/lkurtovic/Sustav-za-rezervaciju-teniskog-termina
- Svi članovi dodani: DA

## User storyji
  US-01 Kao prijavljeni korisnik, želim pregledati slobodne termine kako bih mogao rezervirati termin.   
  US-02 Kao admin, želim moći upravljati terenima i terminima unutar terena.  


## Funkcijski zahtjevi
  FZ-01 Sustav mora omogućiti pregled slobodnih termina za odabrani datum.  
  FZ-02 Sustav mora omogućiti filtriranje termina po vremenu i terenu.  
  FZ-03 Sustav mora omogućiti registraciju korisnika.  
  FZ-04 Sustav mora omogućiti prijavu korisnika.  
  FZ-05 Sustav mora omogućiti rezervaciju slobodnog termina.  
  FZ-06 Sustav mora spriječiti dvostruku rezervaciju istog termina. 

  FZ-07 Sustav mora omogućiti adminu kreiranje novog terena.  
  FZ-08 Sustav mora omogućiti adminu izmjenu podataka o terenu.  
  FZ-09 Sustav mora omogućiti adminu otkazivanje bilo koje rezervacije.  
  FZ-10 Sustav mora omogućiti adminu definiranje radnog vremena terena.  

## Nefunkcijski zahtjevi
  NZ-01 Sustav mora prikazati termine u roku od najviše 2 sekunde za 95% zahtjeva.  
  NZ-02 Sustav mora biti dostupan najmanje 99% vremena.  
  NZ-03 Sustav mora sigurno pohranjivati korisničke podatke (lozinke moraju biti hashirane).  
  NZ-04 Sustav mora podržavati najmanje 100 istovremenih korisnika.  
  NZ-05 Sustav mora bilježiti greške u sustavu.    
  NZ-06 Sustav mora biti mikroservis i biti kontenjiziran.  

## Taskovi
  TASK-01	Dizajn baze podataka: Izrada sheme za tablice Users, Admins, Courts i Reservations s potrebnim relacijama.  
  TASK-02	Autentifikacija: Implementacija API endpointova za registraciju i prijavu korisnika (BCrypt + JWT).   
  TASK-03	Logika slobodnih slotova: Razvoj algoritma koji generira listu slobodnih termina na temelju radnog vremena i postojećih rezervacija.  
  TASK-04	Frontend Kalendar: Izrada UI sučelja za pregled termina s mogućnošću filtriranja po datumu i terenu.	  
  TASK-05	Proces rezervacije: Implementacija POST metode za spremanje nove rezervacije u bazu podataka.	 
  TASK-06	Backend Validacija: Implementacija provjere preklapanja termina u bazi kako bi se spriječila dvostruka rezervacija.	  
  TASK-07	Admin CRUD Terena: Izrada sučelja i API-ja za dodavanje novih terena i uređivanje postojećih (ime, podloga, status).  
  TASK-08	Admin Kontrola: Implementacija mogućnosti da admin otkaže bilo koju aktivnu rezervaciju (soft delete ili status cancelled).	  
  TASK-09	Konfiguracija radnog vremena: Izrada sustava za definiranje globalnog početka i kraja radnog vremena kluba.   
  TASK-10	Testiranje sustava: Pisanje Unit i Integracijskih testova za ključne procese (validacija termina i prava pristupa).	  
  TASK-11	Sustav obavijesti: Implementacija slanja potvrde rezervacije (e-mail ili interna notifikacija).	 
  TASK-12 Izrada containera i upravljanje dockerom.

## Raspodjela zadataka
  Luka: TASK-01, TASK-02, TASK-12, FZ-03, FZ-04  
  Ante: TASK-03, TASK-04, FZ-01, FZ-02  
  Ivo: TASK-05, TASK-06, FZ-05, FZ-06  
  Lucian: TASK-07, TASK-08, FZ-07, FZ-08, FZ-09  
  Lea: TASK-09, TASK-10, TASK-11, FZ-10, FZ-05, FZ-06  
