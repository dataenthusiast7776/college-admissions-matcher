import streamlit as st
import pandas as pd
import altair as alt

# Load and clean data
@st.cache_data
def load_data():
    df = pd.read_csv("master_data.csv")  # use same CSV as app
    df['SAT_Estimate'] = df.apply(
        lambda row: row['SAT_Score'] if not pd.isna(row['SAT_Score'])
        else (row['ACT_Score'] * 45 if not pd.isna(row['ACT_Score']) else None),
        axis=1
    )
    df = df[df['SAT_Estimate'].notna()]
    
    def norm_ethnicity(e):
        e = str(e).lower()
        if "asian" in e:
            return "Asian"
        if "white" in e:
            return "White"
        if "black" in e:
            return "Black"
        if "hispanic" in e or "latino" in e:
            return "Hispanic"
        return "Other"

    df['Ethnicity_Clean'] = df['Ethnicity'].apply(norm_ethnicity)
    df = df[df['Ethnicity_Clean'].isin(["Asian", "White", "Black", "Hispanic"])]
    return df

df = load_data()

# Score bucketing
df['Score_Bucket'] = pd.cut(df['SAT_Estimate'], bins=range(800, 1600, 100))

# Plot
st.title("SAT Score Distribution by Ethnicity")
chart = alt.Chart(df).mark_bar().encode(
    x=alt.X("Score_Bucket:N", title="SAT Score Bucket"),
    y=alt.Y("count():Q", title="Number of Students"),
    color=alt.Color("Ethnicity_Clean:N", title="Ethnicity"),
    tooltip=["Ethnicity_Clean", "count()"]
).properties(
    width=700,
    height=400
)

st.altair_chart(chart)
