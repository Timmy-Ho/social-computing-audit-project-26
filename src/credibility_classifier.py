import pandas as pd, re, os, requests
from urllib.parse import urlparse
from rapidfuzz.distance import Levenshtein

os.makedirs("results", exist_ok=True)

OPENSOURCES_URL = "https://raw.githubusercontent.com/BigMcLargeHuge/opensources/master/sources/sources.csv"
MBFC_URL        = "https://api.github.com/repos/ramybaly/Article-Bias-Prediction/contents/data/jsons"

OPENSOURCES_MAP = {"reliable":"reliable","credible":"reliable","pro-science":"reliable",
                   "conspiracy":"unreliable","fake news":"unreliable","junk science":"unreliable",
                   "hate":"unreliable","unreliable":"unreliable","bias":"mixed","political":"mixed",
                   "satire":"mixed","clickbait":"mixed","state":"mixed"}
MBFC_MAP = {
    "left":         "mixed",
    "left-center":  "mixed",
    "center":       "reliable",
    "right-center": "mixed",
    "right":        "mixed",
}

WIKI_OVERRIDES = {
    # Manually force a status for specific domains if needed, e.g.:
    # "infowars.com": "unreliable",
    # "reuters.com":  "reliable",
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
    df = pd.read_csv(OPENSOURCES_URL, index_col=0)  # first col is the domain (unnamed index)
    df.columns = df.columns.str.strip().str.lower()
    df = df.reset_index().rename(columns={"index": "domain"})
    df["domain"] = df["domain"].str.strip().str.lower().str.replace(r"^www\.", "", regex=True)
    df["status"] = df["type"].str.strip().str.lower().map(OPENSOURCES_MAP).fillna("mixed")
    return df[["domain", "type", "status"]].dropna(subset=["domain"])

def load_mbfc():
    import glob, json
    from pathlib import Path

    # Always resolve relative to this script's location
    script_dir = Path(__file__).parent.parent  # goes up from src/ to project root
    jsons_path = script_dir / "data" / "mbfc_repo" / "data" / "jsons"

    files = list(jsons_path.glob("*.json"))
    print(f"MBFC: found {len(files)} files at {jsons_path}")

    if not files:
        print(f"MBFC: path does not exist or is empty — run:")
        print(f"  git clone --depth=1 https://github.com/ramybaly/Article-Bias-Prediction.git {jsons_path.parent.parent}")
        return pd.DataFrame(columns=["domain", "type", "status"])

    rows = []
    for path in files:
        with open(path, encoding="utf-8") as fh:
            try:
                data = json.load(fh)
            except Exception:
                continue
        if isinstance(data, dict):
            data = [data]
        for item in data:
            raw = str(item.get("source_url") or "").strip().lower()
            raw = re.sub(r"^https?://", "", raw)
            raw = re.sub(r"^www\.", "", raw).rstrip("/")
            bias = str(item.get("bias_text") or "").strip().lower()
            if raw:
                rows.append({"domain": raw, "type": bias, "status": MBFC_MAP.get(bias, "mixed")})

    if not rows:
        print("MBFC: files found but no rows extracted — check JSON field names")
        return pd.DataFrame(columns=["domain", "type", "status"])

    df = pd.DataFrame(rows)
    df = df[df["domain"].str.len() > 0]
    return (df.groupby("domain")
              .agg(status=("status", lambda s: s.value_counts().idxmax()),
                   type=("type", "first"))
              .reset_index())


def match_and_remove(df, lookup, reason_fn, label):
    m = df.merge(lookup, on="domain", how="inner").copy()
    m["reason"] = m.apply(reason_fn, axis=1)
    for status, g in m.groupby("status"):
        g.to_csv(f"results/processed_sources_{status}.csv", mode="a", header=False, index=False)
    print(f"{label}: matched {len(m)} rows — {df['domain'].nunique() - m['domain'].nunique()} new domains classified")
    return df[~df["domain"].isin(m["domain"])]


# --- Load ---
df = pd.read_csv("data/raw_results.csv", parse_dates=["timestamp"])
df["domain"] = df["url"].apply(get_domain)
df_wiki = pd.read_csv("data/raw_wikipedia_perennial_sources.csv")
print(f"Loaded {len(df)} results")

# --- Wikipedia ---
wiki = df_wiki.assign(domain=df_wiki["domains"].str.split(";")).explode("domain")
wiki["domain"] = wiki["domain"].str.strip().str.lower()
wiki.loc[wiki["domain"].isin(WIKI_OVERRIDES), "status"] = (
    wiki.loc[wiki["domain"].isin(WIKI_OVERRIDES), "domain"].map(WIKI_OVERRIDES)
)
ambiguous = wiki.groupby("domain")["status"].nunique()
ambiguous = ambiguous[ambiguous > 1].index
undef = df[df["domain"].isin(ambiguous)].copy()
undef["reason"] = undef["domain"].apply(lambda d: f"domain {d} has conflicting statuses in Wikipedia")
undef.to_csv("results/processed_sources_undefined.csv", index=False)
df = df[~df["domain"].isin(ambiguous)]
wiki_clear = wiki[~wiki["domain"].isin(ambiguous)]
df = match_and_remove(
    df,
    wiki_clear.drop_duplicates("domain")[["domain", "status"]],
    lambda r: f"domain {r['domain']} is {r['status']} per Wikipedia perennial sources",
    "Wikipedia"
)

# --- Rules (.edu, .ac, .gov, doi.org) ---
for ext, status, fname in [(".edu", "reliable", "reliable"), (".ac", "reliable", "reliable"), (".gov", "mixed", "mixed")]:
    mask = df["domain"].str.endswith(ext)
    g = df[mask].copy()
    g["status"] = status
    g["reason"] = g["domain"].apply(lambda d: f"domain {d} has {ext} suffix")
    g.to_csv(f"results/processed_sources_{fname}.csv", mode="a", header=False, index=False)
    df = df[~mask]
    print(f"{ext}: tagged {len(g)} rows")

doi_mask = df["url"].str.contains("doi.org", na=False)
g = df[doi_mask].copy()
g["status"] = "mixed"
g["reason"] = "url contains doi.org"
g.to_csv("results/processed_sources_mixed.csv", mode="a", header=False, index=False)
df = df[~doi_mask]

# --- Typosquats ---
credible = wiki[wiki["status"] == "reliable"]["domain"].dropna().unique().tolist()

def get_core(d):
    return re.sub(r"^www\.", "", d).rsplit(".", 1)[0]

def is_typosquat(d):
    if len(get_core(d)) < 5:
        return None, None
    for c in credible:
        dist = Levenshtein.distance(d, c)
        if d != c and dist <= 1:
            return c, dist
    return None, None

mask, reasons = [], []
for d in df["domain"]:
    c, dist = is_typosquat(d)
    mask.append(c is not None)
    reasons.append(f"domain {d} differs by {dist} char(s) from {c}" if c else None)

mask = pd.Series(mask, index=df.index)
g = df[mask].copy()
g["status"] = "unreliable"
g["reason"] = [r for r, m in zip(reasons, mask) if m]
g.to_csv("results/processed_sources_unreliable.csv", mode="a", header=False, index=False)
df = df[~mask]
print(f"Typosquats: tagged {len(g)} rows")

# --- OpenSources ---
try:
    df = match_and_remove(
        df,
        load_opensources(),
        lambda r: f"domain {r['domain']} is '{r['type']}' per OpenSources",
        "OpenSources"
    )
except Exception as e:
    print(f"OpenSources failed: {e}")

# --- MBFC ---
df = match_and_remove(
    df,
    load_mbfc(),
    lambda r: f"domain {r['domain']} is '{r['type']}' per MBFC",
    "MBFC"
)

# --- Remaining ---
remaining = df.groupby("domain").agg(domain_count=("url", "count"), urls=("url", ";".join)).reset_index()
remaining.sort_values("domain_count", ascending=False).to_csv("results/remaining_sources.csv", index=False)
print(f"Remaining unclassified: {len(remaining)} domains")