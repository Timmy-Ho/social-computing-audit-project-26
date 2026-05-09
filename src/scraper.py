"""
Google Search Scraper
Handles: Results, AI-generated section, sponsored tag
"""

# TODO: Need to check for sponsored sources and probably skip them
# Scraper might require an initial captcha check, but should be fine afterwards

import time
import random
import re
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium_stealth import stealth
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from urllib.parse import urlparse, quote
import csv


# Config
PAGES_TO_SCRAPE = 3
DELAY_BETWEEN_QUERIES = 5
DELAY_BETWEEN_PAGES = 1
MAX_RETRIES = 2

AI_KEYWORDS = []
SPONSORED_KEYWORDS = []

driver = None

def setup_driver():
    global driver
    chrome_options = Options()
    chrome_options.add_argument("--lang=en")
    chrome_options.add_argument("--user-data-dir=/tmp/chrome_profile_google")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)
    
    driver = webdriver.Chrome(options=chrome_options)
    
    # Apply stealth
    stealth(driver,
        languages=["en-US", "en"],
        vendor="Google Inc.",
        platform="Win32",
        webgl_vendor="Intel Inc.",
        renderer="Intel Iris OpenGL Engine",
        fix_hairline=True,
    )
    
    return driver

def random_delay(min_sec=2, max_sec=6):
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
    sponsored_skipped = 0
    try:
        WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.ID, "rso"))
        )
        results_container = driver.find_element(By.ID, "rso")
        result_elements = results_container.find_elements(By.CSS_SELECTOR, "div[jscontroller], div.g")
        
        position = 1
        
        for elem in result_elements:
            try:
                if check_for_captcha(): 
                    manual_captcha_handler()
                
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
        # print(f"Page {page_num}: {sponsored_skipped} sponsored skipped")
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
        captcha_selectors = [ # Might need to be changed depending on browser changes 
            "div[jsname='YJMvMc']"  # Google's CAPTCHA container
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
    current_url = driver.current_url
    if "google.com" not in current_url:
        driver.get(f"https://www.google.com/search?q={query.replace(' ', '+')}&hl=en")
        random_delay(2, 4)
        accept_cookies()
    #accept_cookies()
    
    if check_for_captcha(): 
        manual_captcha_handler()
    
    accept_cookies()
    
    try:
        search_box = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.NAME, "q"))
        )
        search_box.clear()
        search_box.send_keys(query)
        random_delay(0.5, 1)
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
        
        if check_for_captcha(): 
            manual_captcha_handler()
        page_results = extract_results(driver, query, query_type, topic, results_page)
        all_results.extend(page_results)
        
        # Next page
        if results_page < pages:
            next_url = get_next_page_url(driver, results_page)
            if next_url:
                driver.get(next_url)
                time.sleep(4)
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
        max_queries=10000 # For testing
    )
    
