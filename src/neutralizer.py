import pandas as pd
import os

# Files to process
source_files = [
    "results/processed_sources_mixed.csv",
    "results/processed_sources_reliable.csv",
    "results/processed_sources_unreliable.csv",
    "results/processed_sources_undefined.csv",
    "results/remaining_data.csv",
    "data/raw_results.csv"
]

# Load the lookup table
lookup_df = pd.read_csv("data/queries_neutrality.csv")

# Keep only rows where confirmed == 1
confirmed_queries = set(lookup_df[lookup_df["confirmed"] == 1]["query"])

for filename in source_files:
    df = pd.read_csv(filename)

    # If query_type column exists, only filter rows where query_type == 'neutral'
    if 'query_type' in df.columns:
        mask = (df['query_type'] != 'neutral') | (df['query'].isin(confirmed_queries))
        filtered = df[mask]
    else:
        filtered = df[df["query"].isin(confirmed_queries)]

    # Build output filename: e.g. processed_sources_mixed_neutral.csv
    name, ext = os.path.splitext(filename)
    output_filename = f"{name}_neutral{ext}"

    filtered.to_csv(output_filename, index=False)
    print(f"{filename}: {len(df)} rows → {len(filtered)} kept → saved as {output_filename}")