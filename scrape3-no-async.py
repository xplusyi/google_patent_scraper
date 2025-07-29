from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from bs4 import BeautifulSoup
import requests
import json

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ #
#               Custom Errors
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ #

class PatentScrapingError(Exception):
    """Custom exception for errors during the patent scraping process."""
    pass

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ #
#               Core Function
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ #

def get_description(patent_number: str):
    """
    Fetches the publication number and description for a given patent number
    from Google Patents, correctly handling redirects.

    This function uses Playwright to launch a browser, navigate to the page,
    and capture the final URL after any JavaScript-based redirections.

    Args:
        patent_number (str): The patent number to look up.
                             (e.g., 'US2014262394', 'US8834455B2')

    Returns:
        dict: A dictionary containing the 'publication_number', 'description',
              and the 'final_url' that was scraped.
              Returns a dictionary with an 'error' key if scraping fails.
    """
    if not isinstance(patent_number, str) or not patent_number:
        raise ValueError("The 'patent_number' must be a non-empty string.")

    print(f"🚀 Starting scrape for: {patent_number}")

    with sync_playwright() as p:
        browser = None
        try:
            # Launch a headless browser
            browser = p.chromium.launch()
            page = browser.new_page()

            # Construct the initial URL. Google will handle the redirect.
            initial_url = f"https://patents.google.com/?oq={patent_number}"
            
            # Go to the page and wait for it to load.
            # 'load' waits for the 'load' event, which is more reliable.
            page.goto(initial_url, wait_until='load', timeout=60000)

            # *** THIS IS THE KEY STEP ***
            # Capture the final URL after any client-side redirects.
            final_url = page.url
            print(f"➡️  Initial URL: {initial_url}")
            print(f"✅ Final URL after redirect: {final_url}")

            # Use requests to get the final page content. This can sometimes be
            # more reliable or faster than getting it directly from Playwright
            # after page load.
            headers = {'User-Agent': 'Mozilla/5.0'}
            response = requests.get(final_url, headers=headers, timeout=20)
            response.raise_for_status() # Raises HTTPError for bad responses (4xx or 5xx)
            soup = BeautifulSoup(response.content, "lxml")

            # --- Extract Publication Number ---
            # This will now be the correct, final publication number.
            publication_number_element = soup.find('dd', itemprop="publicationNumber")
            publication_number = publication_number_element.get_text(strip=True) if publication_number_element else "Not Found"

            # --- Extract Description ---
            description_element = soup.find('section', itemprop='description')
            description_text = description_element.get_text(separator='\n', strip=True) if description_element else "Description not found."

            print(f"✅ Successfully scraped data for {patent_number}")
            return {
                'input_patent_number': patent_number,
                'publication_number': publication_number,
                'final_url': final_url,
                'description': description_text
            }

        except PlaywrightTimeoutError:
            error_msg = f"Timeout Error: The page for patent '{patent_number}' took too long to load."
            print(f"❌ {error_msg}")
            raise PatentScrapingError(error_msg) from PlaywrightTimeoutError

        except Exception as e:
            error_msg = f"An unexpected error occurred: {e}"
            print(f"❌ {error_msg}")
            raise PatentScrapingError(error_msg) from e
        
        finally:
            # Ensure the browser is closed even if errors occur
            if browser:
                browser.close()

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ #
#               Example Usage
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ #

def main():
    """Main function to run the scraper."""
    # Example patent number that often redirects from an application number
    # to a granted patent number.
    test_patent_number = 'US2014262394' 

    try:
        # Call the sync function and get the result
        patent_data = get_description(test_patent_number)

        # --- Print the results ---
        print("\n" + "="*50)
        print("              Patent Scraping Results")
        print("="*50)
        print(f"Input Patent Number: {patent_data.get('input_patent_number', 'N/A')}")
        print(f"Final Publication Number: {patent_data.get('publication_number', 'N/A')}")
        print(f"Scraped URL: {patent_data.get('final_url', 'N/A')}")
        print("\n--- Description (first 120 chars) ---")
        # Pretty print the description
        print(patent_data.get('description', 'N/A')[:120] + "...")
        print("="*50)

        # You can also save the output to a file
        # file_name = f"{patent_data.get('publication_number', 'output').replace(' ', '_')}.json"
        # with open(file_name, "w", encoding="utf-8") as f:
        #     json.dump(patent_data, f, indent=4, ensure_ascii=False)
        # print(f"\n📄 Results saved to {file_name}")

    except (ValueError, PatentScrapingError) as e:
        print(f"\n--- 🚨 Error ---")
        print(e)

if __name__ == "__main__":
    # To run this script, you need to have playwright installed:
    # pip install playwright
    # playwright install
    main()
