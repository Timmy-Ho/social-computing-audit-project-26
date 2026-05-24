import pandas as pd, re, os, requests
from urllib.parse import urlparse

os.makedirs("results", exist_ok=True)

OPENSOURCES_URL = "https://raw.githubusercontent.com/BigMcLargeHuge/opensources/master/sources/sources.csv"

OPENSOURCES_MAP = {
    "reliable": "reliable", "credible": "reliable", "pro-science": "reliable",
    "conspiracy": "unreliable", "fake news": "unreliable", "junk science": "unreliable",
    "hate": "unreliable", "unreliable": "unreliable",
    "bias": "mixed", "political": "mixed", "satire": "mixed", "clickbait": "mixed", "state": "mixed"
}

def get_domain(url):
    try:
        parsed = urlparse(str(url).strip())
        if not parsed.scheme:
            parsed = urlparse("https://" + str(url).strip())
        domain = parsed.netloc.lower()
        domain = re.sub(r"^www\.", "", domain)
        domain = domain.split(":")[0]
        return domain
    except Exception:
        return ""

def load_opensources():
    df = pd.read_csv(OPENSOURCES_URL, index_col=0)
    df.columns = df.columns.str.strip().str.lower()
    df = df.reset_index().rename(columns={"index": "domain"})
    df["domain"] = df["domain"].str.strip().str.lower().str.replace(r"^www\.", "", regex=True)
    df["status"] = df["type"].str.strip().str.lower().map(OPENSOURCES_MAP).fillna("mixed")
    return df[["domain", "type", "status"]].dropna(subset=["domain"])

def save_opensources_to_csv():
    df = load_opensources()
    df.to_csv("data/raw_opensources.csv", index=False)
    print(f"Saved {len(df)} OpenSources entries to data/raw_opensources.csv")
    return df

def match_and_remove(df, lookup, reason_fn, label):
    m = df.merge(lookup, on="domain", how="inner").copy()
    m["reason"] = m.apply(reason_fn, axis=1)
    
    status_counts = {"reliable": 0, "unreliable": 0, "mixed": 0}
    
    for status, g in m.groupby("status"):
        g.to_csv(f"results/processed_sources_{status}.csv", mode="a", header=False, index=False)
        status_counts[status] = len(g)
    
    total_urls = len(m)
    total_domains = m["domain"].nunique()
    print(f"{label}: {total_domains} domains matched, {total_urls} total URLs "
          f"({status_counts['reliable']} reliable, {status_counts['unreliable']} unreliable, {status_counts['mixed']} mixed)")
    
    return df[~df["domain"].isin(m["domain"])]

def run_opensources_classification():
    df = pd.read_csv("results/remaining_data.csv", parse_dates=["timestamp"])
    df["domain"] = df["url"].apply(get_domain)
    print(f"Loaded {len(df)} results")

    try:
        opensources_df = save_opensources_to_csv()
        df = match_and_remove(
            df,
            opensources_df,
            lambda r: f"domain {r['domain']} is '{r['type']}' per OpenSources",
            "OpenSources"
        )
    except Exception as e:
        print(f"OpenSources failed: {e}")

    remaining = df.groupby("domain").agg(domain_count=("url", "count"), urls=("url", ";".join)).reset_index()
    remaining.sort_values("domain_count", ascending=False).to_csv("results/remaining_sources.csv", index=False)
    print(f"Remaining unclassified: {remaining['domain_count'].sum()} URLs across {len(remaining)} domains")
    
    return df
