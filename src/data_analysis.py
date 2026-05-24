import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from scipy.stats import chi2_contingency
from scipy.stats import levene
import os

os.makedirs("results/figures", exist_ok=True)

# Set style for plots
plt.style.use('seaborn-v0_8-darkgrid')
sns.set_palette("Set2")

# Load raw data
df_raw = pd.read_csv("data/raw_results.csv", parse_dates=["timestamp"])

reliable = pd.read_csv("results/processed_sources_reliable.csv")
unreliable = pd.read_csv("results/processed_sources_unreliable.csv")
mixed = pd.read_csv("results/processed_sources_mixed.csv")

# Combine classifications
classified = pd.concat([
    reliable.assign(credibility="reliable"),
    unreliable.assign(credibility="unreliable"),
    mixed.assign(credibility="mixed")
])

classified = classified.drop_duplicates(subset=['url'], keep='first')

print(f"Classified {len(classified)} out of {len(df_raw)} results")
print(f"  Reliable: {len(reliable)}")
print(f"  Unreliable: {len(unreliable)}")
print(f"  Mixed: {len(mixed)}")
print("\n")

# Add credibility
df = df_raw.merge(
    classified[['url', 'credibility', 'reason']],
    on='url',
    how='left'
)
df['credibility'] = df['credibility'].fillna('unknown')

print("Credibility distribution:")
print(df['credibility'].value_counts())
print("\n")


# ----- Q1: Credibility Distribution by Query Type (Stacked Bar Chart) -----
# Answer to: Does the way you phrase a search query (neutral vs slanted) affect the credibility of search results?
summary = df.groupby(['query_type', 'credibility']).size().unstack(fill_value=0)
summary_pct = summary.div(summary.sum(axis=1), axis=0) * 100

fig, axes = plt.subplots(1, 2, figsize=(16, 6))

# Stacked bar chart (percentages)
ax1 = axes[0]
summary_pct[['reliable', 'mixed', 'unreliable', 'unknown']].plot(
    kind='bar', stacked=True, ax=ax1, color=['#2ecc71', '#f39c12', '#e74c3c', '#95a5a6'], legend=False
)
ax1.set_title('Credibility Distribution by Query Type', fontsize=14, fontweight='bold')
ax1.set_xlabel('Query Type', fontsize=12)
ax1.set_ylabel('Percentage (%)', fontsize=12)
ax1.set_ylim(0, 100)
ax1.set_xticklabels(ax1.get_xticklabels(), rotation=0, ha='center')
for container in ax1.containers:
    ax1.bar_label(container, fmt='%.1f%%', label_type='center', fontsize=9)

# Bar chart (raw counts)
ax2 = axes[1]
summary[['reliable', 'mixed', 'unreliable', 'unknown']].plot(
    kind='bar', ax=ax2, color=['#2ecc71', '#f39c12', '#e74c3c', '#95a5a6'], legend=False
)
ax2.set_title('Raw Counts by Query Type', fontsize=14, fontweight='bold')
ax2.set_xlabel('Query Type', fontsize=12)
ax2.set_ylabel('Number of Results', fontsize=12)
ax2.set_xticklabels(ax2.get_xticklabels(), rotation=0, ha='center')
for container in ax2.containers:
    ax2.bar_label(container, fmt='%d', fontsize=9)

# Shared legend
handles, labels = ax1.get_legend_handles_labels()
fig.legend(handles, labels, title='Credibility', 
           bbox_to_anchor=(1.02, 0.5), loc='center left', 
           fontsize=10, title_fontsize=11)

plt.tight_layout()
plt.savefig('results/figures/Q1_credibility_distribution.png', dpi=150, bbox_inches='tight')
plt.close()
print("Saved: results/figures/Q1_credibility_distribution.png")


# ----- Q2: Top Unreliable Domains (Horizontal Bar Charts) -----
# Answer to: Which specific unreliable websites appear most often, and does their appearance differ between neutral vs slanted searches?
slanted_unreliable = df[(df['query_type'] == 'slanted') & (df['credibility'] == 'unreliable')]
top_domains_slanted = slanted_unreliable['domain'].value_counts().head(10)

neutral_unreliable = df[(df['query_type'] == 'neutral') & (df['credibility'] == 'unreliable')]
top_domains_neutral = neutral_unreliable['domain'].value_counts().head(10)

fig, axes = plt.subplots(1, 2, figsize=(14, 8))

# Slanted queries
ax1 = axes[0]
top_domains_slanted.plot(kind='barh', ax=ax1, color='#e74c3c')
ax1.set_title('Top 10 Unreliable Domains in Slanted Queries', fontsize=14, fontweight='bold')
ax1.set_xlabel('Number of Appearances', fontsize=12)
ax1.set_ylabel('Domain', fontsize=12)
for i, v in enumerate(top_domains_slanted.values):
    ax1.text(v + 0.5, i, str(v), va='center', fontsize=10)

# Neutral queries
ax2 = axes[1]
top_domains_neutral.plot(kind='barh', ax=ax2, color='#e67e22')
ax2.set_title('Top 10 Unreliable Domains in Neutral Queries', fontsize=14, fontweight='bold')
ax2.set_xlabel('Number of Appearances', fontsize=12)
ax2.set_ylabel('Domain', fontsize=12)
for i, v in enumerate(top_domains_neutral.values):
    ax2.text(v + 0.5, i, str(v), va='center', fontsize=10)

plt.tight_layout()
plt.savefig('results/figures/Q2_top_unreliable_domains.png', dpi=150, bbox_inches='tight')
plt.close()
print("Saved: results/figures/Q2_top_unreliable_domains.png")


# ----- Q3: Ranking Position of Unreliable Results (Box Plot) -----
# Answer to: Do unreliable results rank higher (closer to position 1) in slanted vs neutral queries?
unreliable_only = df[df['credibility'] == 'unreliable']

# Calculate SD and other statistics
stats_df = unreliable_only.groupby('query_type')['position'].agg(['mean', 'median', 'std', 'var', 'count'])
print("\nPosition statistics for unreliable results:")
print(stats_df)

# Levene's test for equal variances
neutral_positions = unreliable_only[unreliable_only['query_type'] == 'neutral']['position']
slanted_positions = unreliable_only[unreliable_only['query_type'] == 'slanted']['position']

stat, p_var = levene(neutral_positions, slanted_positions)
print(f"\nLevene's test for equal variances: statistic = {stat:.3f}, p = {p_var:.4f}")
if p_var < 0.05:
    print("Variances are significantly different (spread differs by query type)")
else:
    print("No significant difference in variance")

fig, ax = plt.subplots(figsize=(8, 6))

# Box plot
order = ['neutral', 'slanted']
sns.boxplot(data=unreliable_only, x='query_type', y='position', order=order, ax=ax, palette=['#3498db', '#e74c3c'])

stats = unreliable_only.groupby('query_type')['position'].median().loc[order]
for i, (query_type, med) in enumerate(stats.items()):
    ax.text(
        i, med,
        f"Median = {med:.0f}",
        ha='center',
        va='bottom',
        fontsize=10,
        fontweight='bold'
    )
ax.set_title('Ranking Position of Unreliable Results', fontsize=14, fontweight='bold')
ax.set_xlabel('Query Type', fontsize=12)
ax.set_ylabel('Position (lower = higher ranked)', fontsize=12)
ax.set_ylim(0, 11)  # Positions 1-10 

plt.tight_layout()
plt.savefig('results/figures/Q3_position_analysis.png', dpi=150, bbox_inches='tight')
plt.close()
print("Saved: results/figures/Q3_position_analysis.png")


# ----- Q4: Topics with Highest Unreliable Percentage (Horizontal Bar Chart) -----
# Answer to: Which topics are most vulnerale to misinformation, and does this differ between neutral vs slanted searches?
topic_summary = df.groupby(['topic', 'query_type', 'credibility']).size().unstack(fill_value=0)
topic_summary['unreliable_pct'] = topic_summary['unreliable'] / (topic_summary['reliable'] + topic_summary['unreliable'] + topic_summary['mixed']) * 100

top_topics_slanted = topic_summary.xs('slanted', level='query_type')['unreliable_pct'].sort_values(ascending=False).head(15)
top_topics_neutral = topic_summary.xs('neutral', level='query_type')['unreliable_pct'].sort_values(ascending=False).head(15)

fig, axes = plt.subplots(1, 2, figsize=(16, 10))

# Slanted queries
ax1 = axes[0]
top_topics_slanted.plot(kind='barh', ax=ax1, color='#e74c3c')
ax1.set_title('Topics with Highest % of Unreliable Results (Slanted Queries)', fontsize=14, fontweight='bold')
ax1.set_xlabel('Unreliable Results (%)', fontsize=12)
ax1.set_ylabel('Topic', fontsize=12)
for i, v in enumerate(top_topics_slanted.values):
    ax1.text(v + 1, i, f'{v:.1f}%', va='center', fontsize=9)

# Neutral queries
ax2 = axes[1]
top_topics_neutral.plot(kind='barh', ax=ax2, color='#e67e22')
ax2.set_title('Topics with Highest % of Unreliable Results (Neutral Queries)', fontsize=14, fontweight='bold')
ax2.set_xlabel('Unreliable Results (%)', fontsize=12)
ax2.set_ylabel('Topic', fontsize=12)
for i, v in enumerate(top_topics_neutral.values):
    ax2.text(v + 1, i, f'{v:.1f}%', va='center', fontsize=9)

plt.tight_layout()
plt.savefig('results/figures/Q4_topics_unreliable.png', dpi=150, bbox_inches='tight')
plt.close()
print("Saved: results/figures/Q4_topics_unreliable.png")


# ----- Pie Chart of Overall Credibility -----

fig, ax = plt.subplots(figsize=(8, 8))
credibility_counts = df['credibility'].value_counts()
colors = {'reliable': '#2ecc71', 'mixed': '#f39c12', 'unreliable': '#e74c3c', 'unknown': '#95a5a6'}
pie_colors = [colors.get(c, '#95a5a6') for c in credibility_counts.index]

wedges, texts, autotexts = ax.pie(
    credibility_counts.values,
    labels=credibility_counts.index,
    autopct='%1.1f%%',
    colors=pie_colors,
    explode=[0.05] * len(credibility_counts),
    shadow=True
)
ax.set_title('Overall Credibility Distribution of Search Results', fontsize=16, fontweight='bold')
plt.tight_layout()
plt.savefig('results/figures/overall_credibility_pie.png', dpi=150, bbox_inches='tight')
plt.close()
print("Saved: results/figures/overall_credibility_pie.png")


# ----- Statistical Test Visualization -----
# Answer to: Is the difference between neutral and slanted results statistically significant or just random chance?
contingency = pd.crosstab(df['query_type'], df['credibility'])
chi2, p, dof, expected = chi2_contingency(contingency)

print("\n" + "="*60)
print("STATISTICAL TEST")
print("-"*60)
print(f"Chi-square test: χ² = {chi2:.2f}, p = {p:.2e}, df = {dof}")
print(f"Significant difference: {'YES' if p < 0.05 else 'NO'}")
print("-"*60)


# ----- Summary Statistics Table (as a figure) -----

summary_stats = {
    'Metric': [
        'Total queries',
        'Total results',
        'Classified results',
        'Neutral - Reliable %',
        'Slanted - Reliable %',
        'Neutral - Unreliable %',
        'Slanted - Unreliable %'
    ],
    'Value': [
        df['query'].nunique(),
        len(df),
        len(df[df['credibility'] != 'unknown']),
        round((df[(df['query_type']=='neutral') & (df['credibility']=='reliable')].shape[0] / df[df['query_type']=='neutral'].shape[0]) * 100, 1),
        round((df[(df['query_type']=='slanted') & (df['credibility']=='reliable')].shape[0] / df[df['query_type']=='slanted'].shape[0]) * 100, 1),
        round((df[(df['query_type']=='neutral') & (df['credibility']=='unreliable')].shape[0] / df[df['query_type']=='neutral'].shape[0]) * 100, 1),
        round((df[(df['query_type']=='slanted') & (df['credibility']=='unreliable')].shape[0] / df[df['query_type']=='slanted'].shape[0]) * 100, 1)
    ]
}

summary_df = pd.DataFrame(summary_stats)
summary_df.to_csv("results/analysis_summary.csv", index=False)

# Create a table figure
fig, ax = plt.subplots(figsize=(10, 4))
ax.axis('tight')
ax.axis('off')
table = ax.table(cellText=summary_df.values, colLabels=summary_df.columns, cellLoc='center', loc='center')
table.auto_set_font_size(False)
table.set_fontsize(11)
table.scale(1.2, 1.5)
ax.set_title('Analysis Summary', fontsize=14, fontweight='bold', pad=20)
plt.tight_layout()
plt.savefig('results/figures/summary_table.png', dpi=150, bbox_inches='tight')
plt.close()
print("Saved: results/figures/summary_table.png")

print("\nAll analysis complete! Check the 'results/figures' folder for all visualizations.")