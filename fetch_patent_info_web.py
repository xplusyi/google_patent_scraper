import requests
from bs4 import BeautifulSoup

def fetch_patent_info(patent_number: str) -> dict:
    """
    Extracts the abstract, description, and claims from a Google Patents page.

    Args:
        patent_number (str): The patent number.

    Returns:
        dict: A dictionary containing the patent number, abstract, description, and claims.
              Returns None if the page cannot be fetched.
    """
    url = f"https://patents.google.com/patent/{patent_number}"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()  # Raise HTTPError for bad responses
    except requests.exceptions.RequestException as e:
        print(f"Error fetching patent {patent_number}: {e}")
        return None

    soup = BeautifulSoup(response.content, features="html.parser")

    # Helper function to extract text, handling None
    def extract_text(selector):
        element = soup.select_one(selector)
        return element.text.strip() if element else None

    abstract = extract_text(".abstract")
    description_element = soup.find("section", {"itemprop": "description"})
    description = description_element.text.strip() if description_element else None
    claims_section = soup.find("section", {"itemprop": "claims"})
    claims = claims_section.text.strip() if claims_section else None

    return {
        "patent_number": patent_number,
        "abstract": abstract,
        "description": description,
        "claims": claims,
    }

def main():
    """
    Main function to demonstrate the usage of get_patent_text.
    """
    patent_number = "CN117300988"  # Example patent number
    patent_text = fetch_patent_info(patent_number)

    if patent_text:
        print(f"Patent Number: {patent_text['patent_number']}")
        print(f"Abstract: {patent_text['abstract'][0:10]}")
        print(f"Description: {patent_text['description'][0:100]}")
        print(f"Claims: {patent_text['claims'][0:100]}")
        print(f"{len(patent_text['description'])= }")
        print(f"{len(patent_text['claims'])= }")
    else:
        print(f"Could not retrieve patent text for {patent_number}")

if __name__ == "__main__":
    main()
