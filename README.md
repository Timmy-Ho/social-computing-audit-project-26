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

We compiled **362 topics** across controversial scientific and social issues. Each topic includes: 

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
- Manual CAPTCHA solving since Google keeps track of IPs (Free Proxies get reliably detected)

**Dataset Summary:**
| Metric | Count |
|--------|-------|
| Total queries executed | 724 (362 topics × 2 types) |
| Total results collected | 10292 |
| Classified results | 5746 (55.8%) |
| Unknown/unclassified | 4546 (44.2%) |

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
| MBFC Dataset | Media bias ratings compiled by a project from the idiap research institute | ~4500 domains | [GitHub](https://github.com/idiap/News-Media-Reliability) |
| OpenSources | Curated list of fake news, satire, and unreliable sources | ~1000 domains | [GitHub](https://github.com/BigMcLargeHuge/opensources) |

**Classification Categories:**

| Category | Definition | Count | Percentage |
|----------|------------|-------|------------|
| **Reliable** | Established news organizations, academic institutions, government agencies | 2669 | 25.9% |
| **Mixed** | Sources with factual reporting but also opinion/editorial content | 2171 | 21.1% |
| **Unreliable** | Known fake news, propaganda, pseudoscience, conspiracy sites | 4546 | 44.2% |


### 4. Data Analysis

**Statistical Methods:**
- **Chi-square test** - Assess independence between query type and credibility category
- **Descriptive statistics** - Percentage calculations for distributions
- **Median position comparison** - Compare ranking of results

## Results

### Q1: Credibility Distribution by Query Type

| Credibility | Neutral | Slanted | Difference (Neutral - Slanted) |
|-------------|---------|---------|-------------------------------|
| Reliable | 25.2% (1,308) | 26.7% (1,361) | -1.5% |
| Mixed | 21.3% (1,106) | 20.9% (1,065) | +0.4% |
| Unreliable | 7.7% (402) | 9.9% (504) | -2.2% |
| Unknown | 45.8% (2,376) | 42.5% (2,170) | +3.3% |

**Key Finding:** Slanted queries return **2.2% more unreliable sources** than neutral queries, while neutral queries return **1.5% more reliable sources**. This suggests that query phrasing affects credibility distribution.

### Q2: Top Unreliable Domains

**Key Finding:** Generally, the same unreliable domains appear in both query types, but with higher frequency in slanted queries:

| Domain | Neutral | Slanted | Difference |
|--------|---------|---------|------------|
| reddit.com | 98 | 136 | +38 |
| quora.com | 19 | 46 | +27 |
| sciencedirect.com | 149 | 141 | -8 |

*Note: `sciencedirect.com` appears more in neutral queries, while user-generated content platforms (Reddit, Quora) appear significantly more in slanted queries.*

### Q3: Ranking Position of Unreliable Results

| Metric | Neutral | Slanted |
|--------|---------|---------|
| Mean position | 5.39 | 5.51 |
| Median position | **5.0** | **6.0** |
| Standard deviation | 2.67 | 2.80 |

**Key Finding:** Contrary to our hypothesis, unreliable results rank **higher (better position) in neutral queries** (median position 5) than in slanted queries (median position 6). 

- Levene's test for equal variances: p = 0.215 → no significant difference in spread
- The difference represents a true median shift, not increased variability

**Interpretation:** Google does not push unreliable results higher when users search with biased phrasing. In fact, unreliable sources appear slightly deeper in slanted query results.

### Q4: Most Vulnerable Topics

**Topics with Highest % Unreliable Results in Slanted Queries:**

| Topic | Unreliable % |
|-------|---------------|
| overfishing | 33.3% |
| autonomous_vehicles | 31.4% |
| plastic | 29.8% |
| organic_food | 29.0% |
| wind_energy | 28.9% |

**Topics with Highest % Unreliable Results in Neutral Queries:**

| Topic | Unreliable % |
|-------|---------------|
| mining | 35.0% |
| coal | 27.8% |
| 3d_printing | 27.5% |
| autonomous_vehicles | 25.6% |
| nanotechnology | 25.6% |

**Key Finding:** `overfishing` shows 33.3% unreliable results in slanted queries but was not covered in neutral queries. Topics like `blockchain`, `nanotechnology`, and `autonomous_vehicles` appear in both lists, suggesting technology topics are particularly vulnerable to misinformation regardless of query phrasing.

### Statistical Significance

| Test | Value |
|------|-------|
| Chi-square (χ²) | 21.82 |
| Degrees of freedom | 3 |
| p-value | **7.10 × 10⁻⁵** |

**Conclusion:** The association between query type and credibility is **statistically significant** (p < 0.001). The difference in credibility distribution between neutral and slanted queries is not due to random chance.

## Discussion

### Summary of Findings

1. **Slanted queries produce more unreliable results** (+2.2%) and fewer reliable results (-1.5%) than neutral queries (Q1)
2. **The same unreliable domains appear** in both query types, but user-generated content (Reddit, Quora) is more prevalent in slanted queries (Q2)
3. **Unreliable results rank higher in neutral queries** (median position 5) than in slanted queries (median position 6) – Google seems to put reliable sources higher with slanted queries (Q3)
4. **Technology topics** (blockchain, nanotechnology, autonomous vehicles) show high vulnerability to misinformation across both query types (Q4)

### Limitations

| Limitation | Description |
|------------|-------------|
| **Search personalization** | Results vary by location, search history, and user behavior – not controlled (used Selenium as a new user) |
| **Temporal effects** | Search results change over time as Google updates algorithms |
| **Classification subjectivity** | Source credibility is context-dependent and debated |
| **Incomplete results** | Manual CAPTCHA solving may have led to incomplete data for some queries |
| **Unknown sources** | 44.2% of results could not be classified, limiting analysis scope |
| **Single search engine** | Results may not generalize to Bing, DuckDuckGo, etc. |
| **English only** | Findings may not apply to other languages |

### Future Work

- Test other search engines (Bing, DuckDuckGo, Brave)
- Analyze temporal trends in credibility over time
- Reduce unknown classification rate with additional credibility databases
- Investigate why unreliable results rank higher in neutral queries (Q3 finding)

## Repository Structure

```
main/
├── data/
│   ├── mbfc.csv # Credibility domains from mbfc
│   ├── queries.csv # List of all search queries (topic, neutral, slanted)
│   ├── raw_opensources.csv # Credibility domains from opensources
|   ├── raw_results.csv # Scraped search results from Google
│   └── raw_wikipedia_perennial_sources.csv # Wikipedia Perennial Sources of credibility 
├── results/
│   ├── figures/ # Plots and charts
│   └── ... # Processed data and remaining data
└── src/
│   ├── analysis.py # Credibility Classifier
│   ├── data_analysis.py # Visualizations and statistical analysis
│   ├── opensources_classifier.py # Credibility Classifier for opensources
│   ├── scraper.py # Google search engine scraper
│   └── wikipedia_scraper.py # Wikipedia perennial sources scraper
├── README.md
├── requirements.txt # Dependencies
├── .gitignore
```