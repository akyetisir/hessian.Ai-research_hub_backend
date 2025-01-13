"""import xml.etree.ElementTree as ET
from pymongo import MongoClient
from pymongo.errors import PyMongoError
import requests
from dotenv import load_dotenv
import os
import fitz  # PyMuPDF

load_dotenv()

uri = os.getenv("MongoDB-uri")

def extract_metadata_from_xml(xml_file, pdf_directory):
    
    #Liest eine XML-Datei ein, filtert Einträge ab dem Jahr 2020,
    #sucht zugehörige PDF-Dateien im pdf_directory und gibt eine Liste
    #von Paper-Dictionaries zurück.
    
    try:
        tree = ET.parse(xml_file)
        root = tree.getroot()
    except ET.ParseError as e:
        print(f"Fehler beim Parsen der XML-Datei {xml_file}: {e}")
        return []

    # Alle Namespace-Infos sammeln (falls vorhanden)
    namespaces = {prefix: uri for event, (prefix, uri) in ET.iterparse(xml_file, events=['start-ns'])}

    papers = []
    for entry in root.findall(".//entry", namespaces=namespaces):
        try:
            published_date = None
            published_elem = entry.find("published", namespaces=namespaces)
            if published_elem is not None and published_elem.text:
                published_date = published_elem.text

            # Filter: nur Papers ab 2020
            if published_date and int(published_date.split("-")[0]) >= 2020:
                # Basis-Infos
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
                    "picture": "default_image_url.jpg",
                    "content": None,
                    "doi": entry.find("doi", namespaces=namespaces).text if entry.find("doi", namespaces=namespaces) else None,
                    "journal": entry.find("journal", namespaces=namespaces).text if entry.find("journal", namespaces=namespaces) else None,
                    "platforms": ["arXiv"],
                    "views": 0,
                    "path": None  # Relativer Pfad zur PDF im Projektordner
                }

                # PDF-Link aus XML
                pdf_link = entry.find("link[@title='pdf']", namespaces=namespaces)
                if pdf_link is not None:
                    paper["pdf"] = pdf_link.attrib.get('href', None)

                    # Versuche die lokale PDF-Datei zu finden
                    title_raw = paper["title"] or ""
                    title_norm = title_raw.lower().replace(" ", "_").replace(":", "_").replace(",", "_")
                    title_snippet = title_norm[:20]  # Vergleiche die ersten 20 Zeichen

                    found_file = None
                    for root_dir, _, files in os.walk(pdf_directory):
                        for file in files:
                            file_norm = file.lower().replace(" ", "_").replace(":", "_").replace(",", "_")
                            if title_snippet in file_norm:
                                absolute_path = os.path.join(root_dir, file)
                                relative_path = os.path.relpath(absolute_path, pdf_directory)
                                paper["path"] = os.path.join("pdfs", relative_path)
                                found_file = file
                                break
                        if paper["path"]:
                            break

                    if not found_file:
                        print(f"[DEBUG] Keine passende PDF-Datei gefunden für '{title_raw}' in {pdf_directory}")
                
                # Paper in die Liste
                papers.append(paper)

        except Exception as e:
            print(f"Fehler beim Verarbeiten eines Eintrags in {xml_file}: {e}")

    return papers

def extract_pdf_content(pdf_url):
    
    #Lädt eine PDF von pdf_url und extrahiert ihren Textinhalt via PyMuPDF.
    
    try:
        response = requests.get(pdf_url)
        response.raise_for_status()
        pdf_content = response.content

        # PDF-Text extrahieren
        pdf_text = ""
        with fitz.open(stream=pdf_content, filetype="pdf") as doc:
            for page in doc:
                pdf_text += page.get_text()

        return pdf_text

    except requests.exceptions.RequestException as e:
        print(f"Fehler beim Abrufen der PDF: {e}")
        return None
    except Exception as e:
        print(f"Fehler beim Öffnen/Verarbeiten der PDF-Datei: {e}")
        return None

def save_to_mongodb(papers):
    
    #Speichert eine Liste von Papern in MongoDB.
    
    client = MongoClient(uri)
    db = client["researchhub"]
    collection = db["papers"]

    for paper in papers:
        # Wenn ein PDF-Link existiert, versuche, den PDF-Text zu extrahieren
        if paper["pdf"]:
            content = extract_pdf_content(paper["pdf"])
            if content:
                paper["content"] = content
            else:
                print(f"Fehler beim Speichern des Inhalts für das Paper '{paper['title']}'")
                paper["pdf"] = None
                paper["content"] = None

        try:
            collection.insert_one(paper)
            print(f"Paper '{paper['title']}' erfolgreich gespeichert (path={paper['path']}).")
        except PyMongoError as e:
            print(f"Fehler beim Speichern des Papers '{paper['title']}': {e}")

def process_all_xml_files(xml_directory, pdf_directory):
    
    #Durchläuft alle .xml-Dateien im xml_directory, extrahiert Paper-Metadaten 
    #und speichert sie in MongoDB.
    
    for root_dir, _, files in os.walk(xml_directory):
        for file in files:
            if file.endswith(".xml"):
                xml_path = os.path.join(root_dir, file)
                papers = extract_metadata_from_xml(xml_path, pdf_directory)
                print(f"[DEBUG] Extracted {len(papers)} papers from {file}")
                save_to_mongodb(papers)

if __name__ == "__main__":
    xml_directory = "/Users/yusuf/VSCodeProjects/hessian.Ai-research_hub_backend/xmls"
    pdf_directory = "/Users/yusuf/VSCodeProjects/hessian.Ai-research_hub_backend/pdfs"
    process_all_xml_files(xml_directory, pdf_directory) """

import xml.etree.ElementTree as ET
from pymongo import MongoClient
from pymongo.errors import PyMongoError
import requests
from dotenv import load_dotenv
import os
import fitz  # PyMuPDF

load_dotenv()

uri = os.getenv("MongoDB-uri")

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
                    "path": None
                }

                pdf_link = entry.find("link[@title='pdf']", namespaces=namespaces)
                if pdf_link is not None:
                    paper["pdf"] = pdf_link.attrib.get('href', None)

                    title_raw = paper["title"] or ""
                    title_norm = title_raw.lower().replace(" ", "_").replace(":", "_").replace(",", "_")
                    title_snippet = title_norm[:20]

                    found_file = None
                    for root_dir, _, files in os.walk(pdf_directory):
                        for file in files:
                            file_norm = file.lower().replace(" ", "_").replace(":", "_").replace(",", "_")
                            if title_snippet in file_norm:
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

def extract_pdf_content(pdf_url, paper):
    try:
        response = requests.get(pdf_url)
        response.raise_for_status()
        pdf_content = response.content

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

def save_to_mongodb(papers):
    client = MongoClient(uri)
    db = client["researchhub"]
    collection = db["papers"]  # Zurück zur richtigen Collection "papers"

    for paper in papers:
        if paper["pdf"]:
            content = extract_pdf_content(paper["pdf"], paper)
            if content:
                paper["content"] = content
            else:
                print(f"Fehler beim Speichern des Inhalts für das Paper '{paper['title']}'")
                paper["pdf"] = None
                paper["content"] = None

        try:
            existing_paper = collection.find_one({"title": paper["title"]})
            if existing_paper:
                update_fields = {k: v for k, v in paper.items() if k != "picture"}  # Entferne "picture"-Feld
                collection.update_one({"_id": existing_paper["_id"]}, {"$set": update_fields})
                print(f"Paper '{paper['title']}' erfolgreich aktualisiert (path={paper['path']}, path_image={paper['path_image']}).")
            else:
                collection.insert_one(paper)
                print(f"Paper '{paper['title']}' erfolgreich gespeichert (path={paper['path']}, path_image={paper['path_image']}).")
        except PyMongoError as e:
            print(f"Fehler beim Speichern des Papers '{paper['title']}']: {e}")

def process_all_xml_files(xml_directory, pdf_directory):
    for root_dir, _, files in os.walk(xml_directory):
        for file in files:
            if file.endswith(".xml"):
                xml_path = os.path.join(root_dir, file)
                papers = extract_metadata_from_xml(xml_path, pdf_directory)
                print(f"[DEBUG] Extracted {len(papers)} papers from {file}")
                save_to_mongodb(papers)

if __name__ == "__main__":
    xml_directory = "/Users/yusuf/VSCodeProjects/hessian.Ai-research_hub_backend/xmls"
    pdf_directory = "/Users/yusuf/VSCodeProjects/hessian.Ai-research_hub_backend/pdfs"
    process_all_xml_files(xml_directory, pdf_directory)
