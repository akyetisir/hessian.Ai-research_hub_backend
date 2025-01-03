import httpx
from xml.etree import ElementTree
import os

def fetch_papers(author: str, max_results: int = 15):
    # URL für die arXiv-API
    url = f'http://export.arxiv.org/api/query?search_query=all:{author}&start=0&max_results={max_results}'
    
    # HTTP-Anfrage mit httpx
    with httpx.Client() as client:
        response = client.get(url)

    # Überprüfe den Statuscode der Antwort
    if response.status_code == 200:
        xml_folder = "xmls"
        if not os.path.exists(xml_folder):  # Ordner erstellen, wenn er nicht existiert
            os.mkdir(xml_folder)

        if not os.path.exists("pdfs"):
            os.mkdir("pdfs")

        # Antwort erfolgreich, speichere die XML-Datei
        xml_filename = f"{xml_folder}/papers_{author}.xml"
        with open(xml_filename, "w", encoding="utf-8") as file:
            file.write(response.text)
        print(f"XML-Datei erfolgreich gespeichert: {xml_filename}")

        tree = ElementTree.ElementTree(ElementTree.fromstring(response.text))
        root = tree.getroot()

        downloaded_pdfs = []
        namespaces = {'atom': 'http://www.w3.org/2005/Atom'}
        for entry in root.findall('atom:entry', namespaces):
            pdf_link = entry.find("atom:link[@title='pdf']", namespaces)
            if pdf_link is not None:
                pdf_url = pdf_link.attrib['href']
                downloaded_pdfs.append(pdf_url)

                try:
                    # Sende eine GET-Anfrage, um die PDF-Datei herunterzuladen
                    with httpx.Client() as pdf_client:
                        pdf_response = pdf_client.get(pdf_url)

                    if pdf_response.status_code == 200:
                        # Extrahiere den Titel oder eine eindeutige ID aus dem XML (z.B. den Titel des Artikels)
                        title = entry.find('atom:title', namespaces).text
                        # Verwende den Titel als Dateinamen (ersetze ungültige Zeichen)
                        pdf_filename = f"pdfs/{title[:50].replace('/', '_').replace(' ', '_')}.pdf"
                        # Speichern der PDF
                        with open(pdf_filename, "wb") as pdf_file:
                            pdf_file.write(pdf_response.content)
                        print(f"PDF erfolgreich gespeichert: {pdf_filename}")

                except Exception as e:
                    print(f"Fehler beim Herunterladen der PDF ({pdf_url}): {e}")

        print("Alle verfügbaren PDFs wurden heruntergeladen.")
        return downloaded_pdfs
    else:
        # Gebe detaillierte Fehlermeldung aus
        print(f"Fehler: Status Code: {response.status_code}")
        print(f"Antwort Text: {response.text}")
        return []

# Beispielaufruf
author_name = "Stefan Roth"
max_results = 20
downloaded_pdfs = fetch_papers(author_name, max_results)
print(f"Heruntergeladene PDFs: {downloaded_pdfs}")
