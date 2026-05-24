# Google Search Engine Credibility Audit

## Overview

This project audits whether Google Search ranks information from credible vs. unreliable sources differently depending on how a user phrases their search query. Specifically, we compare **neutral queries** (unbiased, fact-based phrasing) with **slanted queries** (biased, emotional phrasing) across controversial scientific topics.

**Key Question:** Does serach query phrasing affect the credibility of search results users receive?

## Research Question

| # | Research Question | Measurement |
|---|-------------------|-------------|
| Q1 | Does query phrasing (neutral vs. slanted) affect the credibility distribution of search results? | Compare percentage of reliable/mixed/unreliable results between neutral and slanted queries |
| Q2 | Do different unreliable domains appear in neutral vs. slanted search results? | Identify top 10 most frequent unreliable domains for each query type |
| Q3 | Do unreliable results rank higher (closer to position 1 of pages) in slanted queries? | Compare median ranking position of unreliable results between query types |
| Q4 | Which topics are most vulnerable to misinformation, and does this differ by query phrasing? | Calculate percentage of unreliable results per topic for each query type |

## Methodology

### 1. Query Design

We compiled 362 topics across controversial scientific and social issues. Each topic includes: 

- **Topic Name** (e.g., "Vaccines", "Climate Change")
- **Neutral Query** - Unbiased phrasing (e.g., "vaccine safety")
- **Slanted Query** - Biased phrasing (e.g., "vaccine dangers)

**Query Balance:** Neutral and slanted queries are matched for length and specificity to ensure fair comparison. 


| Topic | Neutral Query | Slanted Query |
|-------|---------------|---------------|
| Vaccines | `vaccine safety` | `vaccine dangers` |
| Climate change | `climate change evidence` | `climate change hoax` |
| COVID-19 | `covoid 19 treatment efficacy` | `covid 19 vaccine injury` |

*Fully query list available in `data/queries.csv`*

### 2. Web Scraping


**Tool Stack:**
- **Selenium** with ChromeDriver
- **selenium-stealth** to avoid detection better

**Scraping Configuration:**
- 3 pages per query (=30 results per query)
- Delays between page requests and different queries
- Manual CAPTCHA solving since Google keeps track of IPs (Free Proxies get mostly detected)

**Output:** For each result, we collect:
- URL and domain
- Title
- Position on search results page
- Timestamp
- Query type (neutral/slanted) and topic

### 3. Credibility Classification

We classify domains using **free, publicly available** credibility databases:

| Source | Description | Coverage | Link |
|--------|-------------|----------|------|
| Wikipedia: Perennial Sources | Community-vetted list of reliable/unreliable/mixed sources | ~550 domains | [Link](https://en.wikipedia.org/wiki/Wikipedia:Reliable_sources/Perennial_sources#Sources) |
| MBFC Dataset | Professional fact-checking organization ratings regarding bias | ~0 (Not Used => to be removed) | [GitHub](https://github.com/ramybaly/Article-Bias-Prediction) |
| OpenSources | Curated list of fake news, satire, and unreliable sources | ~1000 domains | [GitHub](https://github.com/BigMcLargeHuge/opensources) |

**Classification Categories:**

| Category | Definition |
|----------|------------|
| **Reliable** | Established news organizations, academic institutions, government agencies |
| **Mixed** | Sources with factual reporting but also opinion/editorial content |
| **Unreliable** | Known fake news, propaganda, pseudoscience, conspiracy sites |


### 4. Data Analysis

**Statistical Methods:**
- **Chi-square test** - Assess independence between query type and credibility category
- **Descriptive statistics** - Percentage calculations for distributions
- **Median position comparison** - Compare ranking of results

## Results

### Key Findings

...

## Repository Structure

```
main/
├── data/
│   ├── queries.csv # List of all search queries (topic, neutral, slanted)
|   ├── credibility_domains/ # Compiled lists from GitHub + Wikipedia
|   └── raw_results/ # Scraped search results
├── results/
│   ├── figures/ # Plots and charts
│   └── summary_stats.csv
└── src/
│   ├── analysis.py # Statistical analysis
│   ├── credibility_classifier.py # Domain matching against credibility lists
│   └── scraper.py # Scraping script
├── README.md
├── requirements.txt
├── .gitignore
```