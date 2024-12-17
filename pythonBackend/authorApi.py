"""

from dotenv import load_dotenv
import os
import json
import requests


load_dotenv()

IEEE_API_KEY = os.getenv("IEEE-API-KEY")

json_file = open('authors.json')
json_str = json_file.read()
json_data = json.loads(json_str)

print(json_data["executeive_board"])


# Base URL for the IEEE Xplore API
BASE_URL = 'https://ieeexploreapi.ieee.org/api/v1/search/articles'

# Define the query parameters
params = {
    'apikey': IEEE_API_KEY,
    'format': 'json',  # Response format
    'author': '',  # Replace with the author's name
    'max_records': 5,  # Number of results to retrieve
    'start_record': 1  # Start at the first record
}

# Make the API request
response = requests.get(BASE_URL, params=params)

# Check the response
if response.status_code == 200:
    data = response.json()
    for article in data.get('articles', []):
        print(f"Title: {article.get('title')}")
        print(f"Authors: {article.get('authors')}")
        print(f"DOI: {article.get('doi')}")
        print(f"Publication Year: {article.get('publication_year')}")
        print(f"URL: {article.get('document_link')}\n")
else:
    print(f"Error: {response.status_code}, {response.text}")
"""

import os
import json
import requests
from typing import List, Dict

def load_data(file_path: str) -> Dict:
    """Load JSON data from a file."""
    with open(file_path, 'r') as f:
        return json.load(f)

def search_papers_by_name(name: str, api_sources: List[str], pdf_dir: str) -> List[Dict]:
    """Search for papers for a given researcher using multiple APIs."""
    results = []

    if "IEEE" in api_sources:
        ieee_results = query_ieee(name, pdf_dir)
        if ieee_results:
            print(f"Got something from IEEE for {name}")
        results.extend(ieee_results)

    if "ORCID" in api_sources:
        orcid_results = query_orcid(name, pdf_dir)
        if orcid_results:
            print(f"Got something from ORCID for {name}")
        results.extend(orcid_results)

    if "DOAJ" in api_sources:
        doaj_results = query_doaj(name, pdf_dir)
        if doaj_results:
            print(f"Got something from DOAJ for {name}")
        results.extend(doaj_results)

    if "PubMed" in api_sources:
        pubmed_results = query_pubmed(name, pdf_dir)
        if pubmed_results:
            print(f"Got something from PubMed for {name}")
        results.extend(pubmed_results)

    if "Zenodo" in api_sources:
        zenodo_results = query_zenodo(name, pdf_dir)
        if zenodo_results:
            print(f"Got something from Zenodo for {name}")
        results.extend(zenodo_results)

    return results

def download_pdf(pdf_url: str, output_dir: str, paper_title: str) -> str:
    """Download a PDF file and save it locally."""
    try:
        response = requests.get(pdf_url, stream=True)
        if response.status_code == 200:
            filename = f"{paper_title[:50].replace(' ', '_')}.pdf"
            filepath = os.path.join(output_dir, filename)
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=1024):
                    f.write(chunk)
            return filepath
        else:
            print(f"Failed to download PDF from {pdf_url}: {response.status_code}")
            return ""
    except Exception as e:
        print(f"Error downloading PDF: {e}")
        return ""

def query_ieee(name: str, pdf_dir: str) -> List[Dict]:
    """Query IEEE API for papers."""
    api_key = "currently_not_avaiable_aus_IEEE_seite"  
    url = f"https://ieeexploreapi.ieee.org/api/v1/search/articles?author={name}&apikey={api_key}"
    response = requests.get(url)
    if response.status_code == 200:
        articles = response.json().get('articles', [])
        for article in articles:
            if 'pdf' in article:
                article['pdf_path'] = download_pdf(article['pdf'], pdf_dir, article.get('title', 'paper'))
        return articles
    else:
        print(f"Error querying IEEE for {name}: {response.status_code}")
        return []

def query_orcid(name: str, pdf_dir: str) -> List[Dict]:
    """Query ORCID API for papers."""
    url = f"https://pub.orcid.org/v3.0/search/?q=author:{name}"
    headers = {"Accept": "application/json"}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        results = response.json().get('results', [])
        for result in results:
            if 'pdf_url' in result:
                result['pdf_path'] = download_pdf(result['pdf_url'], pdf_dir, result.get('title', 'paper'))
        return results
    else:
        print(f"Error querying ORCID for {name}: {response.status_code}")
        return []

def query_doaj(name: str, pdf_dir: str) -> List[Dict]:
    """Query DOAJ API for papers."""
    url = f"https://doaj.org/api/v1/search/articles/{name}"
    response = requests.get(url)
    if response.status_code == 200:
        results = response.json().get('results', [])
        for result in results:
            if 'pdf_url' in result:
                result['pdf_path'] = download_pdf(result['pdf_url'], pdf_dir, result.get('title', 'paper'))
        return results
    else:
        print(f"Error querying DOAJ for {name}: {response.status_code}")
        return []


def query_pubmed(name: str, pdf_dir: str) -> List[Dict]:
    """Query PubMed API for papers."""
    url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term={name}&retmode=json"
    response = requests.get(url)
    if response.status_code == 200:
        paper_ids = response.json().get("esearchresult", {}).get("idlist", [])
        return [query_pubmed_details(pid, pdf_dir) for pid in paper_ids]
    else:
        print(f"Error querying PubMed for {name}: {response.status_code}")
        return []

def query_pubmed_details(paper_id: str, pdf_dir: str) -> Dict:
    """Query details for a specific PubMed paper."""
    url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pubmed&id={paper_id}&retmode=json"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json().get("result", {}).get(paper_id, {})
    else:
        print(f"Error retrieving details for PubMed ID {paper_id}: {response.status_code}")
        return {}


def query_zenodo(name: str, pdf_dir: str) -> List[Dict]:
    """Query Zenodo API for papers."""
    url = f"https://zenodo.org/api/records/?q=authors.name:{name}"
    response = requests.get(url)
    if response.status_code == 200:
        results = response.json().get("hits", {}).get("hits", [])
        for result in results:
            if 'files' in result:
                for file in result['files']:
                    if file.get('type') == 'pdf':
                        result['pdf_path'] = download_pdf(file['links']['self'], pdf_dir, result.get('title', 'paper'))
                        break
        return results
    else:
        print(f"Error querying Zenodo for {name}: {response.status_code}")
        return []


def save_results(results: List[Dict], output_file: str):
    """Save results to a JSON file."""
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)

def main():
    # Load input JSON
    data = load_data("authors.json")

    # Directory to save PDFs
    pdf_dir = "pdfs"
    os.makedirs(pdf_dir, exist_ok=True)

    # Combined results
    all_results = {}

    # Iterate over all groups
    for group, names in data.items():
        group_results = {}
        for name in names:
            print(f"Searching papers for: {name}")
            group_results[name] = search_papers_by_name(name, ["IEEE", "ORCID", "DOAJ", "PubMed", "Zenodo"], pdf_dir)
        all_results[group] = group_results

    # Save all results to a file
    save_results(all_results, "papers_results.json")

if __name__ == "__main__":
    main()
