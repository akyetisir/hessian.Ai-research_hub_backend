"""
    Script to scrape all authors from the following site:
    https://hessian.ai/de/ueber-uns/#researchers
 """

#$ python -m pip install beautifulsoup4
import requests 
import re
import json
from bs4 import BeautifulSoup

URL = "https://hessian.ai/de/ueber-uns/#researchers"

def select_container(container, selector:str):
    return container.find('h3', string=selector).find_next_sibling("div").find_next_sibling("div")

def extract_authors(container):
    authors = container.find_all('a', {'href': re.compile(r"https:\/\/hessian\.ai\/de\/personen\/")})
    author_list = []
    for author in authors:
    # filter out empty text from image links
        if len(author.text) > 0:
            author_list.append(author.text)
    return author_list

if __name__ == "__main__":    
    page = requests.get(URL)
    soup = BeautifulSoup(page.content, "html.parser")
    tags = {"executeive_board": "Vorstand",
            "faculty": "Mitglied",
            "research_group_leaders": "Nachwuchsgruppenleitung",
            "fellows": "Fellows"
            }
    # dont use these tags:
    # "alumni": "Alumni", "managing_office":"Geschäftsstelle"
    
    author_list = {key:[] for key,_ in tags.items()}
    for tag, selector in tags.items():
        container = select_container(soup, selector)
        author_list[tag] = extract_authors(container)
    
    with open('authors.json', 'w') as f:
        json.dump(author_list, f, indent=4)