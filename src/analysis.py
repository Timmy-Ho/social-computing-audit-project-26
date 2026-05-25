import pandas as pd
import re
from rapidfuzz.distance import Levenshtein
from opensources_classifier import run_opensources_classification


def load_data():
    df = pd.read_csv("data/raw_results.csv", parse_dates=["timestamp"])
    df_wiki = pd.read_csv("data/raw_wikipedia_perennial_sources.csv")
    print(df.shape)
    return df, df_wiki

def expand_wiki_domains(df_wiki):
    # Some site have more than one domain, in db they are in the same row
    df_wiki_expanded = df_wiki.assign(
        domain=df_wiki["domains"].str.split(";")
    ).explode("domain")
    return df_wiki_expanded

def override_conflicts(df_wiki_expanded):
    # Manual overrides for domains with conflicting statuses.
    domain_overrides = {
        "theguardian.com": "reliable", #blog is unreliable but there are no blog sources
        "telegraph.co.uk": "reliable", #only unreliable in trasgender topics which we don't have
        "foxnews.com": "unreliable", #mixed in some topic but mostly unreliable
        "forbes.com": "mixed", #depends on publish date of article
        "bloomberg.com": "reliable", #unreliable in article about companies profiles, which we don't have as a topic
        "nypost.com": "unreliable", #reliable on entertainment topics, which we don't care
        "cnet.com": "mixed", #depends on pubblishing date
        "www.adl.org": "mixed", #unreliable on israel topics, reliable otherwise
        "www.sixthtone.com": "mixed", #unreliable in politics, reliable otherwise
        "www.newsnationnow.com": "reliable", #unreliable in UFO, reliable otherwise, we have no UFO topics
    }

    df_wiki_expanded.loc[
        df_wiki_expanded["domain"].isin(domain_overrides), "status"
    ] = df_wiki_expanded.loc[
        df_wiki_expanded["domain"].isin(domain_overrides), "domain"
    ].map(domain_overrides)
    return df_wiki_expanded

def split_ambiguous(df, df_wiki_expanded):
    # Find domains that appear in more than one status
    domain_status_counts = df_wiki_expanded.groupby("domain")["status"].nunique()
    ambiguous_domains = domain_status_counts[domain_status_counts > 1].index

    # Split wiki into ambiguous and unambiguous
    df_wiki_ambiguous = df_wiki_expanded[df_wiki_expanded["domain"].isin(ambiguous_domains)]
    df_wiki_clear = df_wiki_expanded[~df_wiki_expanded["domain"].isin(ambiguous_domains)]

    # Match ambiguous domains to undefined
    undefined = df[df["domain"].isin(ambiguous_domains)].merge(
        df_wiki_ambiguous.drop_duplicates(subset="domain"), on="domain", how="left"
    )
    undefined["reason"] = undefined["domain"].apply(
        lambda d: f"domain {d} matches multiple entries with conflicting statuses in raw_wikipedia_perennial_sources.csv"
    )
    undefined.to_csv("results/processed_sources_undefined.csv", index=False)
    df = df[~df["domain"].isin(undefined["domain"])]
    print(f"Saved {len(undefined)} ambiguous rows to undefined") ##hopefully 0 if i ovveride all confusing sources
    return df, df_wiki_clear

def match_wiki_sources(df, df_wiki_clear):
    
    processed_sources = df.merge(df_wiki_clear.drop_duplicates(subset="domain"), on="domain", how="inner")

    ##Add reason 
    processed_sources["reason"] = processed_sources.apply(
        lambda row: f"domain {row['domain']} matches {row['status']} domain from file raw_wikipedia_perennial_sources.csv",
        axis=1
    )

    ##Remove matched rows from df
    df = df[~df["domain"].isin(processed_sources["domain"].unique())]

    ##split in 3 files reliable/unreliable/mixed
    for status, group in processed_sources.groupby("status"):
        filename = f"results/processed_sources_{status}.csv"
        group.to_csv(filename, index=False)
        print(f"Saved {len(group)} rows to {filename}")

    return df

def tag_academic(df):
    ## treat .edu and .ac domains as reliable 
    edu_ac = df[df["domain"].str.endswith((".edu", ".ac"))].copy()
    edu_ac["status"] = "reliable"
    edu_ac["reason"] = edu_ac["domain"].apply(
        lambda d: f"domain {d} has .edu or .ac, indicating an academic institution"
    )
    edu_ac.to_csv("results/processed_sources_reliable.csv", mode="a", header=False, index=False) 
    df = df[~df["domain"].str.endswith((".edu", ".ac"))]
    print(f"Added {len(edu_ac)} .edu/.ac rows to reliable")
    print(f"Remaining in df: {df.shape}")
    return df

def tag_gov_doi(df):
    ## treat .gov and doi.org domains as mixed
    mixed_mask = df["domain"].str.endswith(".gov") | df["url"].str.contains("doi.org", na=False)
    mixed = df[mixed_mask].copy()
    mixed["status"] = "mixed"
    mixed["reason"] = mixed.apply(
        lambda row: f"domain {row['domain']} contains .gov, which is mixed"
        if row["domain"].endswith(".gov")
        else f"url {row['url']} contains doi.org, which is mixed",
        axis=1
    )
    mixed.to_csv("results/processed_sources_mixed.csv", mode="a", header=False, index=False)
    df = df[~mixed_mask]
    print(f"Added {len(mixed)} .gov/doi rows to mixed")
    print(f"Remaining in df: {df.shape}")
    return df

def tag_typosquats(df, df_wiki_expanded):
    credible_domains = df_wiki_expanded[
        df_wiki_expanded["status"] == "reliable"
    ]["domain"].dropna().unique().tolist()

    def get_core(domain): ## gets the domain between www and .domain
        d = re.sub(r"^www\.", "", domain)
        core = d.rsplit(".", 1)[0]
        return core

    def get_typosquat_reason(domain, credible_domains, threshold=1):  ##get's ulr with the core of one edit distance from a rleiable source, but only if the core is at leas 5 char long (too short cores trigger the edit distance too easily)
        if len(get_core(domain)) < 5:
            return None, None
        for credible in credible_domains:
            dist = Levenshtein.distance(domain, credible)
            if domain != credible and dist <= threshold:
                return credible, dist
        return None, None

    reasons = []
    mask = []
    for domain in df["domain"]:
        credible, dist = get_typosquat_reason(domain, credible_domains)
        if credible:
            mask.append(True)
            reasons.append(f"domain {domain} differs by {dist} character(s) from trusted source: {credible}, indicating it is untrusted")
        else:
            mask.append(False)
            reasons.append(None)

    mask = pd.Series(mask, index=df.index)
    typosquats = df[mask].copy()
    typosquats["status"] = "unreliable"
    typosquats["reason"] = [r for r, m in zip(reasons, mask) if m]
    typosquats.to_csv("results/processed_sources_unreliable.csv", mode="a", header=False, index=False)
    df = df[~mask]
    print(f"Found {len(typosquats)} typosquat domains")
    print(f"Remaining in df: {df.shape}")
    return df

def save_remaining(df):
    remaining_grouped = df.groupby("domain").agg(
        domain_count=("url", "count"),
        urls=("url", lambda x: ";".join(x)),
    ).reset_index()

    remaining_grouped = remaining_grouped.sort_values("domain_count", ascending=False)
    remaining_grouped.to_csv("results/remaining_sources.csv", index=False)
    print(f"Saved {len(remaining_grouped)} unique domains to remaining_sources.csv")
    print(remaining_grouped[["domain", "domain_count"]].head(10))
    df.to_csv("results/remaining_data.csv", index=False)


def add_manual_sources(df, manual_sources: dict):
    counts = {"reliable": 0, "unreliable": 0, "mixed": 0}
    url_counts = {"reliable": 0, "unreliable": 0, "mixed": 0}
    matched_indices = []

    for domain, status in manual_sources.items():
        domain_rows = df[df["domain"] == domain].copy()
        if not domain_rows.empty:
            domain_rows["status"] = status
            domain_rows["reason"] = f"domain {domain} manually labeled as {status}"
            filename = f"results/processed_sources_{status}.csv"
            domain_rows.to_csv(filename, mode="a", header=False, index=False)
            counts[status] += 1
            url_counts[status] += len(domain_rows)
            matched_indices.extend(domain_rows.index.tolist())

    df = df.drop(index=matched_indices)

    total = sum(counts.values())
    total_urls = sum(url_counts.values())
    print(f"Manual sources added: {total} total domains, {total_urls} total URLs ({counts['reliable']} reliable domains, {url_counts['reliable']} URLs, {counts['unreliable']} unreliable domains, {url_counts['unreliable']} URLs, {counts['mixed']} mixed domains, {url_counts['mixed']} URLs)")
    
    return df


manual_sources = {
    "en.wikipedia.org": "reliable", 
    "researchgate.net": "mixed", #Generally reliable but it can have low quality draft or research papers
    "nature.com": "reliable",  
    "who.int": "reliable",  #whord health organisazion, very reliable
    "link.springer.com": "reliable", #Reliable academic pubblisher
    "healthline.com": "mixed",  #In general reliale but is made for consumers, oversimplification, sensasionalization
    "frontiersin.org": "mixed", #generally good but it has a lower editorial standards
    "canada.ca": "mixed",  #generally good but it is a GOV site
    "webmd.com": "reliable",  #It is consumer faced and it often only explain surface level, but it is reliable 
    "mayoclinic.org": "reliable", #Very respeted medical institution
    "nhs.uk": "mixed",  #Government site
    "gov.uk": "mixed",  #Government site
    "science.org": "reliable",  
    "health.clevelandclinic.org": "reliable", #Site of prestigious cliveland clininc, fact and sience base article reviewd by their own doctors 
    "academic.oup.com": "reliable",  #oxford university press 
    "medicalnewstoday.com": "mixed",  #Generally reliabile but not high editorial standars
    "onlinelibrary.wiley.com": "reliable",  #reliable academic pubblisher
    "britannica.com": "reliable",  #It summorizes information (not good for primary academic source) but factually correct
    "ebsco.com": "reliable",  # Major academic database aggregating peer reviewed research across disciplines
    "tandfonline.com": "reliable",  # Taylor and Francis academic publisher with peer reviewed journals
    "scientificamerican.com": "reliable",  # Long standing science journalism outlet with expert authors and editorial review
    "ibm.com": "mixed",  # Tech company site; strong on its own products/research but commercially motivated
    "hopkinsmedicine.org": "reliable",  # Johns Hopkins Medicine, highly prestigious medical institution with expert reviewed content
    "cancer.org": "reliable",  # American Cancer Society, authoritative health organization with evidence based content
    "goodrx.com": "mixed",  # Consumer facing health/pharmacy site; generally accurate but simplified and commercially motivated
    "ourworldindata.org": "reliable",  # Oxford affiliated data journalism with transparent sourcing and rigorous methodology
    "thelancet.com": "reliable",  # One of the world's top peer reviewed medical journals
    "arxiv.org": "mixed",  # Open access preprint server; not peer reviewed, but widely used in academia, quality varies
    "oecd.org": "reliable",  # Intergovernmental economic organization; authoritative policy and statistical data
    "bbc.co.uk": "mixed",  # Reputable public broadcaster; reliable for news but not a primary scientific source
    "betterhealth.vic.gov.au": "mixed",  # Australian government health site; generally reliable but government produced
    "europarl.europa.eu": "mixed",  # European Parliament official site; authoritative for EU policy but institutionally biased
    "jamanetwork.com": "reliable",  # JAMA Network, peer reviewed medical journals from the American Medical Association
    "heart.org": "reliable",  # American Heart Association, authoritative cardiovascular health organization
    "pnas.org": "reliable",  # Proceedings of the National Academy of Sciences, highly reputable peer reviewed journal
    "my.clevelandclinic.org": "reliable",  # Cleveland Clinic patient facing content, medically reviewed by their clinicians
    "bhf.org.uk": "reliable",  # British Heart Foundation, authoritative UK cardiovascular health charity
    "ec.europa.eu": "mixed",  # European Commission official site; authoritative for EU policy but institutionally produced
    "health.com": "mixed",  # Consumer health media brand; generally accurate but prone to oversimplification and sensationalism
    "efsa.europa.eu": "reliable",  # European Food Safety Authority, EU's official independent scientific risk assessment body
    "un.org": "mixed",  # United Nations; authoritative on policy and statistics but broad mandate and institutional framing
    "weforum.org": "mixed",  # World Economic Forum; influential but reflects elite/corporate perspectives
    "bmj.com": "reliable",  # British Medical Journal, top tier peer reviewed medical journal
    "ewg.org": "mixed",  # Environmental Working Group; advocacy organization with real research but a clear environmental agenda
    "world-nuclear.org": "mixed",  # World Nuclear Association; industry affiliated, so pro nuclear bias on policy questions
    "journals.sagepub.com": "reliable",  # SAGE academic publisher with peer reviewed journals across social and health sciences
    "healthychildren.org": "reliable",  # American Academy of Pediatrics official site; authoritative pediatric health guidance
    "ieeexplore.ieee.org": "reliable",  # IEEE digital library; peer reviewed engineering and computer science publications
    "news-medical.net": "mixed",  # Medical news aggregator; covers real research but variable editorial standards
    "nrdc.org": "mixed",  # Natural Resources Defense Council; environmental advocacy organization with real research but clear agenda
    "earth.org": "mixed",  # Environmental media outlet; covers real issues but advocacy oriented framing
    "pubs.acs.org": "reliable",  # American Chemical Society publications; peer reviewed chemistry and materials science journals
    "ama-assn.org": "reliable",  # American Medical Association; authoritative US medical professional organization
    "healthdirect.gov.au": "mixed",  # Australian government health information service; reliable but government produced
    "unep.org": "mixed",  # UN Environment Programme; authoritative on environmental policy but institutional framing
    "fao.org": "reliable",  # UN Food and Agriculture Organization; authoritative global food and agriculture data
    "ehtrust.org": "unreliable",  # Environmental Health Trust; advocacy group that often overstates EMF risks beyond scientific agreement
    "verywellhealth.com": "mixed",  # Consumer health site; generally accurate but simplified and ad supported
    "ucs.org": "mixed",  # Union of Concerned Scientists; science based advocacy with environmental/progressive agenda
    "nejm.org": "reliable",  # New England Journal of Medicine, one of the most prestigious peer reviewed medical journals
    "deloitte.com": "mixed",  # Big consulting firm; professionally produced reports but commercially motivated
    "gavi.org": "reliable",  # Vaccine alliance backed by WHO/UNICEF/World Bank; authoritative on global immunization
    "cambridge.org": "reliable",  # Cambridge University Press; prestigious academic publisher with peer reviewed content
    "swissinfo.ch": "mixed",  # Swiss public broadcaster (SRG SSR); reliable journalism but not a primary scientific source
    "iaea.org": "reliable",  # International Atomic Energy Agency; UN affiliated authoritative body on nuclear science and safety
    "cnn.com": "mixed",  # Major news network; reliable for breaking news but known for sensationalism and simplified science coverage
    "nationalgeographic.com": "mixed",  # Reputable science and nature journalism but consumer oriented and occasionally oversimplified
    "papers.ssrn.com": "mixed",  # Social science preprint server; not peer reviewed, quality varies widely
    "arpansa.gov.au": "reliable",  # Australian Radiation Protection and Nuclear Safety Agency; authoritative government scientific body
    "cancer.org.au": "reliable",  # Cancer Council Australia; authoritative national cancer organization with evidence based content
    "cfs.gov.hk": "mixed",  # Hong Kong Centre for Food Safety; government food safety authority, reliable but government produced
    "cancerresearchuk.org": "reliable",  # Cancer Research UK; leading cancer charity with rigorous evidence based content
    "centerforfoodsafety.org": "mixed",  # Advocacy organization; raises real food safety concerns but has a clear anti GMO/biotech agenda
    "eatingwell.com": "mixed",  # Consumer nutrition media; generally accurate but lifestyle oriented and ad supported
    "fortinet.com": "mixed",  # Cybersecurity company; credible on security topics but commercially motivated
    "mdanderson.org": "reliable",  # MD Anderson Cancer Center, one of the world's top cancer institutions with expert reviewed content
    "foodstandards.gov.au": "reliable",  # Food Standards Australia New Zealand; official government food safety regulatory authority
    "dw.com": "mixed",  # Deutsche Welle, German public international broadcaster; reliable journalism but not a primary scientific source
    "synthego.com": "mixed",  # Biotech company site; informative on CRISPR/gene editing but commercially motivated
    "everydayhealth.com": "mixed",  # Consumer health media; generally reliable but simplified and ad supported
    "research.google": "mixed",  # Google Research; credible technical output but from a major tech company with commercial interests
    "thequantuminsider.com": "mixed",  # Quantum computing news outlet; covers the field but editorial standards unclear and not peer reviewed
    "bfs.admin.ch": "mixed",  # Swiss Federal Statistical Office; authoritative Swiss government statistics
    "paloaltonetworks.com": "mixed",  # Cybersecurity company; credible on security topics but commercially motivated
    "abc.net.au": "mixed",  # Australian Broadcasting Corporation; reputable public broadcaster but not a primary scientific source
    "itu.int": "reliable",  # UN International Telecommunication Union; authoritative intergovernmental body on telecoms standards
    "longdom.org": "unreliable",  # Predatory/low quality open access publisher with minimal peer review standards
    "statista.com": "mixed",  # Data aggregation platform; convenient but secondary source that compiles others' data
    "pcrm.org": "mixed",  # Physicians Committee for Responsible Medicine; advocacy group with pro vegan bias despite medical framing
    "food.gov.uk": "reliable",  # UK Food Standards Agency; official government food safety regulatory authority
    "dl.acm.org": "reliable",  # ACM Digital Library; peer reviewed computer science publications from a major professional association
    "eufic.org": "mixed",  # European Food Information Council; industry funded food information body, generally accurate but potential bias
    "ahajournals.org": "reliable",  # American Heart Association journals; peer reviewed cardiovascular research publications
    "intechopen.com": "mixed",  # Open access book publisher; peer review quality is inconsistent and lower than top journals
    "iaomt.org": "unreliable",  # International Academy of Oral Medicine and Toxicology; anti amalgam advocacy group, not mainstream science
    "rand.org": "reliable",  # RAND Corporation; respected nonpartisan policy research institution with rigorous methodology
    "ideas.repec.org": "mixed",  # Economics research aggregator/preprint repository; quality varies, not all content is peer reviewed
    "aap.org": "reliable",  # American Academy of Pediatrics; authoritative US pediatric medicine professional organization
    "www2.hse.ie": "mixed",  # Ireland's Health Service Executive; reliable government health guidance but institutionally produced
    "cato.org": "mixed",  # Cato Institute; libertarian think tank with real research but a clear ideological agenda
    "fsai.ie": "reliable",  # Food Safety Authority of Ireland; official government food safety regulatory body
    "oecd-nea.org": "reliable",  # OECD Nuclear Energy Agency; authoritative intergovernmental body on nuclear energy data
    "food.ec.europa.eu": "reliable",  # European Commission food safety portal; EU official regulatory authority on food
    "nber.org": "reliable",  # National Bureau of Economic Research; highly reputable economics research organization
    "draxe.com": "unreliable",  # Dr. Axe health website; known for promoting pseudoscience, supplements, and unsubstantiated health claims
    "greenpeace.org": "mixed",  # Major environmental advocacy organization; raises real issues but has a clear activist agenda
    "jstor.org": "reliable",  # Digital library of academic journals; peer reviewed content across disciplines
    "mayoclinichealthsystem.org": "reliable",  # Mayo Clinic Health System; affiliated with the prestigious Mayo Clinic, medically reviewed content
    "mcgill.ca": "reliable",  # McGill University; reputable research university with evidence based science communication
    "ukri.org": "reliable",  # UK Research and Innovation; UK government's major public research funding body

}

def match_mbfc(df):
    cred = pd.read_csv("data/mbfc.csv")
    cred["domain"] = cred["source"].str.strip().str.lower().str.replace(r"^www\.", "", regex=True)
    cred = cred.rename(columns={"nela_gt_label": "status"})
    
    lookup = cred[["domain", "status", "mbfc_credibility_rating"]].drop_duplicates(subset="domain")
    
    m = df.merge(lookup, on="domain", how="inner").copy()
    m["reason"] = m.apply(
        lambda r: f"domain {r['domain']} rated '{r['mbfc_credibility_rating']}' per MBFC",
        axis=1
    )
    m = m.drop(columns=["mbfc_credibility_rating"])
    
    status_counts = {"reliable": 0, "unreliable": 0, "mixed": 0}
    url_counts = {"reliable": 0, "unreliable": 0, "mixed": 0}
    
    for status, g in m.groupby("status"):
        g.to_csv(f"results/processed_sources_{status}.csv", mode="a", header=False, index=False)
        status_counts[status] = g["domain"].nunique()
        url_counts[status] = len(g)
    
    df = df[~df["domain"].isin(m["domain"])]
    
    total_domains = m["domain"].nunique()
    total_urls = len(m)
    print(f"MBFC: {total_domains} domains matched, {total_urls} total URLs "
          f"({status_counts['reliable']} reliable domains/{url_counts['reliable']} URLs, "
          f"{status_counts['unreliable']} unreliable domains/{url_counts['unreliable']} URLs, "
          f"{status_counts['mixed']} mixed domains/{url_counts['mixed']} URLs)")
    
    return df

def check_duplicate_urls():
    files = {
        "reliable": pd.read_csv("results/processed_sources_reliable.csv"),
        "unreliable": pd.read_csv("results/processed_sources_unreliable.csv"),
        "mixed": pd.read_csv("results/processed_sources_mixed.csv"),
        "undefined": pd.read_csv("results/processed_sources_undefined.csv"),
        "remaining": pd.read_csv("results/remaining_data.csv"),
    }

    found_duplicates = False
    file_names = list(files.keys())

    for i in range(len(file_names)):
        for j in range(i + 1, len(file_names)):
            name_a = file_names[i]
            name_b = file_names[j]
            urls_a = set(files[name_a]["url"])
            urls_b = set(files[name_b]["url"])
            overlap = urls_a & urls_b
            if overlap:
                found_duplicates = True
                print(f"DUPLICATE: {name_a} and {name_b} share {len(overlap)} URLs")
                for url in list(overlap)[:5]:
                    print(f"  - {url}")
                if len(overlap) > 5:
                    print(f"  ... and {len(overlap) - 5} more")

    if not found_duplicates:
        print("No duplicate URLs found across any files.")


df, df_wiki = load_data()
df_wiki_expanded = expand_wiki_domains(df_wiki)
df_wiki_expanded = override_conflicts(df_wiki_expanded)
df, df_wiki_clear = split_ambiguous(df, df_wiki_expanded)
df = match_wiki_sources(df, df_wiki_clear)
df = tag_academic(df)
df = tag_gov_doi(df)
df = tag_typosquats(df, df_wiki_expanded)
save_remaining(df)


check_duplicate_urls()
df = run_opensources_classification()
save_remaining(df)
df = match_mbfc(df)
save_remaining(df)
df = add_manual_sources(df, manual_sources)
save_remaining(df)


