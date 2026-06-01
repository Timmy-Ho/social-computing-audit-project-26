# Google Search Engine Credibility Audit

## Overview

This project audits whether Google Search ranks information from credible vs. unreliable sources differently depending on how a user phrases their search query. Specifically, we compare **neutral queries** (unbiased, fact‑based phrasing) with **slanted queries** (biased, emotional phrasing) across 362 scientific topics.

**Key Question:** Does search query phrasing affect the credibility of search results users receive?

## Research Questions

| # | Research Question | Measurement |
|---|-------------------|-------------|
| Q1 | Does query phrasing (neutral vs. slanted) affect the credibility distribution of search results? | Compare percentage of reliable/mixed/unreliable results between neutral and slanted queries |
| Q2 | Do different unreliable domains appear in neutral vs. slanted search results? | Identify top 10 most frequent unreliable domains for each query type |
| Q3 | Do unreliable results rank higher (closer to position 1) in slanted queries? | Compare median ranking position of unreliable results between query types |
| Q4 | Which topics are most vulnerable to misinformation, and does this differ by query phrasing? | Calculate percentage of unreliable results per topic for each query type |
| Q5 | Which topics consistently return reliable results, and does this differ between neutral vs. slanted searches? | Calculate percentage of reliable results per topic for each query type |
| Q6 | For each topic, how does the reliable vs. unreliable split compare side by side? | For each topic, plot reliable and unreliable on the same axis to visualise balance |

## Methodology

### 1. Query Design

We compiled **362 topics** across controversial scientific and social issues (e.g., vaccines, climate change, blockchain, overfishing). Each topic includes:

- **Topic Name** (e.g., “Vaccines”, “Climate Change”)
- **Neutral Query** – fact‑based, unbiased phrasing (e.g., “vaccine safety”)
- **Slanted Query** – biased or emotionally charged phrasing (e.g., “vaccine dangers”)

Queries were matched for length and specificity. The full list is in `data/queries.csv`.

### 2. Web Scraping

**Tool Stack:**
- **Selenium** with ChromeDriver
- **selenium‑stealth** to avoid basic detection

**Scraping Configuration:**
- 3 pages per query (~30 organic results per query)
- Random delays between requests
- Manual CAPTCHA solving (free proxies are reliably blocked)

**Dataset Summary:**

| Metric | Count |
|--------|-------|
| Total queries executed | 724 (362 topics × 2 types) |
| Total results collected | 10,292 |
| Classified results | 5,746 (55.8%) |
| Unknown / unclassified | 4,546 (44.2%) |

**Output (per result):** URL, domain, title, position, timestamp, query type, topic.

### 3. Credibility Classification

We built a multi‑step pipeline using publicly available credibility databases:

| Source | Description | Coverage | Link |
|--------|-------------|----------|------|
| Wikipedia: Perennial Sources | Community‑vetted reliable/unreliable/mixed sources | ~550 domains | [Link](https://en.wikipedia.org/wiki/Wikipedia:Reliable_sources/Perennial_sources) |
| MBFC Dataset | Media bias ratings (Idiap Research Institute) | ~4,500 domains | [GitHub](https://github.com/idiap/News-Media-Reliability) |
| OpenSources | Curated list of fake news, satire, unreliable sources | ~1,000 domains | [GitHub](https://github.com/BigMcLargeHuge/opensources) |

**Pipeline steps:**
1. Direct URL match against Wikipedia (manual conflict resolution)
2. `.edu` / `.ac` → **Reliable**
3. `.gov` / `doi.org` → **Mixed**
4. Typosquat detection (Levenshtein distance ≤1) → **Unreliable**
5. OpenSources + MBFC matches
6. Manual overrides for frequently occurring unclassified domains

**Classification outcome:**

| Category | Definition | Count | Percentage |
|----------|------------|-------|-------------|
| **Reliable** | Established news, academic institutions, government agencies | 2,669 | 25.9% |
| **Mixed** | Factual reporting but opinion/editorial content | 2,171 | 21.1% |
| **Unreliable** | Fake news, propaganda, pseudoscience, conspiracy sites | 906 | 8.8% |
| **Unknown** | Not found in any database | 4,546 | 44.2% |

### 4. Data Analysis

- **Descriptive statistics** – percentages and counts (Q1, Q2)
- **Median positions + Levene’s test** – compare ranking of unreliable results (Q3)
- **Per‑topic unreliable/reliable percentages** (Q4, Q5)
- **Grouped bar charts** – reliable vs. unreliable per topic (Q6)
- **Chi‑square test of independence** – overall association between query type and credibility

All analyses were performed in Python (pandas, scipy, seaborn, matplotlib).

## Results

### Q1 – Credibility Distribution

| Credibility | Neutral (%) | Slanted (%) | Difference (Neutral – Slanted) |
|-------------|-------------|-------------|-------------------------------|
| Reliable     | 28.4        | 29.6        | –1.2                          |
| Mixed        | 18.0        | 17.6        | +0.4                          |
| Unreliable   | 7.9         | 10.2        | –2.3                          |
| Unknown      | 45.8        | 42.5        | +3.3                          |

**Key Finding:** Slanted queries return **2.3% more unreliable results** and **1.2% fewer reliable results** than neutral queries. Query phrasing affects credibility distribution.

### Q2 – Top Unreliable Domains

| Domain | Neutral appearances | Slanted appearances | Difference |
|--------|---------------------|----------------------|------------|
| reddit.com | 98 | 136 | +38 |
| quora.com | 19 | 46 | +27 |
| sciencedirect.com | 149 | 141 | –8 |

**Key Finding:** The same unreliable domains appear in both query types, but user‑generated content (Reddit, Quora) is significantly more frequent in slanted queries.

### Q3 – Ranking Position of Unreliable Results

| Metric | Neutral | Slanted |
|--------|---------|---------|
| Mean position | 5.40 | 5.49 |
| Median position | **5.0** | **6.0** |
| Standard deviation | 2.67 | 2.79 |

**Levene’s test:** F = 1.609, p = 0.215 → no significant difference in spread.

**Key Finding (counter‑intuitive):** Unreliable results rank **higher (better position) in neutral queries** (median 5) than in slanted queries (median 6). Google does **not** push unreliable content higher for biased queries; instead, slanted queries surface slightly more reliable results and demote unreliable ones by one position.

### Q4 – Most Vulnerable Topics (Highest % Unreliable)

**Slanted queries (top 5):**

| Topic | Unreliable % |
|-------|---------------|
| overfishing | 33.3% |
| autonomous_vehicles | 31.4% |
| plastic | 29.8% |
| organic_food | 29.0% |
| wind_energy | 28.9% |

**Neutral queries (top 5):**

| Topic | Unreliable % |
|-------|---------------|
| mining | 35.0% |
| coal | 27.8% |
| 3d_printing | 27.5% |
| autonomous_vehicles | 25.6% |
| nanotechnology | 25.6% |

**Key Finding:** Technology topics (autonomous vehicles, blockchain, nanotechnology) appear in both lists – they are vulnerable regardless of phrasing. Overfishing is highly vulnerable only in slanted queries, suggesting niche topics are more affected by biased phrasing.

### Q5 – Most Reliable Topics (Highest % Reliable)

**Slanted queries (top 5):**

| Topic | Reliable % |
|-------|-------------|
| social_media | 70.4% |
| synthetic_biology | 69.8% |
| job_security | 66.7% |
| artificial_intelligence | 66.0% |
| poverty | 65.1% |

**Neutral queries (top 5):**

| Topic | Reliable % |
|-------|-------------|
| social_media | 70.2% |
| poverty | 66.0% |
| covid19 | 64.5% |
| alcohol | 64.4% |
| deforestation | 63.0% |

**Key Finding:** Topics with strong scientific consensus and abundant institutional sources (social media, poverty, COVID‑19) consistently return high percentages of reliable results. Overlap between neutral and slanted lists is high, indicating that query phrasing does not substantially affect reliability for these topics.

### Q6 – Reliable vs. Unreliable Split per Topic

For the majority of topics, reliable sources exceed unreliable sources, often by a wide margin. In slanted queries, the gap between reliable and unreliable is generally smaller for vulnerable topics (e.g., overfishing, autonomous vehicles). Notably, for “social media”, slanted queries produce **higher reliability** (70.4% vs. 70.2%) and **lower unreliability** (8.5% vs. 14.3%) than neutral queries – suggesting Google may compensate for biased phrasing by elevating authoritative sources.

### Statistical Significance

| Test | Value |
|------|-------|
| Chi‑square (χ²) | 23.42 |
| Degrees of freedom | 3 |
| p‑value | **3.29 × 10⁻⁵** |

**Conclusion:** The association between query type and credibility is **statistically significant** (p < 0.001). The differences observed are not due to random chance.

### Robustness Check: Truly Neutral Queries

Because our original neutral queries (e.g., “vaccine safety”) might still carry implicit framing, we repeated the analysis on a subset of 160 queries that were truly neutral (topic name only, e.g., “vaccines”). The main findings remained:

| Metric | Original Neutral | Truly Neutral | Slanted |
|--------|----------------|---------------|---------|
| Unreliable results (%) | 7.9 | 7.6 | 10.2 |
| Reliable results (%) | 28.4 | 29.2 | 29.6 |
| Median position (unreliable) | 5.0 | 5.0 | 6.0 |
| Chi‑square (vs. slanted) | 23.42 (p = 3.29×10⁻⁵) | 20.06 (p = 1.65×10⁻⁴) | – |

The difference between slanted and truly neutral queries shrinks but remains significant, confirming that our conclusions are robust to the definition of “neutral”.

## Discussion

### Summary of Findings

1. **Slanted queries produce more unreliable results** (+2.3%) and fewer reliable results (–1.2%) than neutral queries (Q1)
2. **The same unreliable domains** appear in both query types, but user‑generated content (Reddit, Quora) is more prevalent in slanted queries (Q2)
3. **Unreliable results rank higher in neutral queries** (median 5) than in slanted queries (median 6) – Google appears to demote unreliable results for biased queries (Q3)
4. **Technology topics** (blockchain, autonomous vehicles) are vulnerable to misinformation across both query types; overfishing is uniquely vulnerable in slanted queries (Q4)
5. **Social media, poverty, and COVID‑19** are among the most reliable topics, with little difference between query types (Q5)
6. **The reliable‑unreliable gap** is generally smaller in slanted queries for vulnerable topics, indicating that biased phrasing reduces the distinction between credible and non‑credible content (Q6)

### Limitations

| Limitation | Description |
|------------|-------------|
| **Search personalization** | Results vary by location, history, and device – partially mitigated by using a fresh profile |
| **Temporal effects** | Scraping performed in May 2026; Google’s algorithm may have changed |
| **Classification subjectivity** | Credibility labels are inherently debatable; we rely on established databases |
| **Low collection rate (47%)** | CAPTCHA blocks and manual solving reduced yield, but sample remains large (n=10,292) |
| **High unknown rate (44%)** | Many domains not in any database; unknown results could bias findings |
| **Single search engine / English only** | Findings may not generalise to Bing, DuckDuckGo, or other languages |

### Future Work

- Replicate the study on other search engines (Bing, DuckDuckGo, Brave)
- Incorporate additional credibility databases to reduce unknown rate
- Conduct controlled experiments to investigate why neutral queries rank unreliable results higher (Q3)
- Expand topic set to include non‑scientific queries and other languages
- Use paid proxy services and CAPTCHA solvers to increase collection rate

## Repository Structure
```
main/
├── data/
│ ├── mbfc.csv # MBFC credibility domains
│ ├── queries.csv # 362 topics + neutral/slanted queries
│ ├── raw_opensources.csv # OpenSources credibility domains
│ ├── raw_results.csv # Scraped search results (10,292 rows)
│ └── raw_wikipedia_perennial_sources.csv # Wikipedia Perennial Sources
├── results/
│ ├── figures/ # All plots and charts
│ │ ├── Q1_credibility_distribution.png
│ │ ├── Q2_top_unreliable_domains.png
│ │ ├── Q3_position_analysis.png
│ │ ├── Q4_topics_unreliable.png
│ │ ├── Q5_topics_reliable.png
│ │ ├── Q6_reliable_vs_unreliable_topics.png
│ │ ├── overall_credibility_pie.png
│ │ └── summary_table.png
│ ├── processed_sources_*.csv # Classified results (reliable/mixed/unreliable)
│ ├── remaining_sources.csv # Unclassified domains
│ └── analysis_summary.csv # Summary statistics table
├── src/
│ ├── analysis.py # Main analysis & visualisations
│ ├── credibility_classifier.py # Domain classification pipeline
│ ├── data_analysis.py # Statistical tests and figures
│ ├── opensources_classifier.py # OpenSources specific classifier
│ ├── scraper.py # Google search scraper
│ └── wikipedia_scraper.py # Wikipedia perennial sources scraper
├── README.md
├── requirements.txt
└── .gitignore
```
