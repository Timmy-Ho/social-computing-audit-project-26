import pandas as pd
import re
from rapidfuzz.distance import Levenshtein

def load_data():
    df = pd.read_csv("../data/raw_results.csv", parse_dates=["timestamp"])
    df_wiki = pd.read_csv("../data/raw_wikipedia_perennial_sources.csv")
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
    undefined.to_csv("../results/processed_sources_undefined.csv", index=False)
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
        filename = f"../results/processed_sources_{status}.csv"
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
    edu_ac.to_csv("../results/processed_sources_reliable.csv", mode="a", header=False, index=False) 
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
    mixed.to_csv("../results/processed_sources_mixed.csv", mode="a", header=False, index=False)
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
    typosquats.to_csv("../results/processed_sources_unreliable.csv", mode="a", header=False, index=False)
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
    remaining_grouped.to_csv("../results/remaining_sources.csv", index=False)
    print(f"Saved {len(remaining_grouped)} unique domains to remaining_sources.csv")
    print(remaining_grouped[["domain", "domain_count"]].head(10))



df, df_wiki = load_data()
df_wiki_expanded = expand_wiki_domains(df_wiki)
df_wiki_expanded = override_conflicts(df_wiki_expanded)
df, df_wiki_clear = split_ambiguous(df, df_wiki_expanded)
df = match_wiki_sources(df, df_wiki_clear)
df = tag_academic(df)
df = tag_gov_doi(df)
df = tag_typosquats(df, df_wiki_expanded)
save_remaining(df)