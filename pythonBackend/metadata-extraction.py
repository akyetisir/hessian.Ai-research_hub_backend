import xml.etree.ElementTree as ET
import json
from pymongo import MongoClient
from pymongo.errors import PyMongoError
import requests
from dotenv import load_dotenv
import os
import fitz  # PyMuPDF
import re
import hashlib  # Für MD5-Hash

load_dotenv()

uri = os.getenv("MongoDB-uri")

# Verbindung zur MongoDB herstellen
client = MongoClient(uri)
db = client["researchhub"]

# Collections
papers_collection = db["papers"]
authors_collection = db["authors"]

# Platzhalterbild
PLACEHOLDER_IMAGE_PATH = "images/placeholder_author.png"

# Liste der relevanten Autoren
author_names = [
    "Mira Mezini", "Kristian Kersting", "Stefan Roth", "Constantin Rothkopf", "Visvanathan Ramesh",
    "Michael Guckert", "Christin Seifert", "Jan Peters", "Iryna Gurevych", "Carsten Binnig",
    "Oskar von Stryk", "Andreas Koch", "Peter Buxmann", "Oliver Hinz", "Andreas Hackethal",
    "Bernd Freisleben", "Thomas Nauss", "Alexander Goesmann", "Gerd Stumme", "Alexander Gepperth",
    "Ulrich Schwanecke", "Martin Kappes", "Bernhard Humm", "Frank Jäkel", "Heinz Koeppl",
    "Sascha Steffen", "Bernhard Seeger", "Georgia Chalvatzaki", "Li Zhang", "Hilde Kühne",
    "Hongbin Zhang", "Gemma Roig", "Thomas Wallis", "Angela Yu", "Dominik L. Michels",
    "Oliver Weeger", "Anna Rohrbach", "Marcus Rohrbach", "Mohammad Emtiyaz Khan", "Michael Klesel",
    "Alexander Oppermann", "Kawa Nazemi", "Ekaterina Jussupow", "Lucas Böttcher", "Martin Kumm",
    "Martin Potthast", "Marcel H. Schulz", "Hamed Shariat Yazdi", "Justus Thies", "Alexander Benlian",
    "Pavel Osinenko", "Martin Mundt", "Simone Schaub-Meyer", "Carlo d’Eramo", "Anirban Mukhopadhyay",
    "Jörg Schlötterer", "Hinrich Schütze", "Wolfgang Wahlster", "Sriraam Natarajan"
]


def normalize_apostrophe(name: str) -> str:
    """Ersetzt typografische Apostrophe durch gerade Apostrophe."""
    return name.replace("’", "'")


# Funktion zur Normalisierung des Titels
def normalize_title(title: str, max_length: int = 50) -> str:
    normalized_title = title.lower()
    normalized_title = re.sub(r'[^a-z0-9._-]', '_', normalized_title)
    normalized_title = re.sub(r'_+', '_', normalized_title)
    normalized_title = normalized_title[:max_length].strip('_')
    return normalized_title

# Funktion zur Normalisierung von Autorennamen
def normalize_author_name(name: str) -> str:
    """Normalisiert den Namen eines Autors, um unterschiedliche Formate zu berücksichtigen."""
    name = name.strip().lower()  # Leerzeichen entfernen und in Kleinbuchstaben umwandeln

    # Fall: Name enthält nur einen Buchstaben (z. B. "Buxmann P")
    if len(name.split()) == 2 and len(name.split()[1]) == 1:
        last_name, first_initial = name.split()
        return f"{last_name}, {first_initial}"

    # Fall: Name ist in der Form "P Buxmann"
    if len(name.split()) == 2 and len(name.split()[0]) == 1:
        first_initial, last_name = name.split()
        return f"{last_name}, {first_initial}"

    # Fall: Name ist in der Form "Peter Buxmann"
    if len(name.split()) == 2:
        first_name, last_name = name.split()
        return f"{last_name}, {first_name}"

    # Fall: Name ist bereits in der Form "Buxmann, Peter"
    if "," in name:
        return name

    # Standardfall: Name bleibt unverändert
    return name

def convert_to_json_format(name: str) -> str:
    """Wandelt einen Namen in das JSON-Format um (z. B. 'Carlo d’Eramo' → 'D'Eramo C')."""
    name = normalize_apostrophe(name)  # Apostrophe normalisieren
    parts = name.strip().split()
    if len(parts) == 2:
        first_name, last_name = parts
        return f"{last_name} {first_name[0]}"  # "D'Eramo C"
    elif len(parts) >= 3:
        last_name = parts[-1]
        first_names = "".join([part[0] for part in parts[:-1]])  # "HS" für "Hamed Shariat"
        return f"{last_name} {first_names}"  # "Yazdi HS"
    return name  # Fallback

def is_relevant_author(json_author_name: str, relevant_authors: list) -> str:
    """Überprüft, ob ein Autor aus einer JSON-Datei in der Liste der relevanten Autoren enthalten ist.
    Gibt den ursprünglichen Namen aus der Liste zurück, falls ein Treffer gefunden wird."""
    json_author_name = normalize_apostrophe(json_author_name)  # Apostrophe in JSON-Namen normalisieren
    for author in relevant_authors:
        json_format_name = convert_to_json_format(author)  # Namen aus der Liste in JSON-Format umwandeln
        json_format_name = normalize_apostrophe(json_format_name)  # Apostrophe in JSON-Format-Namen normalisieren
        if json_format_name.lower() == json_author_name.lower():
            return author  # Ursprünglicher Name aus der Liste
    return None  # Kein Treffer

# Funktion zur Extraktion des Jahres aus dem pubdate-Feld (für JSON)
def extract_year(pubdate: str) -> int:
    """Extrahiert das Jahr aus dem pubdate-Feld."""
    try:
        return int(pubdate.split()[0])  # Extrahiert das erste Element (Jahr)
    except (ValueError, IndexError):
        return 0  # Rückgabe 0, wenn das Jahr nicht extrahiert werden kann

# Funktion zur Extraktion der Metadaten aus XML-Dateien
def extract_metadata_from_xml(xml_file, pdf_directory):
    try:
        tree = ET.parse(xml_file)
        root = tree.getroot()
    except ET.ParseError as e:
        print(f"Fehler beim Parsen der XML-Datei {xml_file}: {e}")
        return []

    namespaces = {prefix: uri for event, (prefix, uri) in ET.iterparse(xml_file, events=['start-ns'])}

    papers = []
    for entry in root.findall(".//entry", namespaces=namespaces):
        try:
            published_date = entry.find("published", namespaces=namespaces).text if entry.find("published", namespaces=namespaces) is not None else None

            if published_date and int(published_date.split("-")[0]) >= 2020:
                paper_title = entry.find("title", namespaces=namespaces)
                abstract_elem = entry.find("summary", namespaces=namespaces)
                citations_elem = entry.find("citations", namespaces=namespaces)

                paper = {
                    "title": paper_title.text if paper_title is not None else "Untitled",
                    "authors": [
                        author.find("name", namespaces=namespaces).text 
                        for author in entry.findall("author", namespaces=namespaces)
                        if author.find("name", namespaces=namespaces) is not None
                    ],
                    "published": published_date,
                    "abstract": abstract_elem.text if abstract_elem is not None else None,
                    "citations": int(citations_elem.text) if citations_elem is not None else 0,
                    "relevance": 0, 
                    "pdf": None,
                    "path_image": None,
                    "content": None,
                    "doi": entry.find("doi", namespaces=namespaces).text if entry.find("doi", namespaces=namespaces) else None,
                    "journal": entry.find("journal", namespaces=namespaces).text if entry.find("journal", namespaces=namespaces) else None,
                    "platforms": ["arXiv"],
                    "views": 0,
                    "path": None,
                    "is_hess_paper": "no_verified",
                    "paper_md5_hash": None
                }

                pdf_link = entry.find("link[@title='pdf']", namespaces=namespaces)
                if pdf_link is not None:
                    paper["pdf"] = pdf_link.attrib.get('href', None)

                    title_raw = paper["title"] or ""
                    title_norm = normalize_title(title_raw)

                    found_file = None
                    for root_dir, _, files in os.walk(pdf_directory):
                        for file in files:
                            file_norm = normalize_title(file)
                            if title_norm in file_norm:
                                absolute_path = os.path.join(root_dir, file)
                                relative_path = os.path.relpath(absolute_path, pdf_directory)
                                paper["path"] = os.path.join("pdfs", relative_path)
                                found_file = file
                                break
                        if paper["path"]:
                            break

                    if not found_file:
                        print(f"[DEBUG] Keine passende PDF-Datei gefunden für '{title_raw}' in {pdf_directory}")
                
                papers.append(paper)

        except Exception as e:
            print(f"Fehler beim Verarbeiten eines Eintrags in {xml_file}: {e}")

    return papers

def extract_metadata_from_json(json_file, pdf_directory):
    try:
        with open(json_file, 'r', encoding='utf-8') as file:
            data = json.load(file)
    except json.JSONDecodeError as e:
        print(f"Fehler beim Parsen der JSON-Datei {json_file}: {e}")
        return []

    papers = []
    for entry in data:
        try:
            pubdate = entry.get("pubdate", "")
            year = extract_year(pubdate)  # Jahr extrahieren
            if year >= 2020:  # Nur Papers ab 2020
                paper = {
                    "title": entry.get("title", "Untitled"),
                    "authors": [author["name"] for author in entry.get("authors", []) if "name" in author],  # Namen unverändert lassen
                    "published": pubdate,
                    "abstract": None,  # JSON enthält kein Abstract-Feld
                    "citations": 0,  # JSON enthält kein Zitationsfeld
                    "relevance": 0,
                    "pdf": None,
                    "path_image": None,
                    "content": None,
                    "doi": next((id["value"] for id in entry.get("articleids", []) if id["idtype"] == "doi"), None),
                    "journal": entry.get("fulljournalname", None),
                    "platforms": ["PubMed"],
                    "views": 0,
                    "path": None,
                    "is_hess_paper": "no_verified",
                    "paper_md5_hash": None
                }

                # PDF-Datei im Verzeichnis suchen
                title_raw = paper["title"] or ""
                title_norm = normalize_title(title_raw)
                found_file = None
                for root_dir, _, files in os.walk(pdf_directory):
                    for file in files:
                        file_norm = normalize_title(file)
                        if title_norm in file_norm:
                            absolute_path = os.path.join(root_dir, file)
                            relative_path = os.path.relpath(absolute_path, pdf_directory)
                            paper["path"] = os.path.join("pdfs", relative_path)
                            paper["pdf"] = absolute_path  # Lokaler Pfad zur PDF
                            found_file = file
                            break
                    if paper["path"]:
                        break

                if not found_file:
                    print(f"[DEBUG] Keine passende PDF-Datei gefunden für '{title_raw}' in {pdf_directory}")
                else:
                    papers.append(paper)  # Nur Papers mit gültigem Pfad hinzufügen

        except Exception as e:
            print(f"Fehler beim Verarbeiten eines Eintrags in {json_file}: {e}")

    return papers

# Funktion zur Extraktion des PDF-Inhalts (für XML-Papers über URL, für JSON-Papers lokal)
def extract_pdf_content(pdf_source, paper, is_json=False):
    try:
        if is_json:
            # Lokale PDF-Datei öffnen
            with open(pdf_source, "rb") as f:
                pdf_content = f.read()
        else:
            # PDF über URL herunterladen
            response = requests.get(pdf_source)
            response.raise_for_status()
            pdf_content = response.content

        # MD5-Hash des PDFs berechnen
        md5_hash = hashlib.md5(pdf_content).hexdigest()
        paper["paper_md5_hash"] = md5_hash

        pdf_text = ""
        image_saved = False
        if not os.path.exists("images"):
            os.makedirs("images")
        with fitz.open(stream=pdf_content, filetype="pdf") as doc:
            for page in doc:
                pdf_text += page.get_text()
                image_list = page.get_images(full=True)
                for img_index, img in enumerate(image_list):
                    xref = img[0]
                    base_image = doc.extract_image(xref)
                    image_bytes = base_image["image"]
                    img_extension = base_image["ext"]
                    image_filename = f"{paper['title'][:20]}_{img_index}.{img_extension}"
                    image_path = os.path.join("images", image_filename)
                    with open(image_path, "wb") as img_file:
                        img_file.write(image_bytes)
                    paper["path_image"] = image_path
                    image_saved = True
                    break
                if image_saved:
                    break

        return pdf_text

    except requests.exceptions.RequestException as e:
        print(f"Fehler beim Abrufen der PDF: {e}")
        return None
    except Exception as e:
        print(f"Fehler beim Öffnen/Verarbeiten der PDF-Datei: {e}")
        return None

# Funktion zur Klassifizierung des Papers
def classify_paper(content):
    if re.search(r'\bhessian\.ai\b', content, re.IGNORECASE) or re.search(r'\bhessian ai\b', content, re.IGNORECASE):
        return "yes_verified"
    elif re.search(r'\btu darmstadt\b', content, re.IGNORECASE) or re.search(r'\btechnische universität darmstadt\b', content, re.IGNORECASE) or re.search(r'\btechnical university darmstadt\b', content, re.IGNORECASE) or re.search(r'@tu-darmstadt\.de\b', content, re.IGNORECASE):
        return "most_probably_a_hess_paper"
    else:
        return "maybe_not_a_hess_paper"

def save_to_mongodb(papers, is_json=False):
    no_pdf_papers = []  # Liste der Papers ohne PDF

    for paper in papers:
        if paper["path"]:  # Nur Papers mit gültigem Pfad verarbeiten
            if paper["pdf"]:
                content = extract_pdf_content(paper["pdf"], paper, is_json=is_json)
                if content:
                    paper["content"] = content
                    paper["is_hess_paper"] = classify_paper(content)
                else:
                    print(f"Fehler beim Speichern des Inhalts für das Paper '{paper['title']}'")
                    paper["pdf"] = None
                    paper["content"] = None
                    paper["is_hess_paper"] = "no_verified"

            try:
                existing_paper = papers_collection.find_one({"paper_md5_hash": paper["paper_md5_hash"]})
                if existing_paper:
                    update_fields = {k: v for k, v in paper.items() if k != "picture"}
                    papers_collection.update_one({"_id": existing_paper["_id"]}, {"$set": update_fields})
                    print(f"Paper '{paper['title']}' erfolgreich aktualisiert (path={paper['path']}, path_image={paper['path_image']}).")
                    paper_id = existing_paper["_id"]  # Verwende die vorhandene _id
                else:
                    result = papers_collection.insert_one(paper)
                    paper_id = result.inserted_id  # Hole die _id des neu eingefügten Papers
                    print(f"Paper '{paper['title']}' erfolgreich gespeichert (path={paper['path']}, path_image={paper['path_image']}).")

                # Autoren in die authors-Collection schreiben
                for author_name in paper["authors"]:
                    if is_json:
                        # Bei JSON-Dateien: Namen aus der Liste in JSON-Format umwandeln und vergleichen
                        original_name = is_relevant_author(author_name, author_names)
                        if original_name:
                            author = authors_collection.find_one({"name": original_name})
                            if author:
                                # Autor existiert bereits: Paper-ID zur Liste der Papers hinzufügen
                                authors_collection.update_one(
                                    {"_id": author["_id"]},
                                    {"$addToSet": {"papers": paper_id}}  # Verhindert Duplikate
                                )
                            else:
                                # Neuen Autor erstellen
                                author_data = {
                                    "name": original_name,
                                    "papers": [paper_id],  # Verweis auf das aktuelle Paper
                                    "semantic_scholar_id": None,
                                    "h_index": 0,
                                    "citations": 0,
                                    "highly_influential_citations": 0,
                                    "image_path": PLACEHOLDER_IMAGE_PATH,
                                    "email": ""
                                }
                                authors_collection.insert_one(author_data)
                    else:
                        # Bei XML-Dateien: Namen unverändert verwenden
                        if author_name in author_names:
                            author = authors_collection.find_one({"name": author_name})
                            if author:
                                authors_collection.update_one(
                                    {"_id": author["_id"]},
                                    {"$addToSet": {"papers": paper_id}}
                                )
                            else:
                                author_data = {
                                    "name": author_name,
                                    "papers": [paper_id],
                                    "semantic_scholar_id": None,
                                    "h_index": 0,
                                    "citations": 0,
                                    "highly_influential_citations": 0,
                                    "image_path": PLACEHOLDER_IMAGE_PATH,
                                    "email": ""
                                }
                                authors_collection.insert_one(author_data)

            except PyMongoError as e:
                print(f"Fehler beim Speichern des Papers '{paper['title']}']: {e}")
        else:
            no_pdf_papers.append(paper)  # Papers ohne Pfad zur Liste hinzufügen

    return no_pdf_papers

# Funktion zur Verarbeitung aller Dateien (XML und JSON)
def process_all_files(xml_directory, json_directory, pdf_directory):
    no_pdf_papers_all = []  # Gesamtliste der Papers ohne Pfad

    # Verarbeite XML-Dateien
    for root_dir, _, files in os.walk(xml_directory):
        for file in files:
            if file.endswith(".xml"):
                xml_path = os.path.join(root_dir, file)
                papers = extract_metadata_from_xml(xml_path, pdf_directory)
                print(f"[DEBUG] Extracted {len(papers)} papers from {file}")
                no_pdf_papers = save_to_mongodb(papers, is_json=False)
                no_pdf_papers_all.extend(no_pdf_papers)

    # Verarbeite JSON-Dateien
    for root_dir, _, files in os.walk(json_directory):
        for file in files:
            if file.endswith(".json"):
                json_path = os.path.join(root_dir, file)
                papers = extract_metadata_from_json(json_path, pdf_directory)
                print(f"[DEBUG] Extracted {len(papers)} papers from {file}")
                no_pdf_papers = save_to_mongodb(papers, is_json=True)
                no_pdf_papers_all.extend(no_pdf_papers)

    print(f"[INFO] Anzahl der Papers ohne Pfad: {len(no_pdf_papers_all)}")
    if no_pdf_papers_all:
        print("[INFO] Papers ohne Pfad:")
        for paper in no_pdf_papers_all:
            print(f"- {paper['title']}")

# Hauptprogramm
if __name__ == "__main__":
    xml_directory = "/Users/yusuf/VSCodeProjects/hessian.Ai-research_hub_backend/xmls"
    json_directory = "/Users/yusuf/VSCodeProjects/hessian.Ai-research_hub_backend/jsons"
    pdf_directory = "/Users/yusuf/VSCodeProjects/hessian.Ai-research_hub_backend/pdfs"
    process_all_files(xml_directory, json_directory, pdf_directory)