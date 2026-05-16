import requests
from bs4 import BeautifulSoup
import re
import time
import pandas as pd
from urllib.parse import urlparse
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

API_URL = "https://en.wikipedia.org/w/api.php" # Using MediaAPI from Wikipedia
BASE_PAGE = "Wikipedia:Reliable_sources/Perennial_sources"

HEADERS = {
    'User-Agent': 'SocialComputingAuditProject/1.0 (timmyho2003@hotmail.com) Python/3.12 requests' # To be inserted with own User Agent
}

# Cache for domain lookups to avoid repeated requests
DOMAIN_CACHE = {}

# Create a session with retries
session = requests.Session()
retry_strategy = Retry(
    total=3,
    backoff_factor=2,  # Wait between retries
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=["GET"]
)
adapter = HTTPAdapter(max_retries=retry_strategy, pool_connections=10, pool_maxsize=10)
session.mount('http://', adapter)
session.mount('https://', adapter)

def get_page_html(page_title):
    params = {
        'action': 'parse',
        'page': page_title,
        'format': 'json',
        'prop': 'text',
        'redirects': '1'
    }
    resp = session.get(API_URL, params=params, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    return data['parse']['text']['*']

def extract_official_domains_from_wikipedia(source_page_title):
    if not source_page_title or source_page_title.startswith('/w/'):
        return []
    
    if source_page_title in DOMAIN_CACHE:
        return DOMAIN_CACHE[source_page_title]
    
    domains = []
    
    for attempt in range(3):
        try:
            params = {
                'action': 'parse',
                'page': source_page_title,
                'format': 'json',
                'prop': 'text',
                'redirects': '1'
            }
            resp = session.get(API_URL, params=params, headers=HEADERS, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            
            if 'parse' not in data:
                DOMAIN_CACHE[source_page_title] = []
                return []
                
            html = data['parse']['text']['*']
            soup = BeautifulSoup(html, 'html.parser')
            
            infobox = soup.find('table', class_='infobox')
            if not infobox:
                DOMAIN_CACHE[source_page_title] = []
                return []
            
            for row in infobox.find_all('tr'):
                header = row.find('th')
                if header and header.get_text():
                    header_text = header.get_text().strip().lower()
                    if 'website' in header_text or 'url' in header_text or 'official' in header_text or 'issn' in header_text:
                        data_cell = row.find('td', class_='infobox-data')
                        if not data_cell:
                            data_cell = row.find('td')
                        
                        if data_cell:
                            for link in data_cell.find_all('a', href=True):
                                link_text = link.get_text(strip=True)
                                if link_text:
                                    clean = link_text.lower().strip().rstrip('/')
                                    clean = re.sub(r'^https?://', '', clean)
                                    if clean and clean not in domains:
                                        domains.append(clean)
            
            DOMAIN_CACHE[source_page_title] = domains
            return domains
            
        except requests.exceptions.ConnectionError as e:
            print(f"      Connection error (attempt {attempt + 1}/3): {str(e)[:50]}")
            if attempt < 2:
                wait_time = (attempt + 1) * 5  
                print(f"      Waiting {wait_time} seconds")
                time.sleep(wait_time)
            else:
                DOMAIN_CACHE[source_page_title] = []
                return []
        except Exception as e:
            print(f"      Error: {type(e).__name__}")
            DOMAIN_CACHE[source_page_title] = []
            return []
    
    DOMAIN_CACHE[source_page_title] = []
    return []

def extract_status_from_cell(cell):
    spans = cell.find_all('span', attrs={'typeof': 'mw:File'})
    for span in spans:
        link = span.find('a')
        if link and link.get('title'):
            return link['title']
    
    links = cell.find_all('a')
    for link in links:
        title = link.get('title', '')
        if title and title not in ['stale discussions', 'edit', 'Discussion in progress']:
            return title
    
    return cell.get_text(strip=True)

def extract_status_icon(status_text):
    """Convert status text to simple classification"""
    status_lower = status_text.lower()
    if 'generally reliable' in status_lower:
        return 'reliable'
    elif 'deprecated' in status_lower or 'blacklisted' in status_lower:
        return 'deprecated'
    elif 'generally unreliable' in status_lower:
        return 'unreliable'
    elif 'no consensus' in status_lower or 'additional considerations' in status_lower:
        return 'mixed'
    else:
        return 'unknown'

def clean_source_name(source_text):
    """Remove shortcuts and extra annotations from source name"""
    clean = re.sub(r'WP:\S+', '', source_text)
    clean = re.sub(r'📌', '', clean)
    clean = re.sub(r'\s+', ' ', clean).strip()
    return clean if clean else source_text

def get_source_wikipedia_title(source_cell):
    link = source_cell.find('a')
    if link and link.get('href'):
        href = link['href']
        if href.startswith('/wiki/'):
            return href.replace('/wiki/', '')
    return None

def extract_summary_from_cell(cell):
    """Extract the summary text"""
    text = cell.get_text(strip=True)
    lines = text.split('\n')
    filtered_lines = []
    for line in lines:
        line = line.strip()
        if line and not re.match(r'^\d{4}$', line):
            filtered_lines.append(line)
    
    text = ' '.join(filtered_lines)
    text = re.sub(r'\s+', ' ', text).strip()
    
    if not text or len(text) < 10:
        paragraphs = cell.find_all('p')
        if paragraphs:
            text = paragraphs[-1].get_text(strip=True)
    
    return text[:1000] if text else ''

def parse_table(table, skip_domain_lookup=False):
    sources = []
    rows = table.find_all('tr')
    total_rows = len(rows[1:])
    
    for idx, row in enumerate(rows[1:]):
        cells = row.find_all('td')
        if len(cells) >= 5:
            source_cell = cells[0]
            source_name = clean_source_name(source_cell.get_text(strip=True))
            wiki_title = get_source_wikipedia_title(source_cell)
            
            status_cell = cells[1]
            status_text = extract_status_from_cell(status_cell)
            status = extract_status_icon(status_text)
            
            summary_cell = cells[4]
            summary = extract_summary_from_cell(summary_cell)
            
            actual_domains = []
            if wiki_title and not skip_domain_lookup:
                print(f"  [{idx+1}/{total_rows}] Processing: {source_name[:40]}...")
                actual_domains = extract_official_domains_from_wikipedia(wiki_title)
                if actual_domains:
                    print(f"     Found: {', '.join(actual_domains)}")
                
                time.sleep(2)  

            sources.append({
                'source': source_name,
                'wikipedia_page': wiki_title,
                'domains': ';'.join(actual_domains) if actual_domains else '',
                'status': status,
                'status_raw': status_text,
                'summary': summary,
            })
    return sources

def get_continuation_subpages(html):
    """Extract links to subpages"""
    soup = BeautifulSoup(html, 'html.parser')
    subpage_titles = []
    for a in soup.find_all('a', href=True):
        href = a['href']
        match = re.search(r'/wiki/Wikipedia:Reliable_sources/Perennial_sources/(\d+)$', href)
        if match:
            title = href.replace('/wiki/', '')
            if title not in subpage_titles:
                subpage_titles.append(title)
    return subpage_titles

def scrape_all_perennial_sources(skip_domain_lookup=True):
    """
    Scrape all sources from main page and subpages.
    """
    main_html = get_page_html(BASE_PAGE)
    soup = BeautifulSoup(main_html, 'html.parser')
    
    main_table = soup.find('table', class_='wikitable')
    if not main_table:
        raise Exception("Main table not found on page.")
    
    all_sources = parse_table(main_table, skip_domain_lookup=skip_domain_lookup)
    
    subpage_titles = get_continuation_subpages(main_html)
    
    for title in subpage_titles:
        print(f"Fetching {title}...")
        sub_html = get_page_html(title)
        sub_soup = BeautifulSoup(sub_html, 'html.parser')
        sub_table = sub_soup.find('table', class_='wikitable')
        if sub_table:
            sources = parse_table(sub_table, skip_domain_lookup=skip_domain_lookup)
            all_sources.extend(sources)
            print(f"  Added {len(sources)} sources.")
        time.sleep(0.5)
    return all_sources

def save_to_csv(sources, output_file='./data/raw_wikipedia_perennial_sources.csv'):
    import os
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    df = pd.DataFrame(sources)
    df.to_csv(output_file, index=False, encoding='utf-8')
    print(f"\nSaved {len(df)} sources to {output_file}")
    return df

if __name__ == "__main__":
    # Set skip_domain_lookup=True for quick run (no domain fetching)
    # Set skip_domain_lookup=False to fetch domains
    sources = scrape_all_perennial_sources(skip_domain_lookup=False)
    print(f"\nTotal sources collected: {len(sources)}")
    
    df = save_to_csv(sources, './data/raw_wikipedia_perennial_sources.csv')
    
    print("\nStatus distribution:")
    print(df['status'].value_counts())