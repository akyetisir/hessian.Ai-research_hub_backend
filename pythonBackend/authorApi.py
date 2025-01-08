# import os
# import json
# import requests
# from typing import List, Dict
# from urllib.parse import quote
# from dotenv import load_dotenv
# import re
# from sklearn.feature_extraction.text import TfidfVectorizer
# from sklearn.metrics.pairwise import cosine_similarity

# load_dotenv()

# ieee_sum = orcid_sum = pubmed_sum = zenodo_sum = pubmed_central_sum = unpaywall_sum = 0

# # Constants
# UNPAYWALL_API = "https://api.unpaywall.org/v2/"
# PUBMED_CENTRAL_API = "https://www.ncbi.nlm.nih.gov/pmc/utils/idconv/v1.0/"
# IEEE_API_KEY = os.getenv("IEEE-API-KEY")
# UNPAYWALL_EMAIL = "tempEMail@hessianTest.com"

# def create_dir(directory: str):
#     """Ensure the directory exists."""
#     os.makedirs(directory, exist_ok=True)

# def load_json(file_path: str) -> Dict:
#     """Load JSON data from a file."""
#     with open(file_path, 'r', encoding='utf-8') as f:
#         return json.load(f)

# def save_results(results: List[Dict], output_file: str):
#     """Save results to a JSON file."""
#     with open(output_file, 'w', encoding='utf-8') as f:
#         json.dump(results, f, indent=2)

# def parse_year(date_str: str) -> int:
#     """Extract the year from a date string."""
#     match = re.search(r'\b(\d{4})\b', date_str)
#     return int(match.group(1)) if match else 0

# def sanitize_title(title: str) -> str:
#     """Sanitize the title for use in filenames."""
#     return re.sub(r'[^a-zA-Z0-9_\-]', '_', title)[:50]

# def is_similar(abstract: str, existing_abstracts: List[str], threshold: float = 0.9) -> bool:
#     """Check if the abstract is similar to any in the existing abstracts."""
#     if not abstract or not existing_abstracts:
#         return False
#     all_texts = existing_abstracts + [abstract]
#     tfidf_vectorizer = TfidfVectorizer().fit_transform(all_texts)
#     similarity_matrix = cosine_similarity(tfidf_vectorizer[-1], tfidf_vectorizer[:-1])
#     return any(sim >= threshold for sim in similarity_matrix[0])

# # Queries
# def query_ieee(name: str) -> List[Dict]:
#     """Query IEEE API for papers."""
#     print("Querying IEEE...")
#     url = f"https://ieeexploreapi.ieee.org/api/v1/search/articles?author={quote(name)}&apikey={IEEE_API_KEY}"
#     try:
#         response = requests.get(url, timeout=10)
#         if response.status_code != 200:
#             print(f"IEEE API error: {response.text}")
#             return []
#         articles = response.json().get('articles', [])
#         filtered_articles = [
#             article for article in articles
#             if parse_year(article.get('publication_year', '0')) >= 2020 and name in article.get('authors', '')
#         ]
#         if filtered_articles:
#             print("Got a hit from IEEE!")
#             global ieee_sum
#             ieee_sum+=1
#         return filtered_articles
#     except Exception as e:
#         print(f"Error querying IEEE: {e}")
#         return []

# def query_orcid(name: str) -> List[Dict]:
#     """Query ORCID API for papers."""
#     print("Querying ORCID...")
#     url = f"https://pub.orcid.org/v3.0/search/?q=author:{quote(name)}"
#     try:
#         response = requests.get(url, headers={"Accept": "application/json"}, timeout=10)
#         results = response.json().get("results", [])
#         filtered_results = [
#             result for result in results
#             if parse_year(result.get('bibjson', {}).get('year', '0')) >= 2020 and name in result.get('title', '')
#         ]
#         if filtered_results:
#             print("Got a hit from ORCID!")
#             global orcid_sum_sum
#             orcid_sum+=1
#         return filtered_results
#     except Exception as e:
#         print(f"Error querying ORCID: {e}")
#         return []

# def query_pubmed(name: str) -> List[str]:
#     """Query PubMed for paper IDs."""
#     print("Querying PubMed...")
#     url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term={quote(name)}&retmode=json"
#     try:
#         response = requests.get(url, timeout=10)
#         ids = response.json().get("esearchresult", {}).get("idlist", [])
#         if ids:
#             print("Got a hit from PubMed!")
#             global pubmed_sum
#             pubmed_sum+=1
#         return ids
#     except Exception as e:
#         print(f"Error querying PubMed: {e}")
#         return []

# def query_pubmed_details(paper_id: str) -> Dict:
#     """Query PubMed for paper details."""
#     url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pubmed&id={paper_id}&retmode=json"
#     try:
#         response = requests.get(url, timeout=10)
#         paper = response.json().get("result", {}).get(paper_id, {})
#         if parse_year(paper.get('pubdate', '0')) >= 2020:
#             return paper
#     except Exception as e:
#         print(f"Error querying PubMed details: {e}")
#     return {}

# def query_zenodo(name: str) -> List[Dict]:
#     """Query Zenodo for papers."""
#     print("Querying Zenodo...")
#     url = f"https://zenodo.org/api/records/?q=authors.name:{quote(name)}"
#     try:
#         response = requests.get(url, timeout=10)
#         results = response.json().get("hits", {}).get("hits", [])
#         filtered_results = [
#             result for result in results
#             if parse_year(result.get('created', '1970-01-01').split('-')[0]) >= 2020 and name in result.get('metadata', {}).get('title', '')
#         ]
#         if filtered_results:
#             print("Got a hit from Zenodo!")
#             global zenodo_sum
#             zenodo_sum+=1
#         return filtered_results
#     except Exception as e:
#         print(f"Error querying Zenodo: {e}")
#         return []

# def query_unpaywall(doi: str) -> str:
#     """Query Unpaywall API for an open-access PDF URL."""
#     if not doi:
#         return ""
#     print("Querying Unpaywall...")
#     try:
#         response = requests.get(f"{UNPAYWALL_API}{doi}?email={UNPAYWALL_EMAIL}", timeout=10)
#         if response.status_code == 200:
#             pdf_url = response.json().get("best_oa_location", {}).get("url_for_pdf", "")
#             if pdf_url:
#                 print("Got a hit from Unpaywall!")
#                 global unpaywall_sum
#                 unpaywall_sum+=1
#             return pdf_url
#     except Exception as e:
#         print(f"Error querying Unpaywall: {e}")
#     return ""

# def query_pubmed_central(doi: str) -> str:
#     """Query PubMed Central API for a PDF URL."""
#     if not doi:
#         return ""
#     print("Querying PubMed Central...")
#     url = f"{PUBMED_CENTRAL_API}?ids={doi}&format=json"
#     try:
#         response = requests.get(url, timeout=10)
#         if response.status_code == 200:
#             pmcid = response.json().get("records", [{}])[0].get("pmcid")
#             if pmcid:
#                 print("Got a hit from PubMed Central!")
#                 global pubmed_central_sum
#                 pubmed_central_sum+=1
#                 return f"https://www.ncbi.nlm.nih.gov/pmc/articles/{pmcid}/pdf/"
#     except Exception as e:
#         print(f"Error querying PubMed Central: {e}")
#     return ""

# def download_pdf(url: str, output_dir: str, title: str, pub_date: str):
#     """Download a PDF file."""
#     if not url:
#         return
#     date_prefix = pub_date.split(' ')[0].replace('-', '') if pub_date else "unknown"
#     filename = f"{date_prefix}_{sanitize_title(title)}.pdf"
#     filepath = os.path.join(output_dir, filename)
#     try:
#         response = requests.get(url, stream=True, timeout=10)
#         if response.status_code == 200 and "application/pdf" in response.headers.get("Content-Type", ""):
#             with open(filepath, 'wb') as f:
#                 for chunk in response.iter_content(chunk_size=1024):
#                     f.write(chunk)
#             print(f"Downloaded: {filepath}")
#         else:
#             print(f"Failed to download PDF from {url}")
#     except Exception as e:
#         print(f"Error downloading PDF: {e}")

# def search_and_download(name: str, output_dir: str):
#     """Search for papers, extract PDF links, and download PDFs."""
#     all_papers = []
#     existing_abstracts = []

#     # API Calls
#     print(f"Searching papers for: {name}")
#     ieee_papers = query_ieee(name)
#     orcid_papers = query_orcid(name)
#     pubmed_ids = query_pubmed(name)
#     zenodo_papers = query_zenodo(name)

#     pubmed_papers = [query_pubmed_details(pid) for pid in pubmed_ids]

#     # Combine and Filter Results
#     candidate_papers = ieee_papers + orcid_papers + pubmed_papers + zenodo_papers
#     for paper in candidate_papers:
#         abstract = paper.get("abstract", "").strip()
#         if not is_similar(abstract, existing_abstracts):
#             all_papers.append(paper)
#             if abstract:
#                 existing_abstracts.append(abstract)

#     save_results(all_papers, "combined_results.json")
#     print("Saved all results to combined_results.json")

#     print("ieee_sum =",ieee_sum)
#     print("orcid_sum =",orcid_sum)
#     print("pubmed_sum =",pubmed_sum)
#     print("zenodo_sum =",zenodo_sum)
#     print("pubmed_central_sum =",pubmed_central_sum)
#     print("unpaywall_sum=",unpaywall_sum)

#     # Download PDFs
#     create_dir(output_dir)
#     for paper in all_papers:
#         doi = paper.get("doi") or paper.get("elocationid")
#         pdf_url = query_unpaywall(doi) or query_pubmed_central(doi)
#         if pdf_url:
#             title = paper.get("title", f"paper_{paper.get('id', '')}")
#             pub_date = paper.get("pubdate", "unknown")
#             download_pdf(pdf_url, output_dir, title, pub_date)
#         else:
#             print(f"No PDF found for {paper.get('title', 'unknown_title')}")

# def main():
#     data = load_json("authors.json")
#     output_dir = "pdfs"
#     for group, names in data.items():
#         for name in names:
#             os.makedirs(f"pdfs\{name}", exist_ok=True)
#             search_and_download(name, f"pdfs\{name}")

# if __name__ == "__main__":
#     main()

import os
import json
import requests
from typing import List, Dict
from urllib.parse import quote
from dotenv import load_dotenv
import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

load_dotenv()

ieee_sum = orcid_sum = pubmed_sum = zenodo_sum = pubmed_central_sum = unpaywall_sum = 0

# Constants
UNPAYWALL_API = "https://api.unpaywall.org/v2/"
PUBMED_CENTRAL_API = "https://www.ncbi.nlm.nih.gov/pmc/utils/idconv/v1.0/"
IEEE_API_KEY = os.getenv("IEEE-API-KEY")
UNPAYWALL_EMAIL = "tempEMail@hessianTest.com"

def create_dir(directory: str):
    """Ensure the directory exists."""
    os.makedirs(directory, exist_ok=True)

def load_json(file_path: str) -> Dict:
    """Load JSON data from a file."""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_results(results: List[Dict], output_file: str):
    """Save results to a JSON file."""
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2)

def save_json(data: Dict, file_path: str):
    """Save JSON data to a file."""
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)

def parse_year(date_str: str) -> int:
    """Extract the year from a date string."""
    match = re.search(r'\b(\d{4})\b', date_str)
    return int(match.group(1)) if match else 0

def sanitize_title(title: str) -> str:
    """Sanitize the title for use in filenames."""
    return re.sub(r'[^a-zA-Z0-9_\-]', '_', title)[:50]

def is_similar(abstract: str, existing_abstracts: List[str], threshold: float = 0.9) -> bool:
    """Check if the abstract is similar to any in the existing abstracts."""
    if not abstract or not existing_abstracts:
        return False
    all_texts = existing_abstracts + [abstract]
    tfidf_vectorizer = TfidfVectorizer().fit_transform(all_texts)
    similarity_matrix = cosine_similarity(tfidf_vectorizer[-1], tfidf_vectorizer[:-1])
    return any(sim >= threshold for sim in similarity_matrix[0])

# Queries
def query_ieee(name: str) -> List[Dict]:
    """Query IEEE API for papers."""
    print("Querying IEEE...")
    url = f"https://ieeexploreapi.ieee.org/api/v1/search/articles?author={quote(name)}&apikey={IEEE_API_KEY}"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code != 200:
            print(f"IEEE API error: {response.text}")
            return []
        articles = response.json().get('articles', [])
        filtered_articles = [
            article for article in articles
            if parse_year(article.get('publication_year', '0')) >= 2020 and name in article.get('authors', '')
        ]
        if filtered_articles:
            print("Got a hit from IEEE!")
            global ieee_sum
            ieee_sum += 1
        return filtered_articles
    except Exception as e:
        print(f"Error querying IEEE: {e}")
        return []

def query_orcid(name: str) -> List[Dict]:
    """Query ORCID API for papers."""
    print("Querying ORCID...")
    url = f"https://pub.orcid.org/v3.0/search/?q=author:{quote(name)}"
    try:
        response = requests.get(url, headers={"Accept": "application/json"}, timeout=10)
        results = response.json().get("results", [])
        filtered_results = [
            result for result in results
            if parse_year(result.get('bibjson', {}).get('year', '0')) >= 2020 and name in result.get('title', '')
        ]
        if filtered_results:
            print("Got a hit from ORCID!")
            global orcid_sum
            orcid_sum += 1
        return filtered_results
    except Exception as e:
        print(f"Error querying ORCID: {e}")
        return []

def query_pubmed(name: str) -> List[str]:
    """Query PubMed for paper IDs."""
    print("Querying PubMed...")
    url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term={quote(name)}&retmode=json"
    try:
        response = requests.get(url, timeout=10)
        ids = response.json().get("esearchresult", {}).get("idlist", [])
        if ids:
            print("Got a hit from PubMed!")
            global pubmed_sum
            pubmed_sum += 1
        return ids
    except Exception as e:
        print(f"Error querying PubMed: {e}")
        return []

def query_pubmed_details(paper_id: str) -> Dict:
    """Query PubMed for paper details."""
    url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pubmed&id={paper_id}&retmode=json"
    try:
        response = requests.get(url, timeout=10)
        paper = response.json().get("result", {}).get(paper_id, {})
        if parse_year(paper.get('pubdate', '0')) >= 2020:
            return paper
    except Exception as e:
        print(f"Error querying PubMed details: {e}")
    return {}

def query_zenodo(name: str) -> List[Dict]:
    """Query Zenodo for papers."""
    print("Querying Zenodo...")
    url = f"https://zenodo.org/api/records/?q=authors.name:{quote(name)}"
    try:
        response = requests.get(url, timeout=10)
        results = response.json().get("hits", {}).get("hits", [])
        filtered_results = [
            result for result in results
            if parse_year(result.get('created', '1970-01-01').split('-')[0]) >= 2020 and name in result.get('metadata', {}).get('title', '')
        ]
        if filtered_results:
            print("Got a hit from Zenodo!")
            global zenodo_sum
            zenodo_sum += 1
        return filtered_results
    except Exception as e:
        print(f"Error querying Zenodo: {e}")
        return []

def query_unpaywall(doi: str, output_dir: str) -> str:
    """Query Unpaywall API for an open-access PDF URL and save JSON response."""
    if not doi:
        return ""
    print("Querying Unpaywall...")
    try:
        response = requests.get(f"{UNPAYWALL_API}{doi}?email={UNPAYWALL_EMAIL}", timeout=10)
        if response.status_code == 200:
            data = response.json()
            pdf_url = data.get("best_oa_location", {}).get("url_for_pdf", "")
            if pdf_url:
                print("Got a hit from Unpaywall!")
                global unpaywall_sum
                unpaywall_sum += 1

                # Save JSON response
                unpaywall_dir = os.path.join(output_dir, "unpaywall_json")
                create_dir(unpaywall_dir)
                sanitized_doi = sanitize_title(doi)
                json_path = os.path.join(unpaywall_dir, f"{sanitized_doi}.json")
                save_json(data, json_path)
                print(f"Saved Unpaywall JSON: {json_path}")

            return pdf_url
    except Exception as e:
        print(f"Error querying Unpaywall: {e}")
    return ""

def query_pubmed_central(doi: str) -> str:
    """Query PubMed Central API for a PDF URL."""
    if not doi:
        return ""
    print("Querying PubMed Central...")
    url = f"{PUBMED_CENTRAL_API}?ids={doi}&format=json"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            pmcid = response.json().get("records", [{}])[0].get("pmcid")
            if pmcid:
                print("Got a hit from PubMed Central!")
                global pubmed_central_sum
                pubmed_central_sum += 1
                return f"https://www.ncbi.nlm.nih.gov/pmc/articles/{pmcid}/pdf/"
    except Exception as e:
        print(f"Error querying PubMed Central: {e}")
    return ""

def download_pdf(url: str, output_dir: str, title: str, pub_date: str):
    """Download a PDF file."""
    if not url:
        return
    date_prefix = pub_date.split(' ')[0].replace('-', '') if pub_date else "unknown"
    filename = f"{date_prefix}_{sanitize_title(title)}.pdf"
    filepath = os.path.join(output_dir, filename)
    try:
        response = requests.get(url, stream=True, timeout=10)
        if response.status_code == 200 and "application/pdf" in response.headers.get("Content-Type", ""):
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=1024):
                    f.write(chunk)
            print(f"Downloaded: {filepath}")
        else:
            print(f"Failed to download PDF from {url}")
    except Exception as e:
        print(f"Error downloading PDF: {e}")

def search_and_download(name: str, output_dir: str):
    """Search for papers, extract PDF links, and download PDFs."""
    all_papers = []
    existing_abstracts = []

    # API Calls
    print(f"Searching papers for: {name}")
    ieee_papers = query_ieee(name)
    orcid_papers = query_orcid(name)
    pubmed_ids = query_pubmed(name)
    zenodo_papers = query_zenodo(name)

    pubmed_papers = [query_pubmed_details(pid) for pid in pubmed_ids]

    # Combine and Filter Results
    candidate_papers = ieee_papers + orcid_papers + pubmed_papers + zenodo_papers
    for paper in candidate_papers:
        abstract = paper.get("abstract", "").strip()
        if not is_similar(abstract, existing_abstracts):
            all_papers.append(paper)
            if abstract:
                existing_abstracts.append(abstract)

    save_results(all_papers, "combined_results.json")
    print("Saved all results to combined_results.json")

    print("ieee_sum =", ieee_sum)
    print("orcid_sum =", orcid_sum)
    print("pubmed_sum =", pubmed_sum)
    print("zenodo_sum =", zenodo_sum)
    print("pubmed_central_sum =", pubmed_central_sum)
    print("unpaywall_sum=", unpaywall_sum)

    # Download PDFs
    create_dir(output_dir)
    for paper in all_papers:
        doi = paper.get("doi") or paper.get("elocationid")
        pdf_url = query_unpaywall(doi, output_dir) or query_pubmed_central(doi)
        if pdf_url:
            title = paper.get("title", f"paper_{paper.get('id', '')}")
            pub_date = paper.get("pubdate", "unknown")
            download_pdf(pdf_url, output_dir, title, pub_date)
        else:
            print(f"No PDF found for {paper.get('title', 'unknown_title')}")

def main():
    data = load_json("authors.json")
    output_dir = "pdfs"
    for group, names in data.items():
        for name in names:
            os.makedirs(f"pdfs\\{name}", exist_ok=True)
            search_and_download(name, f"pdfs\\{name}")

if __name__ == "__main__":
    main()
