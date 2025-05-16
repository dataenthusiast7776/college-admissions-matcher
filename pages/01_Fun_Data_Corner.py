# pages/01_Fun_Data_Corner.py

import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Fun Data Corner", layout="wide")

@st.cache_data
def load_and_prepare_data():
    df = pd.read_csv("master_data.csv")

    # Normalize ethnicity into four groups
    def norm_eth(e):
        if pd.isna(e): return None
        e = e.lower()
        if any(x in e for x in ["indian","south asian","asian"]): return "Asian"
        if "white" in e or "caucasian" in e: return "White"
        if "black" in e or "african" in e: return "Black"
        if any(x in e for x in ["hispanic","latino","latina","latinx"]): return "Hispanic"
        return None

    df['EthnicityNorm'] = df['Ethnicity'].apply(norm_eth)

    # Build a unified SAT score from SAT or ACT*45
    df['SAT_Adjusted'] = df.apply(
        lambda r: r['SAT_Score'] 
                  if pd.notna(r['SAT_Score']) 
                  else (r['ACT_Score'] * 45 if pd.notna(r['ACT_Score']) else None),
        axis=1
    )

    # Keep only our four groups & scores in [1100,1600]
    df = df.dropna(subset=['EthnicityNorm', 'SAT_Adjusted'])
    df = df[(df['SAT_Adjusted'] >= 1100) & (df['SAT_Adjusted'] <= 1600)]

    # Create 50-point buckets
    bins = list(range(1100, 1601, 50))
    labels = [f"{b}-{b+49}" for b in bins[:-1]]
    df['Score_Bucket'] = pd.cut(
        df['SAT_Adjusted'], bins=bins, labels=labels, right=False
    )

    # Drop any rows that fall outside (just in case)
    df = df.dropna(subset=['Score_Bucket'])
    return df

def plot_percentage_histogram(df):
    # Count and compute percentages within each bucket
    counts = (
        df.groupby(['Score_Bucket','EthnicityNorm'])
          .size()
          .reset_index(name='Count')
    )
    counts['TotalInBucket'] = counts.groupby('Score_Bucket')['Count'].transform('sum')
    counts['Percent'] = counts['Count'] / counts['TotalInBucket'] * 100

    # Build grouped bar chart
    fig = px.bar(
        counts,
        x='Score_Bucket',
        y='Percent',
        color='EthnicityNorm',
        barmode='group',
        category_orders={"Score_Bucket": counts['Score_Bucket'].cat.categories},
        labels={
            'Score_Bucket': 'SAT Score Range',
            'Percent': 'Percentage of Students (%)',
            'EthnicityNorm': 'Ethnicity'
        },
        title="SAT Score Distribution by Ethnicity (1100–1600)"
    )
    fig.update_layout(
        xaxis_tickangle=-45,
        bargap=0.15,
        bargroupgap=0.1,
        legend_title_text="Ethnicity",
    )
    st.plotly_chart(fig, use_container_width=True)

def main():
    st.title("🎲 Fun Data Corner")
    st.header("SAT Score Distribution by Ethnicity (1100–1600)")
    st.write(
        "This chart shows, for each 50‑point SAT range between 1100 and 1600, "
        "what percentage of students in that bucket belong to each ethnicity."
    )

    df = load_and_prepare_data()
    plot_percentage_histogram(df)

if __name__ == "__main__":
    main()

