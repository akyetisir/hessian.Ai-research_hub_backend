import xml.etree.ElementTree as ET
from pymongo import MongoClient
import requests
from dotenv import load_dotenv
import os
import fitz  # PyMuPDF

load_dotenv()

uri = os.getenv("MongoDB-uri")

def extract_metadata_from_xml(xml_file):
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

            # Filterung nach Veröffentlichungsdatum ab 2020
            if published_date and int(published_date.split("-")[0]) >= 2020:
                paper = {
                    "titel": entry.find("title", namespaces=namespaces).text,
                    "authors": [author.find("name", namespaces=namespaces).text for author in entry.findall("author", namespaces=namespaces)],
                    "published": published_date,
                    "abstract": entry.find("summary", namespaces=namespaces).text if entry.find("summary", namespaces=namespaces) is not None else None,
                    "citations": int(entry.find("citations", namespaces=namespaces).text) if entry.find("citations", namespaces=namespaces) is not None else 0,
                    "relevance": 0, 
                    "pdf": None,
                    "picture": "default_image_url.jpg",
                    "content": None,
                    "doi": entry.find("doi", namespaces=namespaces).text if entry.find("doi", namespaces=namespaces) else None,
                    "journal": entry.find("journal", namespaces=namespaces).text if entry.find("journal", namespaces=namespaces) else None,
                    "platforms": ["arXiv"],
                    "views": 0
                }

                # PDF Link finden
                pdf_link = entry.find("link[@title='pdf']", namespaces=namespaces)
                if pdf_link is not None:
                    paper["pdf"] = pdf_link.attrib['href']

                papers.append(paper)
        except Exception as e:
            print(f"Fehler beim Verarbeiten eines Eintrags in {xml_file}: {e}")

    return papers

def extract_pdf_content(pdf_url):
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
        print(f"Fehler beim Öffnen der PDF-Datei: {e}")
        return None

def save_to_mongodb(papers):
    client = MongoClient(uri)
    db = client["researchhub"]
    collection = db["papers"]

    for paper in papers:
        if paper["pdf"]:
            content = extract_pdf_content(paper["pdf"])
            if content:
                paper["content"] = content
                del paper["pdf"]
            else:
                print(f"Fehler beim Speichern des Inhalts für das Paper {paper['titel']}")
                paper["pdf"] = None
                paper["content"] = None

        try:
            collection.insert_one(paper)
            print(f"Paper '{paper['titel']}' erfolgreich gespeichert.")
        except Exception as e:
            print(f"Fehler beim Speichern des Papers '{paper['titel']}': {e}")

def process_all_xml_files(xml_directory):
    for root, _, files in os.walk(xml_directory):
        for file in files:
            if file.endswith(".xml"):
                xml_path = os.path.join(root, file)
                papers = extract_metadata_from_xml(xml_path)
                print(f"Extracted Metadata from {file}: {papers}")
                save_to_mongodb(papers)

if __name__ == "__main__":
    xml_directory = "/Users/yusuf/VSCodeProjects/hessian.Ai-research_hub_backend/xmls"
    process_all_xml_files(xml_directory)




       