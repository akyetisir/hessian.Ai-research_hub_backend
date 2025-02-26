import os
import json
import requests
from pymongo import MongoClient
from dotenv import load_dotenv

# Lade Umgebungsvariablen aus der .env-Datei
load_dotenv()

MONGO_URI = os.getenv("MongoDB-uri", "mongodb://localhost:27017/")
DB_NAME = os.getenv("db", "testdb")
AUTHORS_COLLECTION = "authors"

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

    headers = {
        # "x-api-key": "DEIN-API-KEY"
    }
    
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        print(f"Fehler beim Abruf der Daten für Autor-ID {author_id}. Status Code: {response.status_code}")
        return None
    
    data = response.json()
    
    h_index = data.get("hIndex", 0)
    citation_count = data.get("citationCount", 0)
    
    papers_data = data.get("papers", [])
    papers_list = []
    
    for paper in papers_data:
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
    Stellt eine Verbindung zur MongoDB her, holt alle Autoren aus der Collection 'authors'
    der Datenbank DB_NAME, und für jeden Autor:
      - Für jede enthaltene Semantic Scholar ID werden API-Daten abgerufen
      - Die Ergebnisse (Paper-Infos) werden zusammengeführt (Duplikate werden entfernt)
      - Eine JSON-Datei im Ordner 'semanticAPI/<AutorName>/<AutorName>.json' erstellt
    """
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]
    authors_collection = db[AUTHORS_COLLECTION]
    
    # Alle Autoren aus der Collection abrufen
    authors_cursor = authors_collection.find()
    
    for author in authors_cursor:
        author_name = author.get("name", "unbekannt")
        semantic_ids = author.get("semantic_scholar_id", [])
        
        if not semantic_ids or not isinstance(semantic_ids, list):
            print(f"Für Autor/in '{author_name}' wurden keine Semantic Scholar IDs gefunden. Überspringe...")
            continue
        
        combined_hIndex = 0
        combined_citationCount = 0
        papers_dict = {}  # Verhindert Duplikate basierend auf paperId
        
        for sem_id in semantic_ids:
            sem_id = sem_id.strip()
            if not sem_id:
                continue
            
            author_data = fetch_author_data(sem_id)
            if author_data is None:
                continue
            
            # Bei mehreren IDs: Es wird der maximale hIndex und citationCount übernommen
            combined_hIndex = max(combined_hIndex, author_data.get("hIndex", 0))
            combined_citationCount = max(combined_citationCount, author_data.get("citationCount", 0))
            
            for paper in author_data.get("papers", []):
                paper_id = paper.get("paperId")
                if paper_id and paper_id not in papers_dict:
                    papers_dict[paper_id] = paper
        
        if not papers_dict:
            print(f"Keine Paper-Daten für Autor/in '{author_name}' gefunden. Überspringe...")
            continue
        
        combined_result = {
            "hIndex": combined_hIndex,
            "citationCount": combined_citationCount,
            "papers": list(papers_dict.values())
        }
        
        folder_path = os.path.join("semanticAPI", author_name)
        os.makedirs(folder_path, exist_ok=True)
        
        output_file = os.path.join(folder_path, f"{author_name}.json")
        with open(output_file, "w", encoding="utf-8") as out_f:
            json.dump(combined_result, out_f, ensure_ascii=False, indent=2)
        
        print(f"Fertig: {output_file} erstellt.")

if __name__ == "__main__":
    main()
