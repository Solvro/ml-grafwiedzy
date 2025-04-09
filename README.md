# ml-grafwiedzy

## Opis

Ten projekt wykorzystuje `pyproject.toml` oraz `Poetry` do zarządzania zależnościami i środowiskiem Pythona.

## Wymagania

- Python 3.10+
- Poetry

## Instalacja Poetry

Jeśli nie masz zainstalowanego Poetry, możesz to zrobić za pomocą poniższego polecenia:

```sh
curl -sSL https://install.python-poetry.org | python3 -
```

## Jak używać?

### Instalacja zależności

Po sklonowaniu repozytorium przejdź do katalogu projektu i uruchom:

```sh
poetry install
```

### Uruchamianie środowiska wirtualnego

Aby uruchomić interaktywne środowisko wirtualne, użyj:

```sh
poetry shell
```

### Dodawanie zależności

Aby dodać nową zależność do projektu, użyj:

```sh
poetry add <nazwa_pakietu>
```

Przykład:

```sh
poetry add numpy
```

### Uruchamianie skryptów

Jeśli masz plik `main.py`, możesz go uruchomić bezpośrednio przez Poetry:

```sh
poetry run python main.py
```
## Struktura projektu

- pyproject.toml: Główna konfiguracja projektu, w tym zależności, narzędzia do formatowania i inne ustawienia.
- README.md: Dokumentacja projektu.
- src/: Folder zawierający kod źródłowy projektu.

## Jak uruchomić scrapper ? 

### Zainstaluj zależności scrappera
```bash
poetry install --only scraper
```
### Uruchom scrapper.py
```bash
poetry run scrapper <sciezka_dostepu> <poziom_zaglebienia> <ilosc_watkow> <strona_poczatkowa>
```
gdzie :
- sciezka_dostepu -> miejsce, gdzie zostaną zapisane dane 
- poziom_zaglebienia -> poziom zagłębienia się scrappera
- ilosc_watkow -> ilość wątków do pobierania danych
- strona_poczatkowa -> punkt zaczepienia scrappera i jego klucz

Na przykład :

```bash
poetry run scrapper "dane_test/" 0 2 "https://wit.pwr.edu.pl/"  
```
