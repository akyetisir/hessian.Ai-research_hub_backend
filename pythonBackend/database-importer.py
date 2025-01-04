import json
from pymongo import MongoClient
import gridfs
import requests
from requests.exceptions import RequestException
from dotenv import load_dotenv
import os
import fitz  # PyMuPDF

load_dotenv()

uri = os.getenv("MongoDB-uri")

def extract_metadata_from_json(json_file):
    with open(json_file, 'r') as f:
        papers_data = json.load(f)
    
    papers = []
    for entry in papers_data:
        # Autoreninformationen sammeln
        authors = []
        if 'authors' in entry:
            authors = [author["name"] for author in entry.get("authors", [])]
        elif 'creators' in entry.get('metadata', {}):
            authors = [creator["name"] for creator in entry['metadata'].get('creators', [])]

        paper = {
            "titel": entry.get("title", "") or entry.get("metadata", {}).get("title", ""),
            "authors": authors,
            "published": entry.get("pubdate", None) or entry.get("metadata", {}).get("publication_date", None),
            "abstract": entry.get("description", "") or entry.get("metadata", {}).get("description", ""),
            "citations": entry.get("pmcrefcount", 0),
            "relevance": 0,
            "pdf": None,
            "picture": "default_image_url.jpg",
            "content": None,
            "doi": entry.get("doi", "") or entry.get("metadata", {}).get("doi", ""),
            "journal": entry.get("source", "") or entry.get("metadata", {}).get("journal", {}).get("title", ""),
            "platforms": ["PlatformName"],  # Beispiel-Plattform, du kannst sie anpassen
            "views": 0
        }
        
        # PDF Link finden und überprüfen
        if 'files' in entry and len(entry['files']) > 0:
            paper["pdf"] = entry['files'][0]['links']['self']

        papers.append(paper)

    return papers

def save_pdf_to_gridfs(pdf_url, fs):
    if not pdf_url.startswith(('http://', 'https://')):
        print(f"Ungültiger PDF-Link: {pdf_url}")
        return None, None

    try:
        response = requests.get(pdf_url)
        response.raise_for_status()
        pdf_content = response.content
    except RequestException as e:
        print(f"Fehler beim Abrufen der PDF: {e}")
        return None, None
    
    try:
        pdf_id = fs.put(pdf_content, filename=pdf_url.split('/')[-1])

        # PDF-Text extrahieren
        with fitz.open(stream=pdf_content, filetype="pdf") as doc:
            content = ""
            for page in doc:
                content += page.get_text()

        return pdf_id, content

    except (fitz.FileDataError, fitz.FileTypeError) as e:
        print(f"Fehler beim Öffnen der PDF-Datei: {e}")
        return None, None

def save_to_mongodb(papers):
    client = MongoClient(uri)
    db = client["researchhub"]
    fs = gridfs.GridFS(db)
    collection = db["papers"]

    for paper in papers:
        if paper["pdf"]:
            pdf_id, content = save_pdf_to_gridfs(paper["pdf"], fs)
            if pdf_id and content:
                paper["pdf_id"] = pdf_id
                paper["content"] = content
                del paper["pdf"]
            else:
                paper["pdf"] = None
                paper["content"] = None
        
        collection.insert_one(paper)
        print(f"Paper '{paper['titel']}' erfolgreich gespeichert.")

if __name__ == "__main__":
    papers = extract_metadata_from_json("combined_results.json")
    print("Extracted Metadata:", papers)
    save_to_mongodb(papers)







