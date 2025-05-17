import streamlit as st
import pandas as pd
import re
import string
import difflib

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
    df['Eth_norm'] = df['Ethnicity'].apply(normalize_ethnicity)
    df['Gen_norm'] = df['Gender'].apply(normalize_gender)
    df['acc_clean'] = df['acceptances'].apply(clean_acceptances)
    d = df[df['acc_clean']!=""].copy()

    if eth!="No filter":
        d = d[d['Eth_norm']==eth.lower()]
    if gen!="No filter":
        d = d[d['Gen_norm']==gen.lower()]
    if use_gpa and gpa is not None:
        d = d[(d['GPA']>=gpa-0.05)&(d['GPA']<=gpa+0.05)]
    if sat is not None:
        d = d[d['SAT_Score'].apply(lambda x: abs(x-sat)<=30 if not pd.isna(x) else False)]
    if act is not None:
        d = d[d['ACT_Score'].apply(lambda x: abs(x-act)<=1 if not pd.isna(x) else False)]

    d['EC_matches'] = [[] for _ in range(len(d))]

    if ec_query.strip():
        keywords = extract_keywords(ec_query)
        if keywords:
            def check_row(ec_text):
                if pd.isna(ec_text):
                    return False, []
                ec_lower = ec_text.lower()
                hits = [kw for kw in keywords if kw in ec_lower]
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
     @st.cache_data
    def load_data():
        url = "https://raw.githubusercontent.com/vikram-dev1125/college-admissions-matcher/refs/heads/main/master_data.csv"
        return pd.read_csv(url)
        
        df = load_data()
    st.markdown("""
    <div style='text-align:center; margin-bottom:1.5rem;'>
      <h1 style='color:#6A0DAD; font-size:3em; margin-bottom:0;'>MatchMyApp</h1>
      <p style='color:#DAA520; font-size:1.3em; font-weight:bold;'>Find your college application twin!</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div style='font-size:1.05rem; color:white; margin-bottom:2.5rem; line-height:1.7; text-align:left;'>
      Whether you're a rising senior preparing for college applications, a college data enthusiast looking for acceptance data, or a doomscroller on Reddit, this app is for you!
      <br><br>
      Trained on a large dataset of 2900 (and growing!) real applicant profiles sourced from <i>r/collegeresults</i>, the matching algorithm will find you your college application twin, every single time.
      <br><br>
      More features to come, including extracurricular advice, essay review systems, and a fun data corner for stats nerds! All supported by data, and lots of it!
    </div>
    """, unsafe_allow_html=True)

    df = load_data()
    tabs = st.tabs(["Profile Filter", "Filter by College Acceptances", "College List Wizard"])

    with tabs[0]:
        st.markdown("#### Enter your profile (leave filters blank to skip):")
        use_gpa = st.checkbox("Filter by GPA", value=True)
        if use_gpa:
            gpa_s = st.slider("GPA (max 4.0)", 0.0, 4.0, 4.0, 0.01)
            gpa_m = st.number_input("Or enter GPA manually", 0.0, 4.0, gpa_s, 0.01)
            user_gpa = gpa_m if gpa_m != gpa_s else gpa_s
        else:
            user_gpa = None

        score_choice = st.selectbox("Score filter", ["No filter","SAT","ACT"])
        user_sat = user_act = None
        if score_choice=="SAT":
            user_sat = st.number_input("SAT Score",400,1600,1580,10)
        elif score_choice=="ACT":
            user_act = st.number_input("ACT Score",1,36,35,1)

        user_eth = st.selectbox("Ethnicity", ["No filter","Asian","White","Black","Hispanic","Native American","Middle Eastern","Other"])
        user_gen = st.selectbox("Gender", ["No filter","Male","Female"])

        ec_query = st.text_area(
            "Describe your extracurriculars:",
            placeholder="e.g., robotics club, varsity soccer, volunteer tutoring",
            height=80,
        )

        res = match_profiles(df, user_gpa, user_sat, user_act, user_eth, user_gen, ec_query, use_gpa=use_gpa)
        display_results(res)

    with tabs[1]:
        st.markdown("#### Filter profiles accepted to the following college(s) (comma separated):")
        college_input = st.text_input("Enter college name(s)")
        if college_input.strip():
            res = filter_by_colleges(df, college_input)
            display_results(res)
        else:
            st.info("Enter one or more college names to see matching acceptances.")

    with tabs[2]:
        st.header("🎯 College Matchmaker")
        st.markdown("Find schools where students like you got in!")
    
        # Load data from GitHub
    
        # --- User Input ---
        gpa = st.slider("Your GPA (unweighted, max 4.0)", 0.0, 4.0, 4.0, 0.01)
    
        score_type = st.selectbox("Test Type", ["None", "SAT", "ACT"])
        sat_score = act_score = None
        if score_type == "SAT":
            sat_score = st.number_input("SAT Score", 400, 1600, 1500, 10)
        elif score_type == "ACT":
            act_score = st.number_input("ACT Score", 1, 36, 34, 1)
    
        residency = st.selectbox("Are you applying as a...", ["Domestic", "International"])
    
        ec_input = st.text_area("Your extracurriculars (keywords):", height=60, placeholder="e.g. math club, robotics, research")
        major_input = st.text_input("Intended Major (optional):", placeholder="e.g. Computer Science")
    
        email = st.text_input("Your Email (to receive a PDF summary):", placeholder="e.g. you@example.com")
        match_button = st.button("🎉 Match Me!")
    
        # --- Matching Logic ---
        def match_profiles(df, gpa, sat=None, act=None, residency=None, ec_keywords=None, major_keywords=None):
            import difflib
    
            filtered = df.copy()
    
            # Academic filters
            filtered = filtered[filtered["GPA"] >= gpa - 0.2]
            if sat is not None:
                filtered = filtered[filtered["SAT_Score"] >= sat - 40]
            if act is not None:
                filtered = filtered[filtered["ACT_Score"] >= act - 2]
    
            # Residency filter
            if residency:
                filtered = filtered[filtered["Residency"].str.lower() == residency.lower()]
    
            # EC match
            if ec_keywords:
                filtered["ec_score"] = filtered["parsed_ECs"].apply(
                    lambda x: difflib.SequenceMatcher(None, ec_keywords.lower(), str(x).lower()).ratio()
                )
            else:
                filtered["ec_score"] = 0.5
    
            # Major match
            if major_keywords:
                filtered["major_score"] = filtered["Major"].apply(
                    lambda x: difflib.SequenceMatcher(None, major_keywords.lower(), str(x).lower()).ratio()
                )
            else:
                filtered["major_score"] = 0.5
    
            # Combined relevance score
            filtered["match_score"] = (filtered["ec_score"] + filtered["major_score"]) / 2
            filtered = filtered.sort_values("match_score", ascending=False)
    
            return filtered.head(10)
    
        # --- Run & Display ---
        if match_button:
            if not email or "@" not in email:
                st.error("Please enter a valid email to see your matches.")
            else:
                matches = match_profiles(
                    df, gpa, sat_score, act_score, residency,
                    ec_keywords=ec_input, major_keywords=major_input
                )
    
                if matches.empty:
                    st.warning("No matches found. Try adjusting your profile.")
                else:
                    st.success("🎓 Top Matches Based on Your Profile:")
                    for _, row in matches.iterrows():
                        st.markdown(
                            f"**{row['title']}**\n"
                            f"- GPA: {row['GPA']}, SAT: {row['SAT_Score']}, ACT: {row['ACT_Score']}\n"
                            f"- Major: {row['Major']}\n"
                            f"- ECs: {row['parsed_ECs']}\n"
                            f"- Residency: {row['Residency']}"
                        )
    
                    # Save emails locally (for now)
                    with open("emails_collected.txt", "a") as f:
                        f.write(email.strip() + "\n")


if __name__=="__main__":
    main()
