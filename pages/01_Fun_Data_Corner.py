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
    bins = list(range(1100,1601,50))
    labels = [f"{b}-{b+49}" for b in bins[:-1]]
    df['Score_Bucket'] = pd.cut(df['SAT_Adjusted'], bins=bins, labels=labels, right=False)

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
    fig.update_layout(
        xaxis_tickangle=-45, 
        legend_title_text="Race", 
        yaxis_ticksuffix="%", 
        plot_bgcolor='rgb(17,17,17)',
        paper_bgcolor='rgb(17,17,17)',
        font_color='white'
    )
    st.plotly_chart(fig, use_container_width=True)

def plot_ivy_scatter(df_raw):
    ivies = ["Harvard", "Yale", "Princeton", "Columbia", "Brown", "Dartmouth", "Cornell", "Upenn"]

    selected = st.selectbox("Select Ivy League School:", ivies)

    df = df_raw[df_raw['acceptances'].str.contains(selected, case=False, na=False)]
    df = df.dropna(subset=['GPA', 'SAT_Score', 'ACT_Score'])

    df['SAT_Adjusted'] = df.apply(
        lambda r: r['SAT_Score']
        if pd.notna(r['SAT_Score'])
        else (r['ACT_Score'] * 45 if pd.notna(r['ACT_Score']) else None),
        axis=1
    )
    df = df.dropna(subset=['SAT_Adjusted', 'GPA', 'url'])

    fig = px.scatter(
        df,
        x='GPA',
        y='SAT_Adjusted',
        hover_data=['url'],
        title=f"GPA vs SAT/ACT (converted) — {selected}",
        labels={'GPA':'GPA','SAT_Adjusted':'SAT or ACT*45'},
        template='plotly_dark'
    )

    fig.update_traces(
        marker=dict(size=8, line=dict(width=1, color='DarkSlateGrey')),
        customdata=df[['url']],
        hovertemplate="<b>GPA:</b> %{x}<br><b>SAT*:</b> %{y}<br><extra></extra><br><a href='%{customdata[0]}'>Reddit Link</a>"
    )

    fig.update_layout(
        xaxis=dict(range=[2.5, 4.0], dtick=0.05, gridcolor='gray'),
        yaxis=dict(range=[1100, 1600], dtick=10, gridcolor='gray'),
        plot_bgcolor='rgb(17,17,17)',
        paper_bgcolor='rgb(17,17,17)',
        font_color='white'
    )
    st.plotly_chart(fig, use_container_width=True)

def main():
    st.title("🎲 Fun Data Corner")
    st.header("Within‑Race SAT Distribution (1100–1600)")

    st.markdown("""
    Hello fellow data nerds! Here you can find numerous different angles of data visualization from the dataset I am using, updated as my dataset improves.

    I do want to note that since the data were taken from a subreddit dedicated to college results, there is a volunteer response bias in play that definitely overestimates all metrics for the typical student. Nevertheless, there aren't any better sources for this data that I could find, so we will have to roll with it!
    """)

    # Section 1: Race + SAT
    st.subheader("1. Race and Standardized Test Scores")
    df = load_and_prepare_data()

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

    # Section 2: Ivy League GPA vs SAT
    st.subheader("2. GPA vs Standardized Test Score (Ivy League Acceptances)")
    raw_df = pd.read_csv("master_data.csv")
    plot_ivy_scatter(raw_df)

if __name__=="__main__":
    main()
