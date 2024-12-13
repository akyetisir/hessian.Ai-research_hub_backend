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
