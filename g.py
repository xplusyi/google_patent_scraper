# ~ Import packages ~ #
from google_patent_scraper import scraper_class
from pprint import pprint

# ~ Initialize scraper class ~ #
scraper=scraper_class(return_abstract=0, return_description=0, return_claims=0) 

# ~~ Scrape patents individually ~~ #
patent_1 = 'CN221936334' # 'CN113328596' # 'US2668287A'

# patent_2 = 'US266827A'
err_1, soup_1, url_1 = scraper.request_single_patent(patent_1)
# err_2, soup_2, url_2 = scraper.request_single_patent(patent_2)

# ~ Parse results of scrape ~ #
patent_1_parsed = scraper.get_scraped_data(soup_1,patent_1,url_1)
# patent_2_parsed = scraper.get_scraped_data(soup_2,patent_2,url_2)


print('-----------------------------')

print(patent_1_parsed['title'])
# print(patent_1_parsed['abstract_text'][100])
# print(patent_1_parsed['claims_text'][100])
print( f"DESC length is: {len( patent_1_parsed['description_text'])}" )
print( f"DESC is: { patent_1_parsed['description_text'][0:80] }" )
print( f"Abstract is: { patent_1_parsed['abstract_text'][0:20] }" )
print( f"Claims is: { patent_1_parsed['claims_text'][0:50] }" )

print('**************************\n')
pprint(patent_1_parsed['classifications'])
pprint(patent_1_parsed['inventor_name'])
pprint(patent_1_parsed['assignee_name_orig'])
pprint(patent_1_parsed)