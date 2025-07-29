# main.py
import asyncio
import json
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

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
    Google scraper class using Playwright to scrape data from 'https://patents.google.com/'.

    This version uses Playwright to launch a browser, ensuring that dynamically loaded
    content (via JavaScript) is captured.

    There are two primary ways to use the class:

        (1) Add a list of patents and scrape them all at once.

            with scraper_class() as scraper: #<- Use as a context manager
                # ~ Add patents to list ~ #
                scraper.add_patents('US2668287A')
                scraper.add_patents('US8834455B2') # Another example

                # ~ Scrape all patents ~ #
                scraper.scrape_all_patents()

                # ~ Get results of scrape ~ #
                patent_1_parsed = scraper.parsed_patents['US2668287A']
                patent_2_parsed = scraper.parsed_patents['US8834455B2']
                print(json.dumps(patent_1_parsed, indent=2))


        (2) Scrape each patent individually.

            with scraper_class() as scraper: #<- Use as a context manager
                # ~~ Scrape patents individually ~~ #
                patent_1 = 'US2668287A'
                err_1, soup_1, url_1 = scraper.request_single_patent(patent_1)
                if err_1 == 'Success':
                    patent_1_parsed = scraper.get_scraped_data(soup_1, patent_1, url_1)
                    print(json.dumps(patent_1_parsed, indent=2))


    Attributes:
        list_of_patents (list): Patents to be scraped.
        scrape_status (dict): Status of the request for each patent.
        parsed_patents (dict): The parsed data for each successfully scraped patent.
        return_abstract (bool): If True, the abstract will be included in the output.
        return_description (bool): If True, the description will be included.
        return_claims (bool): If True, the claims will be included.
        playwright (SyncPlaywright): The Playwright instance.
        browser (Browser): The Playwright browser instance.
    """
    def __init__(self, return_abstract=False, return_description=False, return_claims=False, headless=True):
        """Initializes the scraper, starts Playwright, and launches a browser."""
        self.list_of_patents = []
        self.scrape_status = {}
        self.parsed_patents = {}
        self.return_abstract = return_abstract
        self.return_description = return_description
        self.return_claims = return_claims
        
        # --- Playwright Initialization ---
        try:
            self.playwright = sync_playwright().start()
            self.browser = self.playwright.chromium.launch(headless=headless)
        except Exception as e:
            print(f"Failed to initialize Playwright: {e}")
            raise

    def __enter__(self):
        """Enter context manager."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context manager, ensuring resources are closed."""
        self.close()

    def close(self):
        """Closes the Playwright browser and stops the Playwright instance."""
        print("Closing browser and Playwright resources...")
        if hasattr(self, 'browser') and self.browser:
            self.browser.close()
        if hasattr(self, 'playwright') and self.playwright:
            self.playwright.stop()
        print("Resources closed.")

    def add_patents(self, patent):
        """
        Append a patent to the patent list attribute self.list_of_patents.

        Args:
            patent (str): The patent number.
        """
        if not isinstance(patent, str):
            raise PatentClassError("'patent' variable must be a string")
        self.list_of_patents.append(patent)

    def delete_patents(self, patent):
        """
        Remove a patent from the patent list.

        Args:
            patent (str): The patent number to remove.
        """
        if patent in self.list_of_patents:
            self.list_of_patents.remove(patent)
        else:
            print(f'Patent {patent} not in patent list')

    def add_scrape_status(self, patent, success_value):
        """Add the status of a scrape to the scrape_status dictionary."""
        self.scrape_status[patent] = success_value

    async def request_single_patent(self, patent):
        """
        Fetches a single patent page using Playwright and returns the parsed HTML.

        Args:
            patent (str): The patent number (e.g., 'US2668287A').

        Returns:
            tuple: A tuple containing:
                - str: The status of the scrape ('Success' or an error message).
                - BeautifulSoup object or str: The parsed HTML soup, or an empty string on failure.
                - str: The final URL visited.
        """
        
        p = self.playwright
        browser = await p.chromium.launch()
        page = await browser.new_page()
        try:
            initial_url = f"https://patents.google.com/?oq={patent}"
            await page.goto(initial_url, wait_until='networkidle', timeout=60000)

            # After waiting, the page URL will have updated to the final redirected URL.
            final_url = page.url
            print(f"➡️ Redirected to: {final_url}")
            html_content = await page.content()

            soup = BeautifulSoup(html_content, "lxml")
            page.close()
            return 'Success', soup, final_url
        except PlaywrightTimeoutError:
            error_msg = f'Timeout Error: The page at {url} took too long to load.'
            print(f'Patent: {patent}, {error_msg}')
            if page:
                page.close()
            return error_msg, '', url
        except Exception as e:
            error_msg = f'An unexpected error occurred: {e}'
            print(f'Patent: {patent}, {error_msg}')
            if page:
                page.close()
            return error_msg, '', url

    def parse_citation(self, single_citation):
        """
        Parses a single patent citation from a table row element.

        Args:
            single_citation (bs4.element.Tag): The BeautifulSoup tag for a citation row.

        Returns:
            dict: A dictionary with 'patent_number', 'priority_date', and 'publication_date'.
        """
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
            
        return {
            'patent_number': patent_number,
            'priority_date': priority_date,
            'publication_date': publication_date
        }

    def process_patent_html(self, soup):
        """
        Parses the full HTML of a patent page to extract key information.

        Args:
            soup (bs4.BeautifulSoup): The BeautifulSoup object for the patent page.

        Returns:
            dict: A dictionary containing all extracted patent data.
        """
        # --- Title ---
        try:
            title_text = soup.find('meta', attrs={'name': 'DC.title'})['content'].rstrip()
        except (TypeError, KeyError):
            title_text = ''

        # --- Inventors & Assignees ---
        inventor_name = [x.get_text(strip=True) for x in soup.find_all('dd', itemprop='inventor')]
        assignee_name_orig = [x.get_text(strip=True) for x in soup.find_all('dd', itemprop='assigneeOriginal')]
        assignee_name_current = [x.get_text(strip=True) for x in soup.find_all('dd', itemprop='assigneeCurrent')]

        # --- Core Dates & Numbers ---
        try:
            publication_date = soup.find('dd', itemprop='publicationDate').get_text(strip=True)
        except AttributeError:
            publication_date = ''
        
        try:
            application_number = soup.find('dd', itemprop="applicationNumber").get_text(strip=True)
        except AttributeError:
            application_number = ''
            
        try:
            filing_date = soup.find('span', itemprop='filingDate').get_text(strip=True)
        except AttributeError:
            filing_date = ''

        # --- Legal Status ---
        try:
            legal_status_ifi = soup.find('dd', itemprop='legalStatusIfi').get_text(strip=True)
        except AttributeError:
            legal_status_ifi = ''

        # --- Event Dates (Priority, Granted, Expiration) ---
        priority_date, granted_date, expiration_date = '', '', ''
        for event in soup.find_all('dd', itemprop='events'):
            try:
                event_type = event.find('span', itemprop='type').get_text(strip=True)
                event_date = event.find('time', itemprop='date').get_text(strip=True)
                if event_type == 'priority':
                    priority_date = event_date
                elif event_type == 'granted':
                    granted_date = event_date
                elif event_type == 'publication' and not publication_date:
                    publication_date = event_date
                
                event_title_span = event.find('span', itemprop='title')
                if event_title_span and 'expiration' in event_title_span.get_text(strip=True).lower():
                    expiration_date = event_date
            except AttributeError:
                continue

        # --- Citations ---
        forward_cites_no_family = [self.parse_citation(c) for c in soup.find_all('tr', itemprop="forwardReferencesOrig")]
        forward_cites_yes_family = [self.parse_citation(c) for c in soup.find_all('tr', itemprop="forwardReferencesFamily")]
        backward_cites_no_family = [self.parse_citation(c) for c in soup.find_all('tr', itemprop='backwardReferences')]
        backward_cites_yes_family = [self.parse_citation(c) for c in soup.find_all('tr', itemprop='backwardReferencesFamily')]

        # --- Classifications ---
        classifications = []
        for item in soup.find_all('li', itemprop='classifications'):
            if item.find('meta', itemprop='Leaf', content='true'):
                try:
                    code = item.find('span', itemprop='Code').get_text(strip=True)
                    description = item.find('span', itemprop='Description').get_text(strip=True)
                    classifications.append({'code': code, 'description': description})
                except AttributeError:
                    continue
        
        # --- Abstract, Description, Claims (optional) ---
        abstract_text, description_text, claims_text = '', '', ''
        if self.return_abstract:
            abstract_element = soup.select_one(".abstract")
            abstract_text = abstract_element.text.strip() if abstract_element else "Abstract not found"

        if self.return_description:
            description_html = soup.find('section', itemprop='description')
            description_text = description_html.get_text(separator='\n', strip=True) if description_html else ""

        if self.return_claims:
            claims_html = soup.find('section', itemprop='claims')
            claims_text = claims_html.get_text(separator='\n', strip=True) if claims_html else ""

        # --- Return Data ---
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
            'legal_status': legal_status_ifi,
            'forward_cite_no_family': json.dumps(forward_cites_no_family, ensure_ascii=False),
            'forward_cite_yes_family': json.dumps(forward_cites_yes_family, ensure_ascii=False),
            'backward_cite_no_family': json.dumps(backward_cites_no_family, ensure_ascii=False),
            'backward_cite_yes_family': json.dumps(backward_cites_yes_family, ensure_ascii=False),
            'classifications': json.dumps(classifications, ensure_ascii=False),
            'abstract_text': abstract_text,
            'description_text': description_text,
            'claims_text': claims_text
        }

    def get_scraped_data(self, soup, patent, url):
        """Processes the soup and adds metadata."""
        parsed_data = self.process_patent_html(soup)
        parsed_data['url'] = url
        parsed_data['patent'] = patent
        return parsed_data

    def scrape_all_patents(self):
        """Scrapes all patents in the list self.list_of_patents."""
        if not self.list_of_patents:
            raise NoPatentsError("No patents to scrape. Add patents using scraper.add_patents()")
            
        for patent in self.list_of_patents:
            error_status, soup, url = self.request_single_patent(patent)
            self.add_scrape_status(patent, error_status)
            if error_status == 'Success':
                self.parsed_patents[patent] = self.get_scraped_data(soup, patent, url)
            else:
                self.parsed_patents[patent] = {'error': error_status}



async def main():
    # Using a 'with' statement is recommended to ensure the browser closes properly.
    with scraper_class(return_abstract=True, return_claims=True, headless=True) as scraper:
        
        # Add the patents you want to scrape
        scraper.add_patents('US2014262394')
        # scraper.add_patents('US8834455B2')
        # scraper.add_patents('US-11000000-B2') # Example with a different format

        # Scrape all patents in the list
        scraper.scrape_all_patents()

        # Print the results
        print("\n--- Scraping Results ---")
        for patent_id, data in scraper.parsed_patents.items():
            print(f"\n--- Data for Patent: {patent_id} ---")
            if 'error' in data:
                print(f"Failed to scrape: {data['error']}")
            else:
                # Pretty print the JSON data
                print(json.dumps(data, indent=4))
        
        print("\n--- Scrape Status ---")
        print(json.dumps(scraper.scrape_status, indent=4))


# Run the main function
if __name__ == "__main__":
    # This allows the async main function to be run.
    asyncio.run(main())