"""
Google Search Scraper
Handles: Results, AI-generated section, sponsored tag
"""

# TODO: Check if AI section gets scraped or not
# TODO: Need to check for sponsored sources and probably skip them
# TODO: Need to be tested for running a larger amount of queries => Delays might not be large enough to circumvent bot detection

import time
import random
import re
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from urllib.parse import urlparse, quote
import csv

# Config
PAGES_TO_SCRAPE = 2
DELAY_BETWEEN_QUERIES = 3
DELAY_BETWEEN_PAGES = 1
MAX_RETRIES = 2

AI_KEYWORDS = []
SPONSORED_KEYWORDS = []

driver = None

def setup_driver(): # Possible configurations via Options()
    global driver
    chrome_options = Options()
    chrome_options.add_argument("--lang=en") # Doesn't work?
    driver = webdriver.Chrome(options=chrome_options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    return driver

def random_delay(min_sec=1, max_sec=3):
    time.sleep(random.uniform(min_sec, max_sec))

def accept_cookies():
    try:
        cookie_button = driver.find_element(By.ID, "L2AGLb")
        cookie_button.click()
        time.sleep(1)
        return True
    except:
        return False

def extract_domain(url):
    try:
        parsed = urlparse(url)
        domain = parsed.netloc
        if domain.startswith("www."):
            domain = domain[4:]
        return domain
    except:
        return url

def get_next_page_url(driver, current_page_num):
    try:
        next_button = driver.find_element(By.ID, "pnnext")
        href = next_button.get_attribute("href")
        if href:
            return href
    except:
        pass
    return None

def extract_results(driver, query, query_type, topic, page_num):
    results = []
    try:
        WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.ID, "rso"))
        )
        results_container = driver.find_element(By.ID, "rso")
        result_elements = results_container.find_elements(By.CSS_SELECTOR, "div[jscontroller], div.g")
        
        position = 1
        
        for elem in result_elements:
            try:
                # TODO: Sponsored skip?
                
                link_element = elem.find_element(By.CSS_SELECTOR, "a")
                url = link_element.get_attribute("href")
                
                if not url or url.startswith("/search") or "google.com" in url:
                    continue
                
                title = ""
                try: 
                    title = elem.find_element(By.CSS_SELECTOR, "h3").text
                except:
                    continue
                
                if not title:
                    continue
                
                domain = extract_domain(url)
                
                results.append({
                    "topic": topic,
                    "query_type": query_type,
                    "query": query,
                    "page": page_num,
                    "position": position,
                    "url": url,
                    "domain": domain,
                    "title": title,
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                })
                
                position += 1
            except Exception as e:
                continue
    except Exception as e:
        print(f" Error extracting results: {e}")
    
    return results

def manual_captcha_handler():
    print("Please solve the CAPTCHA manually in the browser window.")
    print("After solving, press ENTER to continue...")
    input()
    print("Continuing...\n")
    time.sleep(2)

def check_for_captcha():
    try:
        # AI captcha selectors
        captcha_selectors = [
            "iframe[src*='captcha']",
            "div[aria-label*='captcha']",
            "form[action*='captcha']",
            "div[jsname='YJMvMc']",  # Google's CAPTCHA container
            "#captcha-form"
        ]
        
        for selector in captcha_selectors:
            if driver.find_elements(By.CSS_SELECTOR, selector):
                return True
        
        page_text = driver.page_source.lower()
        if "captcha" in page_text or "enter the characters" in page_text:
            return True
            
    except:
        pass
    
    return False

def perform_search(driver, query, topic, query_type, pages=PAGES_TO_SCRAPE):
    all_results = []
    results_page = 1
    ai_data = None
    
    print(f" Searching: '{query}")
    
    driver.get("https://www.google.com")
    accept_cookies()
    time.sleep(2)
    
    if check_for_captcha():
        manual_captcha_handler()
    
    try:
        search_box = driver.find_element(By.NAME, "q")
        search_box.clear()
        search_box.send_keys(query)
        search_box.send_keys(Keys.RETURN)
    except:
        print(f" Error: Coduln't enter search query")
        return all_results
    
    if check_for_captcha():
        manual_captcha_handler()
    time.sleep(2)
    
    # Scrape pages
    while results_page <= pages:
        print(f" Page {results_page}")
        time.sleep(1)
        
        # TODO: AI Overview detection here

        page_results = extract_results(driver, query, query_type, topic, results_page)
        all_results.extend(page_results)
        
        # Next page
        if results_page < pages:
            next_url = get_next_page_url(driver, results_page)
            if next_url:
                driver.get(next_url)
                time.sleep(2)
                results_page += 1
            else:
                print(f" No next page")
                break
        else:
            break
    return all_results
        
def run_scraping(queries_file='data/queries.csv', output_file='data/raw_results.csv', max_queries=None):
    global driver
    # Load queries
    df_queries = pd.read_csv(queries_file)
    if max_queries:
        df_queries = df_queries.head(max_queries)
    
    driver = setup_driver()
    time.sleep(2)
    
    all_results = []
    ai_detections = [] # TODO: Track AI overview appearance
    
    for idx, row in df_queries.iterrows():
        topic = row['topic']
        neutral_query = row['neutral']
        slanted_query = row['slanted']
        
        print(f"\n Topic {idx+1}/{len(df_queries)}: {topic}") 
        
        for query_type, query in [('neutral', neutral_query), ('slanted', slanted_query)]:
            for attempt in range (MAX_RETRIES):
                try:
                    results = perform_search(driver, query, topic, query_type)
                    all_results.extend(results)
                    print(f"Collected {len(results)} total results")
                    # TODO: Need to check AI here
                    break
                except Exception as e:
                    print(f"Attempt {attempt + 1} failed: {e}")
            time.sleep(DELAY_BETWEEN_QUERIES)
        time.sleep(5) # Delay between topics
    
    df_results = pd.DataFrame(all_results)
    df_results.to_csv(output_file, index=False)
    
    print(f"Scraping complete")
    
    driver.quit()
    
    return df_results
                    

if __name__ == "__main__":
    results = run_scraping(
        queries_file='data/queries.csv',
        output_file='data/raw_results.csv',
        max_queries=2 # For testing
    )
    
