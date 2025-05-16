import streamlit as st
import pandas as pd
import plotly.express as px

@st.cache_data
def load_and_prepare_data():
    df = pd.read_csv("master_data_with_ECs.csv")
    
    # Normalize ethnicity to 4 main groups + drop others & unknown
    def norm_ethnicity(e):
        if pd.isna(e): return None
        e = e.lower()
        if any(x in e for x in ["indian","south asian","asian"]): return "Asian"
        if "white" in e or "caucasian" in e: return "White"
        if "black" in e or "african american" in e: return "Black"
        if "hispanic" in e or "latino" in e or "latina" in e or "latinx" in e: return "Hispanic"
        return None

    df['EthnicityNorm'] = df['Ethnicity'].apply(norm_ethnicity)
    
    # Convert ACT to SAT approx if SAT is missing
    df['SAT_Adjusted'] = df.apply(
        lambda row: row['SAT_Score'] if not pd.isna(row['SAT_Score'])
        else (row['ACT_Score'] * 45 if not pd.isna(row['ACT_Score']) else None), axis=1)
    
    # Drop rows with no ethnicity or no SAT_Adjusted
    df = df.dropna(subset=['EthnicityNorm', 'SAT_Adjusted'])
    
    # Create score buckets of 100 points from 400 to 1600
    bins = list(range(400, 1700, 100))
    labels = [f"{b}-{b+99}" for b in bins[:-1]]
    df['SAT_Bucket'] = pd.cut(df['SAT_Adjusted'], bins=bins, labels=labels, right=False)
    
    # Drop rows that didn't fit into buckets (e.g. <400 or >1599)
    df = df.dropna(subset=['SAT_Bucket'])
    
    return df

def plot_ethnicity_scores_histogram(df):
    fig = px.histogram(
        df,
        x='SAT_Bucket',
        color='EthnicityNorm',
        barmode='group',
        category_orders={'SAT_Bucket': [f"{b}-{b+99}" for b in range(400,1600,100)]},
        labels={'SAT_Bucket': 'SAT Score Range', 'count': 'Number of Students', 'EthnicityNorm': 'Ethnicity'},
        title="SAT Score Distribution by Ethnicity",
        color_discrete_map={
            "Asian": "#636EFA",
            "White": "#EF553B",
            "Black": "#00CC96",
            "Hispanic": "#AB63FA"
        }
    )
    fig.update_layout(
        xaxis_tickangle=-45,
        bargap=0.15,
        bargroupgap=0.1,
        legend_title_text='Ethnicity',
        xaxis={'categoryorder':'array', 'categoryarray':[f"{b}-{b+99}" for b in range(400,1600,100)]}
    )
    st.plotly_chart(fig, use_container_width=True)

def main():
    st.title("Fun Data Corner: Ethnicity & SAT Scores")
    df = load_and_prepare_data()
    plot_ethnicity_scores_histogram(df)
    
if __name__ == "__main__":
    main()
