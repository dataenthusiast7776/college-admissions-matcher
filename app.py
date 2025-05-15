import os
import streamlit as st

st.write("Current working directory:", os.getcwd())
st.write("Files here:", os.listdir())

import pandas as pd
import re

def normalize_ethnicity(ethnicity):
    if pd.isna(ethnicity):
        return "unknown"
    e = ethnicity.lower()
    if any(x in e for x in ["indian", "south asian", "asian"]):
        return "asian"
    elif "white" in e or "caucasian" in e:
        return "white"
    elif "black" in e or "african american" in e:
        return "black"
    elif "hispanic" in e or "latino" in e or "latina" in e or "latinx" in e:
        return "hispanic"
    elif "native american" in e or "indigenous" in e:
        return "native american"
    elif "middle eastern" in e or "arab" in e:
        return "middle eastern"
    else:
        return "other"

def normalize_gender(gender):
    if pd.isna(gender):
        return "unknown"
    g = str(gender).strip().lower()
    if g in ['male', 'm']:
        return 'male'
    elif g in ['female', 'f']:
        return 'female'
    else:
        return 'unknown'

def is_score_close(a, b, threshold=0.05):
    if pd.isna(a) or pd.isna(b):
        return False
    return abs(a - b) <= threshold * max(a, b)

def clean_acceptances(raw_acceptances):
    if pd.isna(raw_acceptances) or raw_acceptances.strip() == "":
        return ""

    school_keywords = [
        "university", "college", "institute", "state", "academy", "school",
        "tech", "polytechnic", "poly", "mit", "stanford", "harvard", "princeton", "yale"
    ]

    bad_keywords = [
        "club", "volunteer", "internship", "hook", "income", "essay", "activity", 
        "award", "reflection", "summary", "miscellaneous", "consideration", "recommendation",
        "research", "grades"
    ]

    good_keywords = ["ea", "ed", "rea", "rd"]

    parts = re.split(r"[\n,]+", raw_acceptances)

    cleaned = []
    for part in parts:
        part_lower = part.lower().strip()
        if not part_lower:
            continue
        if any(bk in part_lower for bk in bad_keywords):
            continue
        if any(sk in part_lower for sk in school_keywords):
            cleaned.append(part.strip())
            continue
        if any(gk == part_lower for gk in good_keywords):
            cleaned.append(part.strip())
            continue
        if len(part_lower.split()) <= 8:
            cleaned.append(part.strip())

    cleaned_str = ", ".join(cleaned)
    if len(cleaned_str) > 250:
        return ""

    return cleaned_str

def match_profiles(df, user_gpa, user_sat, user_act, user_ethnicity, user_gender):
    user_eth_norm = normalize_ethnicity(user_ethnicity)
    user_gender_norm = normalize_gender(user_gender)

    df['Ethnicity_normalized'] = df['Ethnicity'].apply(normalize_ethnicity)
    df['Gender_normalized'] = df['Gender'].apply(normalize_gender)
    df['acceptances_cleaned'] = df['acceptances'].apply(clean_acceptances)

    df_filtered = df[df['acceptances_cleaned'].str.strip() != ""]
    df_filtered = df_filtered[df_filtered['Ethnicity_normalized'] == user_eth_norm]
    df_filtered = df_filtered[df_filtered['Gender_normalized'] == user_gender_norm]

    df_filtered = df_filtered[
        (df_filtered['GPA'] >= user_gpa - 0.05) & 
        (df_filtered['GPA'] <= user_gpa + 0.05)
    ]

    def score_filter(row):
        sat_close = False
        act_close = False
        if not pd.isna(row['SAT_Score']):
            sat_close = abs(row['SAT_Score'] - user_sat) <= 30
        if not pd.isna(row['ACT_Score']):
            act_close = is_score_close(row['ACT_Score'], user_act, threshold=0.05)
        return sat_close or act_close

    df_filtered = df_filtered[df_filtered.apply(score_filter, axis=1)]

    output_cols = ['url', 'GPA', 'SAT_Score', 'ACT_Score', 'Ethnicity', 'Gender', 'acceptances_cleaned']
    matches = df_filtered[output_cols]

    return matches

@st.cache_data
def load_data():
    return pd.read_csv("https://raw.githubusercontent.com/vikram-dev1125/college-admissions-matcher/refs/heads/main/collegeresults_with_ethnicity_gpa_with_acceptances3.csv")

def main():
    st.title("College Admissions Profile Matcher")

    df = load_data()

    st.markdown("### Enter your academic profile:")

    user_gpa = st.number_input("GPA (4.0 scale)", min_value=0.0, max_value=4.5, value=4.0, step=0.01)
    user_sat = st.number_input("SAT Score", min_value=400, max_value=1600, value=1580, step=10)
    user_act = st.number_input("ACT Score", min_value=1, max_value=36, value=35, step=1)

    user_ethnicity = st.text_input("Ethnicity (e.g., Indian, White, Hispanic)", "Indian")
    user_gender = st.selectbox("Gender", options=["Male", "Female"])

    if st.button("Find Matching Profiles"):
        with st.spinner("Searching..."):
            matches = match_profiles(df, user_gpa, user_sat, user_act, user_ethnicity, user_gender)

        if matches.empty:
            st.warning("No matching profiles found.")
        else:
            st.success(f"Found {len(matches)} matching profiles:")
            for _, row in matches.iterrows():
                st.markdown(f"""
                    **URL:** {row['url']}  
                    **GPA:** {row['GPA']:.2f}  
                    **SAT:** {row['SAT_Score']}  
                    **ACT:** {row['ACT_Score']}  
                    **Ethnicity:** {row['Ethnicity']}  
                    **Gender:** {row['Gender']}  
                    **Acceptances:** {row['acceptances_cleaned']}
                    ---
                """)

if __name__ == "__main__":
    main()
