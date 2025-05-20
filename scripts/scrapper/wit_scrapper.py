import requests
from bs4 import BeautifulSoup
import pandas as pd
import re

def clean_text(text):
    """Usuwa nadmiarowe białe znaki i formatowanie tekstu."""
    if text is None:
        return ""
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def get_cell_text(cell):
    """Pobiera tekst z komórki tabeli z uwzględnieniem formatowania."""
    if cell is None:
        return ""
    # Pobierz tekst z wszystkich elementów p w komórce
    p_texts = [clean_text(p.get_text()) for p in cell.find_all('p')]
    # Jeśli nie ma elementów p, pobierz bezpośrednio tekst z komórki
    if not p_texts:
        return clean_text(cell.get_text())
    # Połącz tekst z elementów p
    return " ".join(filter(None, p_texts))

def extract_table_data(table):
    """Ekstrahuje dane z tabeli HTML."""
    rows = table.find_all('tr')
    if len(rows) < 2:
        return []
    
    # Pobierz nagłówki
    header_row = rows[0]
    headers = [get_cell_text(cell) for cell in header_row.find_all(['th', 'td'])]
    
    # Sprawdź czy to tabela z egzaminami
    if not any(header.lower() in ["termin", "data", "godzina"] for header in headers):
        return []
    
    # Standaryzacja nazw kolumn
    standardized_headers = []
    for header in headers:
        header_lower = header.lower()
        if "kierunek" in header_lower or "specjalno" in header_lower:
            standardized_headers.append("Kierunek/Specjalność")
        elif "kod" in header_lower:
            standardized_headers.append("Kod kursu")
        elif "nazwa" in header_lower:
            standardized_headers.append("Nazwa kursu")
        elif "prowadz" in header_lower:
            standardized_headers.append("Prowadzący")
        elif "termin" in header_lower:
            standardized_headers.append("Termin")
        elif "data" in header_lower:
            standardized_headers.append("Data")
        elif "godzina" in header_lower:
            standardized_headers.append("Godzina")
        elif "sala" in header_lower:
            standardized_headers.append("Sala")
        elif "budynek" in header_lower:
            standardized_headers.append("Budynek")
        else:
            standardized_headers.append(header)
    
    # Funkcja do analizy struktury tabeli i obsługi rowspan/colspan
    data = []
    
    # Słownik do śledzenia komórek z rowspan
    rowspan_data = {}
    
    for row_index, row in enumerate(rows[1:], 1):
        row_data = {}
        col_index = 0
        
        cells = row.find_all(['th', 'td'])
        
        # Uzupełnienie danymi z komórek z rowspan z poprzednich wierszy
        for col_idx, col_data in sorted(rowspan_data.items()):
            if row_index in col_data["rows"]:
                row_data[col_data["header"]] = col_data["value"]
                
        # Przetwarzanie komórek w bieżącym wierszu
        for cell_index, cell in enumerate(cells):
            # Przesunięcie indeksu kolumny, aby uwzględnić rowspan z poprzednich wierszy
            while col_index in [span_data["col_index"] for span_data in rowspan_data.values() 
                                if row_index in span_data["rows"]]:
                col_index += 1
            
            # Pobierz tekst z komórki
            cell_text = get_cell_text(cell)
            
            # Pobierz atrybuty rowspan i colspan
            rowspan = int(cell.get('rowspan', 1))
            colspan = int(cell.get('colspan', 1))
            
            # Jeśli komórka ma rowspan > 1, zapisz jej dane do późniejszego wykorzystania
            if rowspan > 1:
                affected_rows = list(range(row_index + 1, row_index + rowspan))
                rowspan_data[len(rowspan_data)] = {
                    "rows": affected_rows,
                    "col_index": col_index,
                    "header": standardized_headers[col_index] if col_index < len(standardized_headers) else f"Column_{col_index}",
                    "value": cell_text
                }
            
            # Zapisz wartość komórki w bieżącym wierszu
            if col_index < len(standardized_headers):
                header = standardized_headers[col_index]
                row_data[header] = cell_text
            
            # Przesunięcie indeksu kolumny z uwzględnieniem colspan
            col_index += colspan
        
        # Dodanie przetworzonych danych wiersza do wynikowej listy
        if row_data:
            # Sprawdź czy mamy do czynienia z wierszem II terminu
            if "Termin" in row_data and "II termin" in row_data["Termin"]:
                # Próba połączenia danych z poprzednim wierszem (I termin)
                if data and all(key in data[-1] for key in ["Kierunek/Specjalność", "Kod kursu", "Nazwa kursu", "Prowadzący"]):
                    for key in ["Kierunek/Specjalność", "Kod kursu", "Nazwa kursu", "Prowadzący"]:
                        if key not in row_data and key in data[-1]:
                            row_data[key] = data[-1][key]
            
            data.append(row_data)
    
    return data

def scrape_exam_schedule():
    """Główna funkcja do pobrania harmonogramu egzaminów."""
    url = "https://wit.pwr.edu.pl/studenci/organizacja-toku-studiow/harmonogram-egzaminow"
    
    print(f"Pobieranie danych z: {url}")
    
    try:
        # Dodanie nagłówków dla lepszej kompatybilności
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
        }
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        html_content = response.content
        print(f"Pobrano stronę (status: {response.status_code})")
    except Exception as e:
        print(f"Błąd podczas pobierania strony: {e}")
        return None
    
    # Parsowanie HTML
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Znalezienie wszystkich tabel na stronie
    tables = soup.find_all('table')
    print(f"Znaleziono {len(tables)} tabel na stronie")
    
    # Lista do przechowywania danych ze wszystkich tabel
    all_data = []
    
    # Przetwarzanie każdej tabeli
    for i, table in enumerate(tables):
        print(f"Analizowanie tabeli {i+1}...")
        table_data = extract_table_data(table)
        if table_data:
            print(f"  - Znaleziono {len(table_data)} rekordów w tabeli {i+1}")
            all_data.extend(table_data)
    
    if not all_data:
        print("Nie znaleziono żadnych danych w tabelach!")
        return None
    
    print(f"Łącznie znaleziono {len(all_data)} rekordów")
    
    # Konwersja do DataFrame
    df = pd.DataFrame(all_data)
    
    # Upewnienie się, że mamy wszystkie standardowe kolumny
    required_columns = ["Kierunek/Specjalność", "Kod kursu", "Nazwa kursu", "Prowadzący", 
                        "Termin", "Data", "Godzina", "Sala", "Budynek"]
    
    for col in required_columns:
        if col not in df.columns:
            df[col] = ""
    
    # Wybór tylko wymaganych kolumn w odpowiedniej kolejności
    df = df[required_columns]
    
    return df

def main():
    # Pobranie danych
    df = scrape_exam_schedule()
    
    if df is not None:
        # Zapisanie do pliku CSV
        output_file = "harmonogram_egzaminow.csv"
        df.to_csv(output_file, index=False, encoding='utf-8-sig')
        print(f"Dane zostały zapisane do pliku {output_file}")
        
        # Wyświetlenie pierwszych kilku wierszy
        print("\nPierwszych 5 wierszy danych:")
        print(df.head(5))
    else:
        print("Nie udało się pobrać danych harmonogramu egzaminów.")

if __name__ == "__main__":
    main()