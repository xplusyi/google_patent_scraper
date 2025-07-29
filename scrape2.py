# main.py
import asyncio
import json
import requests
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ #
#                 Custom Errors
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ #

class PatentClassError(Exception):
    """Custom exception for errors in patent class usage."""
    pass

class NoPatentsError(Exception):
    """Custom exception for when no patents are provided to scrape."""
    pass

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ #
#             Create scraper class
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ #
class scraper_class:
    """
    Asynchronous Google scraper class using Playwright to scrape data from 'https://patents.google.com/'.

    This version uses the async API of Playwright to fetch patents concurrently,
    which is significantly faster for multiple patents.

    Usage:

    async def main():
        # Use 'async with' to manage the browser lifecycle
        async with scraper_class(return_abstract=True, return_claims=True, return_description=True) as scraper:
            scraper.add_patents('US2668287A')
            scraper.add_patents('US8834455B2')

            # This will now run all scraping tasks concurrently
            await scraper.scrape_all_patents()

            print(json.dumps(scraper.parsed_patents, indent=2))

    if __name__ == "__main__":
        asyncio.run(main())
    """
    def __init__(self, return_abstract=False, return_description=False, return_claims=False, headless=True):
        """Initializes the scraper's configuration."""
        self.list_of_patents = []
        self.scrape_status = {}
        self.parsed_patents = {}
        self.return_abstract = return_abstract
        self.return_description = return_description
        self.return_claims = return_claims
        self.headless = headless
        self.playwright = None
        self.browser = None

    async def __aenter__(self):
        """
        Asynchronous context manager entry.
        Initializes Playwright and the browser.
        """
        print("Starting Playwright and launching browser...")
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=self.headless)
        print("Browser launched.")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """
        Asynchronous context manager exit.
        Ensures resources are closed properly.
        """
        print("Closing browser and Playwright resources...")
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        print("Resources closed.")

    def add_patents(self, patent):
        """Appends a patent to the list to be scraped."""
        if not isinstance(patent, str):
            raise PatentClassError("'patent' variable must be a string")
        self.list_of_patents.append(patent)

    def delete_patents(self, patent):
        """Removes a patent from the list."""
        if patent in self.list_of_patents:
            self.list_of_patents.remove(patent)
        else:
            print(f'Patent {patent} not in patent list')

    def add_scrape_status(self, patent, success_value):
        """Adds the status of a scrape to the dictionary."""
        self.scrape_status[patent] = success_value

    async def request_single_patent(self, patent):
        """
        Fetches a single patent page asynchronously.

        Args:
            patent (str): The patent number.

        Returns:
            tuple: A tuple containing the patent number and the result dictionary.
                   The result will contain either the parsed data or an error message.
        """
        initial_url = f"https://patents.google.com/?oq={patent}"
        print(f"🚀 Starting scrape for: {patent} at {initial_url}")
        
        page = None
        try:
            page = await self.browser.new_page()
            await page.goto(initial_url, wait_until='load', timeout=60000)
            final_url = page.url
            print(f"➡️ Redirected to: {final_url} for patent {patent}")
            
            # *** FIX: Explicitly wait for a key element to be visible. ***
            # This is the crucial step. We wait for the element containing the publication
            # date to appear. This ensures the page's JavaScript has finished rendering
            # the dynamic content before we try to parse the HTML.

            # print(f"⏳ Waiting for content to load for patent {patent}...")
            # await page.wait_for_selector('dd[itemprop="assigneeCurrent"]', timeout=10000)
            # print(f"✅ Content loaded for patent {patent}.")
            # html_content = await page.content()
            # soup = BeautifulSoup(html_content, "lxml")

            headers = {'User-Agent': 'Mozilla/5.0'}
            response = requests.get(final_url, headers=headers, timeout=20)
            response.raise_for_status() # Raises HTTPError for bad responses (4xx or 5xx)
            soup = BeautifulSoup(response.content, features="lxml")
            
            # Process the data and return it
            parsed_data = self.get_scraped_data(soup, patent, final_url)
            self.add_scrape_status(patent, 'Success')
            await page.close()
            return patent, parsed_data

        except PlaywrightTimeoutError:
            error_msg = f'Timeout Error: Could not find key content on page {final_url}. The page might not be a valid patent page or took too long to load.'
            print(f'❌ Patent: {patent}, {error_msg}')
            if page: await page.close()
            self.add_scrape_status(patent, error_msg)
            return patent, {'error': error_msg}
        except Exception as e:
            error_msg = f'An unexpected error occurred: {e}'
            print(f'❌ Patent: {patent}, {error_msg}')
            if page: await page.close()
            self.add_scrape_status(patent, error_msg)
            return patent, {'error': error_msg}

    def parse_citation(self, single_citation):
        """Parses a single patent citation from a table row element."""
        try:
            patent_number = single_citation.find('span', itemprop='publicationNumber').get_text(strip=True)
        except AttributeError:
            patent_number = ''
        try:
            priority_date = single_citation.find('td', itemprop='priorityDate').get_text(strip=True)
        except AttributeError:
            priority_date = ''
        try:
            publication_date = single_citation.find('td', itemprop='publicationDate').get_text(strip=True)
        except AttributeError:
            publication_date = ''
        return {'patent_number': patent_number, 'priority_date': priority_date, 'publication_date': publication_date}

    def process_patent_html(self, soup):
        """Parses the full HTML of a patent page to extract key information."""
        try:
            # Using a more specific selector for the title
            # title_element = soup.find('h1', id='title')
            # title_text = title_element.get_text(strip=True) if title_element else ''
            title = soup.find('meta',attrs={'name':'DC.title'})
            title_text=title['content'].rstrip()
        except (TypeError, KeyError, AttributeError):
            title_text = ''


        inventor_name = [x.get_text(strip=True) for x in soup.find_all('dd', itemprop='inventor')]
        assignee_name_orig = [x.get_text(strip=True) for x in soup.find_all('dd', itemprop='assigneeOriginal')]
        assignee_name_current = [x.get_text(strip=True) for x in soup.find_all('dd', itemprop='assigneeCurrent')]

        try:
            publication_date = soup.find('dd', itemprop='publicationDate').get_text(strip=True)
        except AttributeError:
            publication_date = ''
        try:
            publication_number = soup.find('dd',itemprop="publicationNumber").get_text()
        except:
            publication_number = ''
        try:
            application_number = soup.find('dd', itemprop="applicationNumber").get_text(strip=True)
        except AttributeError:
            application_number = ''
        try:
            filing_date_element = soup.find('dd', itemprop='filingDate')
            filing_date = filing_date_element.find('time').get_text(strip=True) if filing_date_element else ''
        except AttributeError:
            filing_date = ''
        try:
            legal_status_ifi = soup.find('dd', itemprop='legalStatusIfi').get_text(strip=True)
        except AttributeError:
            legal_status_ifi = ''

        priority_date, granted_date, expiration_date = '', '', ''
        for event in soup.find_all('dd', itemprop='events'):
            try:
                event_type = event.find('span', itemprop='type').get_text(strip=True)
                event_date = event.find('time', itemprop='date').get_text(strip=True)
                if event_type == 'priority': priority_date = event_date
                elif event_type == 'granted': granted_date = event_date
                elif event_type == 'publication' and not publication_date: publication_date = event_date
                event_title_span = event.find('span', itemprop='title')
                if event_title_span and 'expiration' in event_title_span.get_text(strip=True).lower():
                    expiration_date = event_date
            except AttributeError:
                continue

        forward_cites_no_family = [self.parse_citation(c) for c in soup.find_all('tr', itemprop="forwardReferencesOrig")]
        forward_cites_yes_family = [self.parse_citation(c) for c in soup.find_all('tr', itemprop="forwardReferencesFamily")]
        backward_cites_no_family = [self.parse_citation(c) for c in soup.find_all('tr', itemprop='backwardReferences')]
        backward_cites_yes_family = [self.parse_citation(c) for c in soup.find_all('tr', itemprop='backwardReferencesFamily')]

        classifications = []
        for item in soup.find_all('li', itemprop='classifications'):
            if item.find('meta', itemprop='Leaf', content='true'):
                try:
                    code = item.find('span', itemprop='Code').get_text(strip=True)
                    description = item.find('span', itemprop='Description').get_text(strip=True)
                    classifications.append({'code': code, 'description': description})
                except AttributeError:
                    continue
        
        abstract_text, description_text, claims_text = '', '', ''
        if self.return_abstract:
            abstract_element = soup.select_one("section.abstract > div.abstract")
            abstract_text = abstract_element.text.strip() if abstract_element else "Abstract not found"
        if self.return_description:
            description_html = soup.find('section', itemprop='description')
            description_text = description_html.get_text(separator='\n', strip=True) if description_html else ""
        if self.return_claims:
            claims_html = soup.find('section', itemprop='claims')
            claims_text = claims_html.get_text(separator='\n', strip=True) if claims_html else ""

        return {
            'title': title_text, 
            'inventor_name': json.dumps(inventor_name, ensure_ascii=False),
            'assignee_name_orig': json.dumps(assignee_name_orig, ensure_ascii=False),
            'assignee_name_current': json.dumps(assignee_name_current, ensure_ascii=False),
            'publication_date': publication_date, 
            'priority_date': priority_date,
            'granted_date': granted_date, 
            'filing_date': filing_date, 
            'expiration_date': expiration_date,
            'application_number': application_number, 
            'publication_number': publication_number,
            'legal_status': legal_status_ifi,
            'forward_cite_no_family': json.dumps(forward_cites_no_family, ensure_ascii=False),
            'forward_cite_yes_family': json.dumps(forward_cites_yes_family, ensure_ascii=False),
            'backward_cite_no_family': json.dumps(backward_cites_no_family, ensure_ascii=False),
            'backward_cite_yes_family': json.dumps(backward_cites_yes_family, ensure_ascii=False),
            'classifications': json.dumps(classifications, ensure_ascii=False),
            'abstract_text': abstract_text, 
            'description_text': description_text, 
            'claims_text': claims_text,
        }

    def get_scraped_data(self, soup, patent, url):
        """Processes the soup and adds metadata."""
        parsed_data = self.process_patent_html(soup)
        parsed_data['url'] = url
        parsed_data['patent'] = patent
        return parsed_data

    async def scrape_all_patents(self):
        """
        Scrapes all patents in the list concurrently.
        """
        if not self.list_of_patents:
            raise NoPatentsError("No patents to scrape. Add patents using scraper.add_patents()")
        
        tasks = [self.request_single_patent(patent) for patent in self.list_of_patents]
        results = await asyncio.gather(*tasks)
        
        for patent_id, data in results:
            self.parsed_patents[patent_id] = data

async def main():
    """Main function to run the scraper."""
    async with scraper_class(return_abstract=True, return_claims=0, return_description=0, headless=False) as scraper:
        
        scraper.add_patents('US2014262394') 
        # scraper.add_patents('US8834455B2')
        # scraper.add_patents('US-11000000-B2')
        # scraper.add_patents('WO2022060606A1')

        await scraper.scrape_all_patents()

        print("\n--- ✅ Scraping Results ---")
        print(json.dumps(scraper.parsed_patents, indent=4))
        
        print("\n--- 📊 Scrape Status ---")
        print(json.dumps(scraper.scrape_status, indent=4))

if __name__ == "__main__":
    asyncio.run(main())
