import os
import json
import re
import requests
import httpx
from datetime import datetime
from xml.etree import ElementTree
from urllib.parse import quote
from dotenv import load_dotenv
from typing import List, Dict
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# --------------------------------------------------------------------------
# Konfiguration & globale Variablen
# --------------------------------------------------------------------------
load_dotenv()

UNPAYWALL_API = "https://api.unpaywall.org/v2/"
UNPAYWALL_EMAIL = "tempEMail@hessianTest.com"

# Summen für Statistik
arxiv_sum = 0
pubmed_sum = 0
unpaywall_sum = 0

# --------------------------------------------------------------------------
# Hilfsfunktionen
# --------------------------------------------------------------------------
def create_dir(directory: str):
    """Erzeugt Ordner, falls nicht vorhanden."""
    os.makedirs(directory, exist_ok=True)

def load_json(file_path: str) -> Dict:
    """JSON laden."""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_json(data: Dict, file_path: str):
    """JSON speichern."""
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)

def parse_year(date_str: str) -> int:
    """Extrahiert das Jahr aus einem beliebigen String (z.B. '2021-05-10')."""
    match = re.search(r'\b(\d{4})\b', date_str)
    return int(match.group(1)) if match else 0

def sanitize_filename(title: str, max_length: int = 50) -> str:
    """
    Bereinigt einen Titel für die Verwendung als Dateiname:
    - Alles zu Kleinbuchstaben
    - Ersetzt unerwünschte Zeichen (inkl. ', ", {, }, etc.) durch Unterstriche
    - Kürzt auf die maximal zulässige Länge
    """
    sanitized = title.lower()
    # Ersetze alles außer a-z, 0-9, ., -, _ durch "_"
    sanitized = re.sub(r'[^a-z0-9._-]', '_', sanitized)
    # Mehrere Unterstriche hintereinander zu einem machen
    sanitized = re.sub(r'_+', '_', sanitized)
    # Auf max_length kürzen und ggf. trailing underscores entfernen
    sanitized = sanitized[:max_length].strip('_')
    return sanitized

def generate_unique_filename(folder: str, filename: str, extension: str) -> str:
    """
    Prüft, ob ein Dateiname bereits existiert, und fügt bei Bedarf einen Zähler hinzu.
    """
    base_filename = filename
    counter = 1
    new_path = os.path.join(folder, f"{filename}{extension}")
    while os.path.exists(new_path):
        filename = f"{base_filename}_{counter}"
        counter += 1
        new_path = os.path.join(folder, f"{filename}{extension}")
    return new_path

def is_similar(abstract: str, existing_abstracts: List[str], threshold: float = 0.9) -> bool:
    """Checkt via TF-IDF, ob ein Abstract >= threshold Ähnlichkeit aufweist."""
    if not abstract or not existing_abstracts:
        return False
    all_texts = existing_abstracts + [abstract]
    tfidf = TfidfVectorizer().fit_transform(all_texts)
    sim_matrix = cosine_similarity(tfidf[-1], tfidf[:-1])
    return any(s >= threshold for s in sim_matrix[0])

# --------------------------------------------------------------------------
# Teil 1: ArXiv-Code
# --------------------------------------------------------------------------
def fetch_papers_arxiv(author: str, max_results: int = 200):
    """
    Ruft die ArXiv-API auf, lädt das gesamte XML (AtomFeed) herunter,
    speichert die XML-Datei unter xmls/arxiv/{autor_sanitized},
    filtert dann alle Einträge < 2020 raus und lädt alle gefundenen
    PDFs in pdfs/arxiv/{autor_sanitized}.
    """
    global arxiv_sum

    query_author = author.strip()
    sanitized_author = sanitize_filename(author)

    # Ordner: XML + PDFs
    xml_folder = os.path.join("xmls", "arxiv", sanitized_author)
    pdfs_folder = os.path.join("pdfs", "arxiv", sanitized_author)
    create_dir(xml_folder)
    create_dir(pdfs_folder)

    url = (
        "http://export.arxiv.org/api/query"
        f"?search_query=au:\"{query_author}\""
        f"&start=0&max_results={max_results}"
    )
    print(f"\n[ArXiv] Suche für Autor: {author}\n  -> {url}")

    with httpx.Client() as client:
        response = client.get(url)

    if response.status_code == 200:
        # XML speichern
        xml_filename = f"papers_{sanitized_author}.xml"
        xml_path = os.path.join(xml_folder, xml_filename)
        with open(xml_path, "w", encoding="utf-8") as xf:
            xf.write(response.text)
        print(f"[ArXiv] XML gespeichert: {xml_path}")

        # XML parsen
        tree = ElementTree.ElementTree(ElementTree.fromstring(response.text))
        root = tree.getroot()
        ns = {'atom': 'http://www.w3.org/2005/Atom'}

        downloaded_count = 0

        for entry in root.findall('atom:entry', ns):
            published_str = entry.find('atom:published', ns)
            if published_str is not None:
                pub_date = datetime.strptime(published_str.text, "%Y-%m-%dT%H:%M:%SZ")
                if pub_date.year < 2020:
                    continue

            pdf_link = entry.find("atom:link[@title='pdf']", ns)
            if pdf_link is not None:
                pdf_url = pdf_link.attrib['href']
                # PDF herunterladen
                try:
                    with httpx.Client() as pdf_client:
                        pdf_resp = pdf_client.get(pdf_url)
                    if pdf_resp.status_code == 200:
                        title = entry.find('atom:title', ns).text or "arxiv_paper"
                        safe_title = sanitize_filename(title)
                        pdf_out = generate_unique_filename(pdfs_folder, safe_title, ".pdf")
                        with open(pdf_out, "wb") as pf:
                            pf.write(pdf_resp.content)
                        downloaded_count += 1
                        # print(f"[ArXiv] PDF gespeichert: {pdf_out}")
                except Exception as e:
                    print(f"[ArXiv] Fehler beim PDF-Download {pdf_url}: {e}")
        arxiv_sum += downloaded_count
        print(f"[ArXiv] {downloaded_count} PDFs (>=2020) für {author} gespeichert.")
    else:
        print(f"[ArXiv] Fehler: HTTP {response.status_code}")

# --------------------------------------------------------------------------
# Teil 2: PubMed + Unpaywall
# --------------------------------------------------------------------------
def query_pubmed(name: str) -> List[str]:
    """Sucht nach PubMed IDs (post-Filtern wir auf Jahr >= 2020)."""
    global pubmed_sum
    print(f"[PubMed] Suche für: {name}")
    url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term={quote(name)}&retmode=json"
    try:
        resp = requests.get(url, timeout=15)
        if resp.status_code == 200:
            ids = resp.json().get("esearchresult", {}).get("idlist", [])
            if ids:
                pubmed_sum += 1
            return ids
        else:
            print("[PubMed] API error:", resp.text)
            return []
    except Exception as e:
        print("[PubMed] Fehler:", e)
        return []

def query_pubmed_details(paper_id: str) -> Dict:
    """Holt JSON-Details zu einem Paper (PubMed), checkt Jahr >=2020."""
    url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pubmed&id={paper_id}&retmode=json"
    try:
        r = requests.get(url, timeout=15)
        if r.status_code == 200:
            data = r.json().get("result", {}).get(paper_id, {})
            y = parse_year(data.get("pubdate", "0"))
            if y >= 2020:
                return {
                    "source": "pubmed",
                    "id": paper_id,
                    "title": data.get("title", ""),
                    "pubdate": data.get("pubdate", ""),
                    "doi": data.get("elocationid", ""),  # kann PubMed-DOI sein
                }
        else:
            print("[PubMed] details error:", r.text)
    except Exception as e:
        print("[PubMed] details error:", e)
    return {}

def query_unpaywall(doi: str, output_dir: str) -> str:
    """Sucht nach PDF-URL via Unpaywall (falls 'best_oa_location' existiert)."""
    global unpaywall_sum
    if not doi:
        return ""
    print(f"[Unpaywall] Checking for PDF (DOI={doi})")
    try:
        up_url = f"{UNPAYWALL_API}{doi}?email={UNPAYWALL_EMAIL}"
        resp = requests.get(up_url, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            pdf_url = data.get("best_oa_location", {}).get("url_for_pdf", "")
            if pdf_url:
                unpaywall_sum += 1
                # JSON speichern
                up_json_dir = os.path.join(output_dir, "unpaywall_json")
                create_dir(up_json_dir)
                json_path = os.path.join(up_json_dir, f"{sanitize_filename(doi)}.json")
                save_json(data, json_path)
                # print(f"[Unpaywall] JSON saved: {json_path}")
            return pdf_url
    except Exception as e:
        print("[Unpaywall] error:", e)
    return ""

def download_pdf(pdf_url: str, output_dir: str, title: str):
    """Lädt PDF-Datei runter (kein Jahres-Präfix)."""
    if not pdf_url:
        return
    safe_title = sanitize_filename(title if title else "paper")
    pdf_path = generate_unique_filename(output_dir, safe_title, ".pdf")

    try:
        r = requests.get(pdf_url, stream=True, timeout=20)
        if r.status_code == 200 and "application/pdf" in r.headers.get("Content-Type", ""):
            with open(pdf_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=1024):
                    f.write(chunk)
            # print("[Download] PDF gespeichert:", pdf_path)
        else:
            print(f"[Download] Kein PDF: {pdf_url}")
    except Exception as e:
        print("[Download] Fehler:", e)

def search_and_download_pubmed_unpaywall(author: str):
    """
    Sucht PubMed nach IDs, holt die Paper-Details (>=2020), versucht PDF via Unpaywall zu kriegen.
    Speichert PDFs in pdfs/pubmed_unpaywall/{author_sanitized}/...
    """
    sanitized_author = sanitize_filename(author)
    outdir = os.path.join("pdfs", "pubmed_unpaywall", sanitized_author)
    create_dir(outdir)

    # 1) IDs von PubMed
    ids = query_pubmed(author)
    # 2) Hole Details
    papers = []
    for pid in ids:
        p = query_pubmed_details(pid)
        if p:  # Jahr >=2020
            papers.append(p)

    # 3) Speichere JSON
    json_file = os.path.join(outdir, f"combined_results_{sanitized_author}.json")
    save_json(papers, json_file)

    # 4) Für jedes Paper -> PDF via Unpaywall
    for paper in papers:
        doi = paper.get("doi", "")
        title = paper.get("title", f"paper_{paper.get('id','')}")
        pdf_url = query_unpaywall(doi, outdir)
        if pdf_url:
            download_pdf(pdf_url, outdir, title)
        else:
            pass
            # print("[Info] No PDF found for:", title)

# --------------------------------------------------------------------------
# Hauptprogramm
# --------------------------------------------------------------------------
def main():
    authors_dict = load_json("authors.json")

    for group_name, author_list in authors_dict.items():
        print(f"\n--- Starte Verarbeitung für Gruppe: {group_name} ---")
        for author in author_list:
            # 1) ArXiv
            fetch_papers_arxiv(author, max_results=200)

            # 2) PubMed + Unpaywall
            search_and_download_pubmed_unpaywall(author)

    print("\nSkript beendet. Statistiken:")
    print(f"  arxiv_sum      = {arxiv_sum}")
    print(f"  pubmed_sum     = {pubmed_sum}")
    print(f"  unpaywall_sum  = {unpaywall_sum}")

if __name__ == "__main__":
    main()
