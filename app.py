import streamlit as st
import pandas as pd
import re
import string

# ——— Stopwords & Keyword Extraction ———
STOPWORDS = {
    "a","an","the","and","or","but","if","then","with","on","in",
    "at","by","for","of","to","from","is","are","was","were","it",
    "this","that","these","those","as","be","has","have","had","i",
    "you","he","she","we","they","them","his","her","my","your",
}

def extract_keywords(text):
    text = text.translate(str.maketrans("", "", string.punctuation))
    tokens = text.lower().split()
    return [t for t in tokens if t not in STOPWORDS]

# ——— Normalization Helpers ———
def normalize_ethnicity(ethnicity):
    if pd.isna(ethnicity):
        return "unknown"
    e = ethnicity.lower()
    if any(x in e for x in ["indian","south asian","asian"]):
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
    if g in ['male','m']:
        return 'male'
    if g in ['female','f']:
        return 'female'
    return 'unknown'

def clean_acceptances(raw):
    if pd.isna(raw) or not raw.strip():
        return ""
    parts = re.split(r"[\n,]+", raw)
    bad_kw = {
        "club","volunteer","internship","hook","income","essay",
        "activity","award","reflection","summary","miscellaneous",
        "consideration","recommendation","research","grades"
    }
    school_kw = {
        "university","college","institute","state","academy","school",
        "tech","polytechnic","poly","mit","stanford","harvard","princeton","yale"
    }
    good = []
    for p in parts:
        pl = p.strip().lower()
        if not pl or any(b in pl for b in bad_kw):
            continue
        if any(s in pl for s in school_kw) or pl in {"ea","ed","rea","rd"} or len(pl.split())<=8:
            good.append(p.strip())
    joined = ", ".join(good)
    return joined if len(joined)<=250 else ""

def match_profiles(df, gpa, sat, act, eth, gen, ec_query, use_gpa=True):
    # normalize & base filters
    df['Eth_norm'] = df['Ethnicity'].apply(normalize_ethnicity)
    df['Gen_norm'] = df['Gender'].apply(normalize_gender)
    df['acc_clean'] = df['acceptances'].apply(clean_acceptances)
    d = df[df['acc_clean']!=""].copy()

    # demog filters
    if eth!="No filter":
        d = d[d['Eth_norm']==eth.lower()]
    if gen!="No filter":
        d = d[d['Gen_norm']==gen.lower()]

    # GPA filter ±0.05 if enabled
    if use_gpa and gpa is not None:
        d = d[(d['GPA']>=gpa-0.05)&(d['GPA']<=gpa+0.05)]

    # score filters
    if sat is not None:
        d = d[d['SAT_Score'].apply(lambda x: abs(x-sat)<=30 if not pd.isna(x) else False)]
    if act is not None:
        d = d[d['ACT_Score'].apply(lambda x: abs(x-act)<=1 if not pd.isna(x) else False)]

    # init EC_matches
    d['EC_matches'] = [[] for _ in range(len(d))]

    # EC keyword filtering
    if ec_query.strip():
        keywords = extract_keywords(ec_query)
        if keywords:
            def check_row(ec_text):
                if pd.isna(ec_text):
                    return False, []
                ec_lower = ec_text.lower()
                hits = [kw for kw in keywords if kw in ec_lower]
                # require at least 2 hits if user provided ≥2 keywords
                if len(keywords)>=2:
                    return (len(hits)>=2, hits)
                return (len(hits)>=1, hits)
            mask = d['parsed_ECs'].apply(lambda txt: check_row(txt)[0])
            d = d[mask].copy()
            d['EC_matches'] = d['parsed_ECs'].apply(lambda txt: check_row(txt)[1])

    return d[['url','GPA','SAT_Score','ACT_Score','Ethnicity','Gender','acc_clean','EC_matches']]

def filter_by_colleges(df, colleges_input):
    cols = [c.strip().lower() for c in colleges_input.split(",") if c.strip()]
    d = df[df['acc_clean']!=""]
    for c in cols:
        d = d[d['acc_clean'].str.lower().str.contains(c, na=False)]
    return d[['url','GPA','SAT_Score','ACT_Score','Ethnicity','Gender','acc_clean','parsed_ECs']]

@st.cache_data
def load_data():
    try:
        return pd.read_csv(
            "https://raw.githubusercontent.com/vikram-dev1125/college-admissions-matcher/refs/heads/main/master_data.csv"
        )
    except:
        st.warning("Could not load remote data, using local master_data_with_ECs.csv")
        return pd.read_csv("master_data_with_ECs.csv")

def display_results(res):
    if res.empty:
        st.warning("0 matches found.")
    else:
        st.success(f"Found {len(res)} matching profiles:")
        for _, r in res.iterrows():
            ec_hits = r['EC_matches'] if 'EC_matches' in r.index else []
            ec_line = f"<br><b>ECs in common:</b> {', '.join(ec_hits)}" if ec_hits else ""
            st.markdown(f"""
            <div style="font-size:14px; line-height:1.4; margin-bottom:8px;">
              • <a href="{r['url']}" target="_blank">{r['url']}</a><br>
              GPA: {r['GPA']:.2f} | SAT: {r['SAT_Score']} | ACT: {r['ACT_Score']}<br>
              Ethnicity: {r['Ethnicity']} | Gender: {r['Gender']}<br>
              Acceptances: {r['acc_clean']}{ec_line}
            </div>
            """, unsafe_allow_html=True)

def main():
    st.markdown("""
    <div style='text-align:center; margin-bottom:1.5rem;'>
      <h1 style='color:#6A0DAD; font-size:3em; margin-bottom:0;'>MatchMyApp</h1>
      <p style='color:#DAA520; font-size:1.3em; font-weight:bold;'>Find your college application twin!</p>
    </div>
    """, unsafe_allow_html=True)

    df = load_data()
    tabs = st.tabs(["Profile Filter", "Filter by College Acceptances", "College List Wizard"])

    # ------- Tab 1 -------
    with tabs[0]:
        st.markdown("#### Enter your profile (leave filters blank to skip):")
        ...
        # Existing profile matcher logic
        ...

    # ------- Tab 2 -------
    with tabs[1]:
        st.markdown("#### Filter profiles accepted to the following college(s) (comma separated):")
        ...
        # Existing college name filter
        ...

    # ------- Tab 3: College List Wizard -------
    with tabs[2]:
        st.markdown("### 🎓 College List Wizard")

        st.markdown("##### Academic Info")
        gpa = st.slider("Unweighted GPA (4.0 scale)", 0.0, 4.0, 4.0, 0.01)
        test_optional = st.checkbox("I'm applying test-optional")
        sat = act = None
        if not test_optional:
            test_type = st.radio("Which test do you have?", ["SAT", "ACT"], horizontal=True)
            if test_type == "SAT":
                sat = st.number_input("SAT Score", 400, 1600, 1580, step=10)
            else:
                act = st.number_input("ACT Score", 1, 36, 35)

        st.markdown("##### Activities")
        ecs = st.text_area("Describe your extracurriculars:", height=80, placeholder="e.g., debate team, research intern, robotics")

        st.markdown("##### Budget")
        budget = st.number_input("Estimated annual college budget (in USD)", min_value=0, value=20000, step=1000)

        st.markdown("##### Preferences")
        location_pref = st.multiselect("Preferred location type(s)", ["Urban", "Suburban", "Rural"], default=["Urban", "Suburban"])
        size_pref = st.multiselect("Preferred school size", ["Small (<5K)", "Medium (5K–15K)", "Large (15K+)"], default=["Medium (5K–15K)"])

        st.markdown("##### International Options")
        canada = st.checkbox("Include Canadian universities?")
        uk = st.checkbox("Include UK universities?")
        other_intl = st.checkbox("Include other international options?")

        st.markdown("##### Dream School (optional)")
        dream_school = st.text_input("What's your dream school?")

        submit = st.button("Generate College List")

        if submit:
            st.success("Thanks! 🎉 This info will be used to generate your college list.")
            st.json({
                "GPA": gpa,
                "SAT": sat,
                "ACT": act,
                "Test-Optional": test_optional,
                "ECs": ecs,
                "Budget": budget,
                "Location": location_pref,
                "Size": size_pref,
                "Canada": canada,
                "UK": uk,
                "Other Intl": other_intl,
                "Dream School": dream_school,
            })
if __name__ == "__main__":
    main()
