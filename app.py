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
import os
import smtplib
from email.message import EmailMessage
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

import smtplib
from email.message import EmailMessage
import io
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.utils import ImageReader
from collections import Counter
import re
import pandas as pd

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

    if email and not is_valid_email(email):
        st.warning("Please enter a valid email address.")

    # Parsing inputs (gpa, test_score) omitted here for brevity (same as your original code)...

    # Match Me! button
    match_button = st.button("Match Me!", disabled=not is_valid_email(email))
    if not match_button:
        return

    # Your filtering logic here (same as your original code)...
    # Assume df2 is your filtered DataFrame after all filters applied

    # Prepare matched colleges summary (counts)
    all_schools = [school for sub in df2["cleaned_list"] for school in sub]
    counts = Counter(all_schools)
    matched_colleges = counts.most_common(20)

    # Prepare matched profiles list for PDF (simplify keys for example)
    matched_profiles = []
    for _, r in df2.iterrows():
        matched_profiles.append({
            "url": r["url"],
            "GPA": r["GPA"],
            "SAT": r["SAT_Score"],
            "ACT": r["ACT_Score"],
            "Major": r["Major"],
            "Residency": r["Residency_norm"],
            "Acceptances": r["acceptances"],
            "EC Hits": [kw for kw in extract_keywords(ecs) if kw in str(r['parsed_ECs']).lower()]
        })

    # User inputs summary for PDF
    user_inputs = {
        "GPA": gpa,
        "Test Score": test_score,
        "Major": major,
        "Extracurriculars": ecs,
        "Residency": "Domestic" if domestic else "International",
        "Email": email
    }

    # Generate PDF bytes
    pdf_buffer = generate_pdf(user_inputs, matched_colleges, matched_profiles)

    # Send email with PDF attached
    success, msg = send_email_with_pdf(
        to_email=email,
        subject="Your MatchMyApp College Match Report",
        body_text="Hi! Attached is your MatchMyApp report. Best of luck!",
        pdf_bytes=pdf_buffer.getvalue()
    )

    if success:
        st.success(msg)
    else:
        st.error(msg)

    # Log email
    with open("emails_collected.txt", "a") as f:
        f.write(email + "\n")


def generate_pdf(user_inputs, matched_colleges, matched_profiles, logo_path="logo.png"):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    # Logo
    if logo_path:
        try:
            logo = ImageReader(logo_path)
            c.drawImage(logo, width - 150, height - 80, width=100, preserveAspectRatio=True, mask='auto')
        except:
            pass  # Fail silently if logo isn't found

    c.setFont("Helvetica-Bold", 16)
    c.drawString(40, height - 50, "🎓 College List Match Report")

    y = height - 100
    c.setFont("Helvetica", 11)

    def write_line(text, indent=0, space=15):
        nonlocal y
        if y < 60:
            c.showPage()
            y = height - 50
        c.drawString(40 + indent, y, text)
        y -= space

    # User inputs
    write_line("Your Profile:")
    for k, v in user_inputs.items():
        write_line(f"{k}: {v}", indent=20)

    write_line("")
    write_line("Top Matched Colleges:")
    for school, count in matched_colleges:
        write_line(f"{school} — {count} acceptance(s)", indent=20)

    write_line("")
    write_line("Matched Reddit Profiles:")
    for profile in matched_profiles:
        write_line(f"{profile['url']}", indent=20)
        write_line(f"GPA: {profile['GPA']} | SAT: {profile['SAT']} | ACT: {profile['ACT']}", indent=40)
        write_line(f"Major: {profile['Major']} | Residency: {profile['Residency']}", indent=40)
        write_line(f"Acceptances: {profile['Acceptances']}", indent=40)
        write_line(f"EC Hits: {', '.join(profile['EC Hits'])}", indent=40)
        write_line("", indent=20)

    c.save()
    buffer.seek(0)
    return buffer


def send_email_with_pdf(to_email: str, subject: str, body_text: str, pdf_bytes: bytes, filename="MatchMyApp_Report.pdf"):
    import streamlit as st

    # Read email creds from Streamlit secrets
    email_user = st.secrets["email_user"]
    email_pass = st.secrets["email_password"]
    smtp_server = st.secrets.get("smtp_server", "smtp.gmail.com")
    smtp_port = st.secrets.get("smtp_port", 587)

    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = email_user
    msg['To'] = to_email
    msg.set_content(body_text)

    msg.add_attachment(pdf_bytes, maintype='application', subtype='pdf', filename=filename)

    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(email_user, email_pass)
            server.send_message(msg)
        return True, "Email sent successfully!"
    except Exception as e:
        return False, f"Failed to send email: {e}"


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
