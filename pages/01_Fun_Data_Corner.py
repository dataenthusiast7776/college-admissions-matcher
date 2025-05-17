import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Fun Data Corner", layout="wide")

@st.cache_data
def load_and_prepare_data():
    df = pd.read_csv("https://drive.google.com/uc?export=download&id=1nZtwYcUX_KraxOTAOLg6-ZvKZnKMNpSg")

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

    # GPA and acceptances for Ivy League scatter plots
    df_gpa = df[['GPA', 'acceptances', 'SAT_Score', 'ACT_Score']].copy()
    df_gpa = df_gpa.dropna(subset=['GPA', 'acceptances'])
    
    # Calculate combined SAT/ACT score again for scatter plot, to be safe
    df_gpa['SAT_Adjusted'] = df_gpa.apply(
        lambda r: r['SAT_Score']
                  if pd.notna(r['SAT_Score'])
                  else (r['ACT_Score'] * 45 if pd.notna(r['ACT_Score']) else None),
        axis=1
    )
    df_gpa = df_gpa.dropna(subset=['SAT_Adjusted'])
    
    return df, df_gpa

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

def get_ivy_school_data(df_gpa, school_name):
    accepted = df_gpa[df_gpa['acceptances'].str.contains(school_name, case=False, na=False)]
    ivy_gpa_data = []
    for _, row in accepted.iterrows():
        ivy_gpa_data.append({
            'GPA': row['GPA'],
            'SAT_ACT_Score': row['SAT_Adjusted']
        })
    return pd.DataFrame(ivy_gpa_data)

def plot_ivy_scatter_single(df_school, school_name):
    if df_school.empty:
        st.write(f"No GPA and test score data found for {school_name} acceptances.")
        return
    
    fig = px.scatter(
        df_school,
        x='GPA',
        y='SAT_ACT_Score',
        labels={
            'GPA': 'GPA (3.0 - 4.0 scale)',
            'SAT_ACT_Score': 'Unified SAT/ACT Score'
        },
        title=f"GPA vs. SAT/ACT Scores of Students Accepted to {school_name}",
        color_discrete_sequence=["#636EFA"]
    )
    fig.update_xaxes(range=[3.0, 4.0])
    fig.update_yaxes(range=[1100, 1600])
    st.plotly_chart(fig, use_container_width=True)

def main():
    st.title("🎲 Fun Data Corner")
    
    st.markdown("""
    Hello fellow data nerds! Here you can find numerous different angles of data visualization from the dataset I am using, updated as my dataset improves.

    I do want to note that since the data were taken from a subreddit dedicated to college results, there is a volunteer response bias in play that definitely overestimates all metrics for the typical student. Nevertheless, there aren't any better sources for this data that I could find, so we will have to roll with it!
    """)
    
    # 1. SAT Scores Visualization
    st.subheader("1. Race and Standardized Test Scores")
    df, df_gpa = load_and_prepare_data()

    with st.expander("▶️ SAT Visualization Options", expanded=False):
        sat_mode = st.radio(
            "Visualization type:",
            ["Box‑Plot Distribution", "Within‑Race Percentage Histogram"]
        )

    if sat_mode == "Box‑Plot Distribution":
        with st.expander("▶️ Box‑Plot of SAT Scores by Race", expanded=False):
            plot_box(df)
    else:
        st.subheader("Percentage Histogram Within Each Race")
        plot_within_race(df)
        
    # 2. Ivy League GPA vs SAT/ACT Separate Scatter Plots
    st.subheader("2. Ivy League GPA vs. SAT/ACT Scores of Accepted Students")

    ivy_schools = [
        'Brown',
        'Columbia',
        'Cornell',
        'Dartmouth',
        'Harvard',
        'Penn',
        'Princeton',
        'Yale'
    ]
    
    selected_school = st.selectbox("Select Ivy League School:", ivy_schools)
    df_school = get_ivy_school_data(df_gpa, selected_school)
    plot_ivy_scatter_single(df_school, selected_school)

if __name__=="__main__":
    main()
