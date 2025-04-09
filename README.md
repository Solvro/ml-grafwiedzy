# ml-grafwiedzy

## Opis

Ten projekt wykorzystuje `pyproject.toml` oraz `Poetry` do zarządzania zależnościami i środowiskiem Pythona.

## Wymagania

- Python 3.10+
- Poetry
- Neo4j
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
- data/: Folder przeznaczony na dane używane przez projekt.
- notebooks/: Folder zawierający notatniki Jupyter do eksploracji danych i prototypowania.
- scripts/: Folder zawierający skrypty uruchomieniowe i pomocnicze.

## Konfiguracja Neo4j

Projekt wykorzystuje Neo4j uruchomiony w kontenerze Dockera.

### **Uruchamianie Neo4j w Dockerze**

Najpierw upewnij się, że masz zainstalowany **Docker** i **Docker Compose**. Następnie w katalogu głównym projektu utwórz plik docker-compose.yml (jeśli jeszcze go nie ma) i dodaj:

```yaml
services:
  neo4j:
    image: neo4j:2025.03.0
    container_name: neo4j_container
    restart: unless-stopped
    ports:
      - "7474:7474"
      - "7687:7687"
    environment:
      NEO4J_AUTH: neo4j/testpassword
    volumes:
      - neo4j_data:/data
      - neo4j_logs:/logs

volumes:
  neo4j_data:
  neo4j_logs:
```

### **Uruchomienie Neo4j**

Aby uruchomić bazę danych, wykonaj:

```sh
docker-compose up -d
```

Po uruchomieniu możesz wejść w panel administracyjny Neo4j pod adresem:
➡ **http://localhost:7474/**
**Login:** `neo4j`
**Hasło:** `testpassword`

### **Utwórz plik** `.env` w katalogu głównym projektu i dodaj:

Dla aplikacji działającej na tym samym komputerze co Docker:
```ini
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=testpassword
```

Dla aplikacji działającej w kontenerze razem z Neo4j:
```ini
NEO4J_URI=bolt://neo4j_container:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=testpassword
```

### **Załaduj zmienne w kodzie** – w pliku `src/topwr_ml/config.py`:

```python
import os
from dotenv import load_dotenv

# Wczytanie zmiennych z pliku .env
load_dotenv()

NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USER = os.getenv("NEO4J_USER")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")
```

### **Użyj konfiguracji w module obsługi bazy Neo4j** (`src/topwr_ml/graph/connection.py`):

```python
from py2neo import Graph
from src.topwr_ml.config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD

# Inicjalizacja połączenia z Neo4j
graph = Graph(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
```

### Restartowanie bazy Neo4j

Jeśli chcesz zatrzymać i ponownie uruchomić bazę, użyj:

```sh
docker-compose down
docker-compose up -d
```

## Uruchamianie skryptów

Aby uruchomić skrypt, który tworzy graf, użyj:

```bash
poetry run python scripts/run_graph.py
```

Skrypt ten:
* Ładuje dane z pliku CSV lub innego źródła
* Tworzy węzły i relacje w bazie Neo4j
* Umożliwia analizę danych w grafie

## Wykonywanie zapytań Cypher

Aby wykonać zapytania Cypher w bazie Neo4j, możesz użyć modułu `queries.py`:

```python
from src.topwr_ml.graph.queries import run_query

query = "MATCH (n:Person) RETURN n LIMIT 10"
results = run_query(query)

print("Wyniki zapytania:", results)
```

## Testowanie

Aby przetestować działanie grafu wiedzy, możesz napisać testy w folderze `tests/`.

Każdy test powinien sprawdzać:
* Łączenie z bazą Neo4j
* Tworzenie węzłów i krawędzi
* Wykonywanie zapytań Cypher i sprawdzanie wyników

Przykład testu:

```python
def test_graph_connection():
    from src.topwr_ml.graph.connection import graph
    assert graph is not None
```