# pages/01_Fun_Data_Corner.py

import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Fun Data Corner", layout="wide")

@st.cache_data
def load_and_prepare_data():
    df = pd.read_csv("master_data.csv")

    # Normalize into four racial groups
    def norm_race(e):
        if pd.isna(e): return None
        e = e.lower()
        if any(x in e for x in ["indian","south asian","asian"]): return "Asian"
        if "white" in e or "caucasian" in e: return "White"
        if "black" in e or "african" in e: return "Black"
        if any(x in e for x in ["hispanic","latino","latina","latinx"]): return "Hispanic"
        return None

    df['RaceNorm'] = df['Ethnicity'].apply(norm_race)

    # Unified SAT score (SAT or ACT*45)
    df['SAT_Adjusted'] = df.apply(
        lambda r: r['SAT_Score']
                  if pd.notna(r['SAT_Score'])
                  else (r['ACT_Score'] * 45 if pd.notna(r['ACT_Score']) else None),
        axis=1
    )

    # Keep only chosen races & scores 1100–1600
    df = df.dropna(subset=['RaceNorm','SAT_Adjusted'])
    df = df[(df['SAT_Adjusted'] >= 1100) & (df['SAT_Adjusted'] <= 1600)]
    return df

def plot_box(df):
    fig = px.box(
        df,
        x='RaceNorm',
        y='SAT_Adjusted',
        color='RaceNorm',
        labels={'RaceNorm':'Race','SAT_Adjusted':'SAT Score'},
        title="SAT Score Distribution by Race (1100–1600)",
        color_discrete_map={
            "Asian":"#636EFA","White":"#EF553B",
            "Black":"#00CC96","Hispanic":"#AB63FA"
        }
    )
    fig.update_traces(boxmean=True)
    fig.update_layout(showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

def plot_within_race(df):
    # Buckets
    bins = list(range(1100,1601,50))
    labels = [f"{b}-{b+49}" for b in bins[:-1]]
    df['Score_Bucket'] = pd.cut(df['SAT_Adjusted'], bins=bins, labels=labels, right=False)

    # Count & percent within each race
    counts = (
        df.groupby(['RaceNorm','Score_Bucket'])
          .size()
          .reset_index(name='Count')
    )
    counts['TotalByRace'] = counts.groupby('RaceNorm')['Count'].transform('sum')
    counts['Percent'] = counts['Count'] / counts['TotalByRace'] * 100

    fig = px.bar(
        counts,
        x='Score_Bucket',
        y='Percent',
        color='RaceNorm',
        barmode='group',
        category_orders={'Score_Bucket': labels},
        labels={'Score_Bucket':'SAT Score Range','Percent':'% within Race','RaceNorm':'Race'},
        title="Within‑Race SAT Distribution (1100–1600)"
    )
    fig.update_layout(xaxis_tickangle=-45, legend_title_text="Race", yaxis_ticksuffix="%")
    st.plotly_chart(fig, use_container_width=True)

def main():
    st.title("🎲 Fun Data Corner")
    st.header("Within‑Race SAT Distribution (1100–1600)")

    # Intro paragraph right after header
    st.markdown("""
    Hello fellow data nerds! Here you can find numerous different angles of data visualization from the dataset I am using, updated as my dataset improves.

    I do want to note that since the data were taken from a subreddit dedicated to college results, there is a volunteer response bias in play that definitely overestimates all metrics for the typical student. Nevertheless, there aren't any better sources for this data that I could find, so we will have to roll with it!
    """)

    df = load_and_prepare_data()

    mode = st.radio(
        "Visualization type:",
        ["Box‑Plot Distribution", "Within‑Race Percentage Histogram"]
    )

    if mode == "Box‑Plot Distribution":
        # Condensed into a collapsible expander
        with st.expander("▶️ Box‑Plot of SAT Scores by Race", expanded=False):
            plot_box(df)
    else:
        st.subheader("Percentage Histogram Within Each Race")
        plot_within_race(df)

if __name__=="__main__":
    main()
