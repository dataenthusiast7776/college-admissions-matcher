import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np

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

def plot_strip(df):
    ivy_schools = {
        "Brown": "brown",
        "Columbia": "purple",
        "Cornell": "orange",
        "Dartmouth": "green",
        "Harvard": "red",
        "Penn": "blue",
        "Princeton": "black",
        "Yale": "gold"
    }

    # Filter admitted students per ivy and collect their GPA
    records = []
    for school in ivy_schools.keys():
        admitted = df[df['acceptances'].str.contains(school, case=False, na=False)]
        for gpa in admitted['GPA'].dropna():
            records.append({'School': school, 'GPA': gpa})

    df_ivy = pd.DataFrame(records)

    # Add jitter on x axis for strip effect
    jitter_strength = 0.1
    x_vals = []
    school_to_num = {school: i for i, school in enumerate(ivy_schools.keys())}
    for school in df_ivy['School']:
        base_pos = school_to_num[school]
        jitter = np.random.uniform(-jitter_strength, jitter_strength)
        x_vals.append(base_pos + jitter)
    df_ivy['x_jitter'] = x_vals

    fig = px.scatter(
        df_ivy,
        x='x_jitter',
        y='GPA',
        color='School',
        color_discrete_map=ivy_schools,
        labels={'x_jitter': 'School', 'GPA': 'GPA'},
        title="GPA Distribution of Ivy League Admittees",
        hover_data=['School', 'GPA'],
        width=900,
        height=500
    )

    # Update x-axis to show school names at correct positions
    fig.update_xaxes(
        tickvals=list(range(len(ivy_schools))),
        ticktext=list(ivy_schools.keys()),
        title_text="Ivy League School"
    )
    fig.update_yaxes(range=[3.0,4.0], title_text="GPA")
    fig.update_traces(marker=dict(size=7, opacity=0.7))
    fig.update_layout(showlegend=True)

    st.plotly_chart(fig, use_container_width=True)

def main():
    st.title("🎲 Fun Data Corner")
    st.header("Within‑Race SAT Distribution (1100–1600)")

    st.markdown("""
    Hello fellow data nerds! Here you can find numerous different angles of data visualization from the dataset I am using, updated as my dataset improves.

    I do want to note that since the data were taken from a subreddit dedicated to college results, there is a volunteer response bias in play that definitely overestimates all metrics for the typical student. Nevertheless, there aren't any better sources for this data that I could find, so we will have to roll with it!
    """)

    # New label below intro
    st.subheader("1. Race and Standardized Test Scores")

    df = load_and_prepare_data()

    # Collapsible widget for choosing visualization type
    with st.expander("▶️ Visualization Options", expanded=False):
        mode = st.radio(
            "Visualization type:",
            ["Box‑Plot Distribution", "Within‑Race Percentage Histogram"]
        )

    if mode == "Box‑Plot Distribution":
        with st.expander("▶️ Box‑Plot of SAT Scores by Race", expanded=False):
            plot_box(df)
    else:
        st.subheader("Percentage Histogram Within Each Race")
        plot_within_race(df)

    # Next graph: Ivy League GPA strip plot
    st.subheader("2. GPA Distribution of Ivy League Admittees")
    plot_strip(df)

if __name__=="__main__":
    main()


