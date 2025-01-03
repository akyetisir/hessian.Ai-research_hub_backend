import os
import httpx
import json
from xml.etree import ElementTree
from datetime import datetime


with open("authors.json", "r", encoding="utf-8") as f:
    authors_dict = json.load(f)



def fetch_papers(author: str, max_results: int = 100):
    """
    Ruft die ArXiv-API auf, lädt das gesamte XML (AtomFeed) herunter,
    speichert die XML-Datei, filtert dann alle Einträge < 2020 raus
    und lädt alle gefundenen PDFs in den jeweiligen Unterordner im
    Verzeichnis 'pdfs/' (z.B. pdfs/stefan_roth).
    """

    # Query sollte im Format "Vorname Nachname" in Anführungszeichen stehen.
    # z.B. author = "Stefan Roth" -> "Stefan Roth"
    query_author = author.strip()  # In diesem Fall ist 'Vorname Nachname' bereits als String

    # URL für die arXiv-API: Suche nur nach Autor in Anführungszeichen
    url = (
        "http://export.arxiv.org/api/query"
        f"?search_query=au:\"{query_author}\""
        f"&start=0&max_results={max_results}"
    )

    print(f"\nStarte ArXiv-Suche für Autor: {author}\n  -> Query: {url}")

    with httpx.Client() as client:
        response = client.get(url)

    if response.status_code == 200:
        # Ordner für XMLs anlegen (falls nicht vorhanden)
        xml_folder = "xmls"
        if not os.path.exists(xml_folder):
            os.mkdir(xml_folder)

        # Unterordner für die PDFs des jeweiligen Autors erstellen,
        # z.B. /pdfs/stefan_roth
        pdfs_root_folder = "pdfs"
        if not os.path.exists(pdfs_root_folder):
            os.mkdir(pdfs_root_folder)

        author_folder_name = author.lower().replace(" ", "_")
        author_pdf_folder = os.path.join(pdfs_root_folder, author_folder_name)
        if not os.path.exists(author_pdf_folder):
            os.mkdir(author_pdf_folder)

        # XML-Datei ablegen (un-gefiltert, gesamter Feed)
        xml_filename = f"{xml_folder}/papers_{author.replace(' ', '_')}.xml"
        with open(xml_filename, "w", encoding="utf-8") as file:
            file.write(response.text)
        print(f"XML-Datei erfolgreich gespeichert: {xml_filename}")

        # Nun parsen wir das XML und filtern nach Publikationsdatum >= 2020
        tree = ElementTree.ElementTree(ElementTree.fromstring(response.text))
        root = tree.getroot()

        # Namespace definieren, damit wir 'find' und 'findall' korrekt nutzen können
        namespaces = {'atom': 'http://www.w3.org/2005/Atom'}

        downloaded_pdfs = []

        # Durch alle <entry>-Knoten loopen
        for entry in root.findall('atom:entry', namespaces):
            # Veröffentlichungsdatum parsen -> <published>
            published_str = entry.find('atom:published', namespaces)
            if published_str is not None:
                published_date = datetime.strptime(published_str.text, "%Y-%m-%dT%H:%M:%SZ")
                if published_date.year < 2020:
                    # Falls vor 2020 -> Überspringen
                    continue

            # PDF-Link ermitteln (<link title="pdf">)
            pdf_link = entry.find("atom:link[@title='pdf']", namespaces)
            if pdf_link is not None:
                pdf_url = pdf_link.attrib['href']

                # PDF herunterladen
                try:
                    with httpx.Client() as pdf_client:
                        pdf_response = pdf_client.get(pdf_url)

                    if pdf_response.status_code == 200:
                        # Titel für den PDF-Dateinamen extrahieren
                        title = entry.find('atom:title', namespaces).text
                        # ungültige Zeichen ersetzen
                        safe_title = title[:50].replace('/', '_').replace(' ', '_')
                        pdf_filename = os.path.join(author_pdf_folder, f"{safe_title}.pdf")

                        # PDF speichern
                        with open(pdf_filename, "wb") as pdf_file:
                            pdf_file.write(pdf_response.content)

                        downloaded_pdfs.append(pdf_filename)
                        print(f"PDF gespeichert: {pdf_filename}")
                except Exception as e:
                    print(f"Fehler beim Download der PDF ({pdf_url}): {e}")

        print(f"Alle (seit 2020) verfügbaren PDFs wurden heruntergeladen für {author}.")
        return downloaded_pdfs

    else:
        print(f"Fehler: Status Code: {response.status_code}")
        print(f"Antwort Text: {response.text}")
        return []


# Hauptteil des Skripts: Für jede Gruppe in authors_dict jeden Autor verarbeiten.
if __name__ == "__main__":
    all_downloaded_pdfs = []

    for group_name, author_list in authors_dict.items():
        print(f"\n--- Starte Verarbeitung für Gruppe: {group_name} ---")
        for author in author_list:
            downloaded_pdfs = fetch_papers(author, max_results=50)
            all_downloaded_pdfs.extend(downloaded_pdfs)

    print("\nSkript beendet. Alle gefundenen PDFs liegen in den jeweiligen Unterordnern unter 'pdfs/'.")
