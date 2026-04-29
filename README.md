# Google Search Engine Credibility Audit

## Overview

This project aims to audit whether Google Search ranks credibility sources differently depending on how a scientific query is phrased. We compare **neutral** queries (e.g., "vaccine safety") with **slanted** queries (e.g., "vaccine dangers"). 

## Research Question


## Methodology

### 1. Query Design

We compiled a list of topics with search queries: 

| Topic | Neutral Query | Slanted Query |
|-------|---------------|---------------|
| Vaccines | `vaccine safety` | `vaccine dangers` |
| Climate change | `climate change evidence` | `climate change hoax` |

*Fully query list available in `data/queries.csv`*

### 2. Web Scraping
- **Tool:** Selenium with ChromeDriver
- ...

### 3. Credibility Classification

We use **free, publicly available** sources to identify credibility of domains:

| Source | Description | Link |
|--------|-------------|------|
| Wikipedia: Reliable Sources | ... | https://en.wikipedia.org/wiki/Wikipedia:Reliable_sources/Perennial_sources#Sources |
| MBFC Dataset | ... | https://github.com/ramybaly/Article-Bias-Prediction |
| OpenSources | ... | https://github.com/BigMcLargeHuge/opensources |

### Analysis Metrics

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