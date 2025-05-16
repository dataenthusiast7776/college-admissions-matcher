import os
import streamlit as st
import pandas as pd
import re

# Show current folder (for debugging; remove in prod)
st.write("Current working directory:", os.getcwd())
st.write("Files here:", os.listdir())

# ——— Normalization Helpers ———
def normalize_ethnicity(ethnicity):
    if pd.isna(ethnicity):
        return "unknown"
    e = ethnicity.lower()
    if any(x in e for x in ["indian", "south asian", "asian"]):
        return "asian"
    if "white" in e or "caucasian" in e:
        return "white"
    if "black" in e or "african american" in e:
        return "black"
    if "hispanic" in e or "latino" in e or "latina" in e or "latinx" in e:
        return "hispanic"
    if "native american" in e or "indigenous" in e:
        return "native american"
    if "middle eastern" in e or "arab" in e:
        return "middle eastern"
    return "other"

def normalize_gender(gender):
    if pd.isna(gender):
        return "unknown"
    g = str(gender).strip().lower()
    if g in ['male', 'm']:
        return 'male'
    if g in ['female', 'f']:
        return 'female'
    return 'unknown'

def clean_acceptances(raw):
    if pd.isna(raw) or not raw.strip():
        return ""
    parts = re.split(r"[\n,]+", raw)
    good, bad_kw, school_kw = [], {"club","volunteer","internship","hook","income",
                                   "essay","activity","award","reflection","summary",
                                   "miscellaneous","consideration","recommendation",
                                   "research","grades"}, \
                              {"university","college","institute","state",
                               "academy","school","tech","polytechnic","poly",
                               "mit","stanford","harvard","princeton","yale"}
    for p in parts:
        pl = p.strip().lower()
        if not pl or any(b in pl for b in bad_kw):
            continue
        if any(s in pl for s in school_kw) or pl in {"ea","ed","rea","rd"} or len(pl.split())<=8:
            good.append(p.strip())
    joined = ", ".join(good)
    return joined if len(joined)<=250 else ""

def match_profiles(df, gpa, sat, act, eth, gen):
    df['Eth_norm'] = df['Ethnicity'].apply(normalize_ethnicity)
    df['Gen_norm'] = df['Gender'].apply(normalize_gender)
    df['acc_clean'] = df['acceptances'].apply(clean_acceptances)
    d = df[df['acc_clean']!=""]

    # Ethnicity filter
    if eth!="No filter":
        d = d[d['Eth_norm']==eth.lower()]
    # Gender filter
    if gen!="No filter":
        d = d[d['Gen_norm']==gen.lower()]

    # GPA filter ±0.05
    d = d[(d['GPA']>=gpa-0.05)&(d['GPA']<=gpa+0.05)]

    # Score filter
    if sat is not None:
        d = d[d['SAT_Score'].apply(lambda x: abs(x-sat)<=30 if not pd.isna(x) else False)]
    if act is not None:
        d = d[d['ACT_Score'].apply(lambda x: abs(x-act)<=1 if not pd.isna(x) else False)]

    return d[['url','GPA','SAT_Score','ACT_Score','Ethnicity','Gender','acc_clean']]

@st.cache_data
def load_data():
    # make sure this is the RAW URL from GitHub
    return pd.read_csv(
      "https://raw.githubusercontent.com/vikram-dev1125/college-admissions-matcher/refs/heads/main/master_data.csv"
    )

def main():
    st.title("College Admissions Profile Matcher")

    df = load_data()

    st.markdown("#### Enter your profile (leave filters as “No filter” to skip):")

    # GPA: slider + manual, capped at 4.0
    gpa_s = st.slider("GPA (max 4.0)", 0.0, 4.0, 4.0, 0.01)
    gpa_m = st.number_input("Or enter GPA manually", 0.0, 4.0, gpa_s, 0.01)
    user_gpa = gpa_m if gpa_m!=gpa_s else gpa_s

    # Score filter selectbox
    score_choice = st.selectbox("Score filter", ["No filter", "SAT", "ACT"])
    user_sat = None; user_act = None
    if score_choice=="SAT":
        user_sat = st.number_input("SAT Score", 400, 1600, 1580, 10)
    elif score_choice=="ACT":
        user_act = st.number_input("ACT Score", 1, 36, 35, 1)

    # Ethnicity & Gender filters
    user_eth = st.selectbox("Ethnicity", 
        ["No filter","Asian","White","Black","Hispanic","Native American","Middle Eastern","Other"]
    )
    user_gen = st.selectbox("Gender", ["No filter","Male","Female"])

    # perform filtering
    try:
        res = match_profiles(df, user_gpa, user_sat, user_act, user_eth, user_gen)
    except:
        res = pd.DataFrame()

    if res.empty:
        st.warning("0 matches found.")
    else:
        st.success(f"Found {len(res)} matching profiles:")
        for _, r in res.iterrows():
            st.markdown(f"""
            <div style="font-size:14px; line-height:1.4; margin-bottom:8px;">
              • <a href="{r['url']}" target="_blank">{r['url']}</a><br>
              GPA: {r['GPA']:.2f} | SAT: {r['SAT_Score']} | ACT: {r['ACT_Score']}<br>
              Ethnicity: {r['Ethnicity']} | Gender: {r['Gender']}<br>
              Acceptances: {r['acc_clean']}
            </div>
            """, unsafe_allow_html=True)

if __name__=="__main__":
    main()
