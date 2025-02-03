import os
import json
import re
import requests
from rapidfuzz import fuzz
from pymongo import MongoClient
from dotenv import load_dotenv

# === .env laden ===
load_dotenv()

MONGO_URI = os.getenv("MongoDB-uri", "mongodb://localhost:27017/")
DB_NAME = os.getenv("db", "testdb")
AUTHORS_COLLECTION = "authors"
PAPERS_COLLECTION = "papers"
SEMANTIC_API_ROOT = "semanticAPI"
MATCH_THRESHOLD = 90

def clean_title(original_title):
    cleaned = re.sub(r'[^a-zA-Z0-9 ]', '_', original_title)
    cleaned = cleaned.replace(' ', '_')
    return cleaned[:50]

def fetch_author_data_in_single_request(author_id):
    """
    Holt alle benötigten Infos in EINEM Request von der Semantic Scholar Graph API:
      - hIndex, citationCount
      - papers (title, paperId, year, publicationDate, isOpenAccess,
                citationCount, influentialCitationCount)
    """
    base_url = "https://api.semanticscholar.org/graph/v1/author/"
    fields = (
        "hIndex,citationCount,"
        "papers.title,papers.paperId,papers.year,"
        "papers.publicationDate,papers.isOpenAccess,"
        "papers.citationCount,papers.influentialCitationCount"
    )
    # Mit limit=1000 holen wir bis zu 1000 Paper pro Autor
    url = f"{base_url}{author_id}?fields={fields}&limit=1000"
    
    headers = {
        # "x-api-key": "DEIN-API-KEY"  # falls du einen hast
    }
    
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print(f"Fehler beim Abruf der Daten für Autor-ID {author_id}. Status Code: {response.status_code}")
        return None
    
    data = response.json()
    
    # Autor-Ebene
    h_index = data.get("hIndex", 0)
    citation_count = data.get("citationCount", 0)
    
    # Paper-Ebene
    papers_list = []
    for p in data.get("papers", []):
        papers_list.append({
            "title": p.get("title", ""),
            "paperId": p.get("paperId", ""),
            "year": p.get("year", None),
            "publicationDate": p.get("publicationDate", ""),
            "isOpenAccess": p.get("isOpenAccess", False),
            "citationCount": p.get("citationCount", 0),
            "influentialCitationCount": p.get("influentialCitationCount", 0)
        })
    
    return {
        "hIndex": h_index,
        "citationCount": citation_count,
        "papers": papers_list
    }

def main():
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]
    authors_col = db[AUTHORS_COLLECTION]
    papers_col = db[PAPERS_COLLECTION]
    
    # Lies die JSON mit (name, id)
    with open("authors_semantic.json", "r", encoding="utf-8") as f:
        authors = json.load(f)
    
    for author in authors:
        author_name = author.get("name", "unbekannt")
        author_id = author.get("id", "").strip()
        
        if not author_id:
            print(f"Keine ID für Autor/in '{author_name}' gefunden oder ID ist leer. Überspringe...")
            continue
        
        # 1. Hole alle Daten in EINEM Request
        author_data = fetch_author_data_in_single_request(author_id)
        if not author_data:
            continue
        
        h_index = author_data["hIndex"]
        citation_count = author_data["citationCount"]
        all_papers = author_data["papers"]  # Liste von dicts
        
        # 2. Summiere HPC über ALLE Paper, egal welches Jahr
        total_hic_for_author = 0
        for paper in all_papers:
            total_hic_for_author += paper["influentialCitationCount"]
        
        # 3. Nur Paper ab 2020 in DB aktualisieren (Fuzzy-Titelabgleich)
        #    (Weil in der DB nur diese Paper existieren)
        author_doc = authors_col.find_one({"name": author_name})
        if not author_doc:
            print(f"Autor '{author_name}' nicht in DB gefunden. Überspringe.")
            continue
        
        author_paper_ids = author_doc.get("papers", [])
        
        for paper in all_papers:
            title = paper["title"]
            year = paper["year"] or 0
            
            if year >= 2020:
                cleaned_title = clean_title(title)
                best_score = 0
                matched_paper_id = None
                
                # Lade die Paper, die zum Autor gehören
                paper_docs = papers_col.find({"_id": {"$in": author_paper_ids}})
                for p_doc in paper_docs:
                    db_title = p_doc.get("title", "")
                    score = fuzz.ratio(cleaned_title.lower(), clean_title(db_title).lower())
                    if score > best_score:
                        best_score = score
                        matched_paper_id = p_doc["_id"]
                
                if matched_paper_id and best_score >= MATCH_THRESHOLD:
                    print(f"Autor: {author_name}, Paper-Match mit Score={best_score}")
                    update_fields = {
                        "citationCount": paper["citationCount"],
                        "highlyInfluentialCitations": paper["influentialCitationCount"]
                    }
                    papers_col.update_one({"_id": matched_paper_id}, {"$set": update_fields})
        
        # 4. Autor in DB aktualisieren (h_index, citations, HPC-Summe)
        authors_col.update_one(
            {"_id": author_doc["_id"]},
            {
                "$set": {
                    "h_index": h_index,
                    "citations": citation_count,
                    "highly_influential_citations": total_hic_for_author
                }
            }
        )
        
        # 5. (Optional) Speichern in einer JSON-Datei local
        #    Falls du weiterhin eine local <AutorName>.json ablegen willst:
        folder_path = os.path.join(SEMANTIC_API_ROOT, author_name)
        os.makedirs(folder_path, exist_ok=True)
        
        output_file = os.path.join(folder_path, f"{author_name}.json")
        with open(output_file, "w", encoding="utf-8") as out_f:
            json.dump(author_data, out_f, ensure_ascii=False, indent=2)
        
        print(f"Autor '{author_name}' aktualisiert. (hIndex={h_index}, citations={citation_count}, HPC={total_hic_for_author})")
    
    client.close()

if __name__ == "__main__":
    main()
