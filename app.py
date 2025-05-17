import streamlit as st
import pandas as pd
import re
import string
from difflib import get_close_matches
from collections import Counter
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
import io

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
            ec_hits = r.get('EC_matches', [])
            ec_line = f"<br><b>ECs in common:</b> {', '.join(ec_hits)}" if ec_hits else ""
            st.markdown(f"""
            <div style="font-size:14px; line-height:1.4; margin-bottom:8px;">
              • <a href="{r['url']}" target="_blank">{r['url']}</a><br>
              GPA: {r['GPA']:.2f} | SAT: {r['SAT_Score']} | ACT: {r['ACT_Score']}<br>
              Ethnicity: {r['Ethnicity']} | Gender: {r['Gender']}<br>
              Acceptances: {r['acc_clean']}{ec_line}
            </div>
            """, unsafe_allow_html=True)

# ——— New College List Wizard ———
def is_valid_email(email):
    return re.match(r"[^@]+@[^@]+\.[^@]+", email)

def normalize_residency(residency):
    if pd.isna(residency):
        return "other"
    r = residency.lower()
    if "domestic" in r:
        return "domestic"
    if "international" in r:
        return "international"
    return "other"

def fuzzy_match_major(user_major, majors_list, cutoff=0.6):
    if not user_major.strip():
        return None
    matches = get_close_matches(user_major.lower(), [m.lower() for m in majors_list], n=1, cutoff=cutoff)
    return matches[0] if matches else None

from collections import Counter

def college_list_wizard(df):
    st.markdown("### 🎓 College List Wizard (DEBUG MODE)")
    st.info("Provide your academic profile and we’ll find matching accepted colleges!")

    # Inputs
    gpa = st.text_input("Enter your GPA (0.0–4.0):")
    test_score = st.text_input("Enter SAT (400–1600) or ACT (1–36):")
    major = st.text_input("Intended Major (please spell out full major, e.g., 'Computer Science'):")
    ecs = st.text_area("Describe your Extracurriculars:")
    domestic = st.checkbox("Domestic student? (leave unchecked for International)")
    email = st.text_input("Enter your Email:")

    # Email validation
    if email and not is_valid_email(email):
        st.warning("Please enter a valid email address.")

    # Parse GPA
    try:
        gpa_val = float(gpa)
    except:
        gpa_val = None

    # Parse test score
    sat_val = act_val = None
    if test_score.strip().isdigit():
        sc = int(test_score.strip())
        if 1 <= sc <= 36:
            act_val = sc
            sat_val = sc * 45
        elif 400 <= sc <= 1600:
            sat_val = sc

    # Simple keyword match major (full major spelled out)
    def match_major(user_major, majors_list):
        user_major_lower = user_major.strip().lower()
        for m in majors_list:
            if user_major_lower in m.lower():
                return m  # return exact df major spelling
        return None

    majors_list = df['Major'].dropna().unique()
    matched_major = match_major(major, majors_list)

    # Match Me! button
    match_button = st.button("Match Me!", disabled=not is_valid_email(email))
    if not match_button:
        return

    # Start filtering
    df2 = df.copy()
    st.write("🔹 Initial DataFrame:", df2.shape)

    # Residency
    df2['Residency_norm'] = df2['Residency'].apply(normalize_residency)
    target_res = "domestic" if domestic else "international"
    df2 = df2[df2['Residency_norm'] == target_res]
    st.write(f"🔹 After Residency filter ({target_res}):", df2.shape)
    st.dataframe(df2[['Residency','Residency_norm']].head())

    # GPA
    if gpa_val is not None:
        df2 = df2[(df2['GPA'] >= gpa_val - 0.1) & (df2['GPA'] <= gpa_val + 0.1)]
        st.write(f"🔹 After GPA filter (±0.1 around {gpa_val}):", df2.shape)
        st.dataframe(df2[['GPA']].head())

    # SAT/ACT
    def sat_act_match(row):
        sat_ok = sat_val is not None and not pd.isna(row['SAT_Score']) and abs(row['SAT_Score'] - sat_val) <= 30
        act_ok = act_val is not None and not pd.isna(row['ACT_Score']) and abs(row['ACT_Score'] - act_val) <= 1
        conv_ok = act_val is not None and not pd.isna(row['SAT_Score']) and abs(row['SAT_Score'] - act_val*45) <= 30
        return sat_ok or act_ok or conv_ok

    if sat_val is not None or act_val is not None:
        df2 = df2[df2.apply(sat_act_match, axis=1)]
        st.write("🔹 After SAT/ACT filter:", df2.shape)
        st.dataframe(df2[['SAT_Score','ACT_Score']].head())

    # Major filter
    if matched_major:
        df2 = df2[df2['Major'] == matched_major]
        st.write(f"🔹 After Major filter (matched: {matched_major}):", df2.shape)
        st.dataframe(df2[['Major']].head())
    else:
        st.warning("Major not found in database. No major filter applied.")

    # Extracurriculars
    ec_keys = extract_keywords(ecs)
    if ec_keys:
        df2 = df2[df2['parsed_ECs'].apply(lambda txt: any(kw in str(txt).lower() for kw in ec_keys))]
        st.write(f"🔹 After EC keyword filter (keywords: {ec_keys}):", df2.shape)
        st.dataframe(df2[['parsed_ECs']].head())

    # Extract clean acceptances after all filters are applied
    indicators = [
        "university", "college", "institute", "school",
        "academy", "tech", "polytechnic", "poly", "mit",
        "stanford", "harvard", "princeton", "yale"
        # add more top 40 schools and top 10 LACs if you want here
    ]

    def extract_clean_colleges(raw):
        if not isinstance(raw, str) or not raw.strip():
            return []
        parts = re.split(r"[\n,]+", raw)
        cleaned = []
        for p in parts:
            seg = p.strip()
            if not seg:
                continue
            # drop comments in parentheses
            name = seg.split("(", 1)[0].strip()
            low = name.lower()
            if any(ind in low for ind in indicators):
                cleaned.append(name[:100])  # limit to 100 chars max
        return cleaned

    df2["cleaned_list"] = df2["acceptances"].apply(extract_clean_colleges)
    all_schools = [school for sub in df2["cleaned_list"] for school in sub]

    if not all_schools:
        st.warning("No clean acceptances found.")
        return

    # count frequency
    counts = Counter(all_schools)
    st.markdown("#### Accepted Colleges Summary:")
    for school, cnt in counts.most_common(20):
        st.markdown(f"- **{school}** — {cnt} acceptance(s)")

    if df2.empty:
        st.warning("No matches found.")
        return

    st.markdown("---\n#### Matched Profiles:")
    for _, r in df2.iterrows():
        ec_hits = [kw for kw in ec_keys if kw in str(r['parsed_ECs']).lower()]
        st.markdown(f"""
        • [{r['url']}]({r['url']})  
          GPA: {r['GPA']:.2f} | SAT: {r['SAT_Score']} | ACT: {r['ACT_Score']}  
          Major: {r['Major']} | Residency: {r['Residency_norm']}  
          Acceptances: {r['acceptances']}  
          EC hits: {', '.join(ec_hits)}
        """)

    # Log email
    with open("emails_collected.txt", "a") as f:
        f.write(email + "\n")









# ——— Main App ———
def main():
    st.set_page_config(page_title="MatchMyApp", layout="centered")
    st.markdown("""
    <div style='text-align:center;'>
      <h1 style='color:#6A0DAD; font-size:3em;'>MatchMyApp</h1>
      <p style='color:#DAA520; font-size:1.2em;'>Find your college application twin!</p>
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

        user_eth = st.selectbox(
            "Ethnicity",
            ["No filter","Asian","White","Black","Hispanic","Native American","Middle Eastern","Other"],
        )
        user_gen = st.selectbox("Gender", ["No filter","Male","Female"])
        ec_query = st.text_area(
            "Describe your extracurriculars:",
            placeholder="e.g., robotics club, varsity soccer, volunteer tutoring",
            height=80,
        )

        res = match_profiles(
            df, user_gpa, user_sat, user_act,
            user_eth, user_gen, ec_query,
            use_gpa=use_gpa
        )
        display_results(res)

    with tabs[1]:
        st.markdown("#### Filter profiles accepted to the following college(s):")
        college_input = st.text_input("Enter college name(s), comma‑separated:")
        if college_input.strip():
            res = filter_by_colleges(df, college_input)
            display_results(res)
        else:
            st.info("Enter one or more college names to see matching acceptances.")

    with tabs[2]:
        college_list_wizard(df)

if __name__ == "__main__":
    main()
