import os
import json
import requests

def fetch_author_data(author_id):
    """
    Ruft die gewünschten Informationen für eine/n Autor/in (nach ID)
    von der Semantic Scholar Graph API ab.

    Gibt ein Dictionary zurück mit:
      - hIndex
      - citationCount
      - papers (Liste mit allen Paper-Infos)
    """
    base_url = "https://api.semanticscholar.org/graph/v1/author/"
    
    # Felder, die wir aus der API abrufen möchten
    fields = "hIndex,citationCount,papers.title,papers.paperId,papers.year,papers.publicationDate,papers.isOpenAccess"
    
    # Mit 'limit=1000' holen wir bis zu 1000 Paper in einem Request
    url = f"{base_url}{author_id}?fields={fields}&limit=1000"

    # Falls du einen API-Key hast, kannst du ihn hier angeben:
    headers = {
        # "x-api-key": "DEIN-API-KEY"
    }
    
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        print(f"Fehler beim Abruf der Daten für Autor-ID {author_id}. "
              f"Status Code: {response.status_code}")
        return None
    
    data = response.json()
    
    # Autor-Ebene
    h_index = data.get("hIndex", 0)
    citation_count = data.get("citationCount", 0)
    
    # Paper-Ebene
    papers_data = data.get("papers", [])
    papers_list = []
    
    for paper in papers_data:
        # Du kannst bei Bedarf auch .get("journal") oder .get("venue") abrufen,
        # falls das relevant ist. Hier nur die gewünschten Felder:
        papers_list.append({
            "title": paper.get("title", ""),
            "paperId": paper.get("paperId", ""),
            "year": paper.get("year", None),
            "publicationDate": paper.get("publicationDate", ""),
            "isOpenAccess": paper.get("isOpenAccess", False)
        })
    
    result = {
        "hIndex": h_index,
        "citationCount": citation_count,
        "papers": papers_list
    }
    return result

def main():
    """
    Liest eine lokale JSON-Datei 'authors_semantic.json' ein,
    die eine Liste von Autor*innen mit 'name' und 'id' enthält.

    Für jede/n Autor*in mit einer nicht-leeren ID werden
    die Daten (hIndex, citationCount, + Paperinfos) von Semantic Scholar abgefragt
    und in /semanticAPI/<AutorName>/<AutorName>.json gespeichert.
    """
    # 1. JSON mit Autor*innen laden
    with open("authors_semantic.json", "r", encoding="utf-8") as f:
        authors = json.load(f)
    
    for author in authors:
        author_name = author.get("name", "unbekannt")
        author_id = author.get("id", "").strip()
        
        # Überspringe Autor*innen ohne (gültige) ID
        if not author_id:
            print(f"Keine ID für Autor/in '{author_name}' gefunden oder ID ist leer. Überspringe...")
            continue
        
        # 2. Daten von der Semantic Scholar API abrufen
        author_data = fetch_author_data(author_id)
        if author_data is None:
            # Falls ein Fehler aufgetreten ist, weiter zum nächsten Autor
            continue
        
        # 3. Ordner erstellen: /semanticAPI/<AutorName>
        folder_path = os.path.join("semanticAPI", author_name)
        os.makedirs(folder_path, exist_ok=True)
        
        # 4. Ergebnis in JSON-Datei schreiben: /semanticAPI/<AutorName>/<AutorName>.json
        output_file = os.path.join(folder_path, f"{author_name}.json")
        
        with open(output_file, "w", encoding="utf-8") as out_f:
            json.dump(author_data, out_f, ensure_ascii=False, indent=2)
        
        print(f"Fertig: {output_file} erstellt.")

if __name__ == "__main__":
    main()
