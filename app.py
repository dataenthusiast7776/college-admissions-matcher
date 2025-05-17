import streamlit as st
import pandas as pd

@st.cache_data
def load_data():
    url = "https://raw.githubusercontent.com/vikram-dev1125/college-admissions-matcher/refs/heads/main/master_data.csv"
    return pd.read_csv(url)

def match_profiles(df, gpa, sat=None, act=None, residency=None, ec_keywords=None, major_keywords=None):
    import difflib

    filtered = df.copy()

    # Academic filters (allow slight tolerance)
    if gpa is not None:
        filtered = filtered[filtered["GPA"] >= gpa - 0.2]
    if sat is not None:
        filtered = filtered[filtered["SAT_Score"] >= sat - 40]
    if act is not None:
        filtered = filtered[filtered["ACT_Score"] >= act - 2]

    # Residency filter
    if residency:
        filtered = filtered[filtered["Residency"].str.lower() == residency.lower()]

    # EC matching score
    if ec_keywords:
        filtered["ec_score"] = filtered["parsed_ECs"].apply(
            lambda x: difflib.SequenceMatcher(None, ec_keywords.lower(), str(x).lower()).ratio()
        )
    else:
        filtered["ec_score"] = 0.5

    # Major matching score
    if major_keywords:
        filtered["major_score"] = filtered["Major"].apply(
            lambda x: difflib.SequenceMatcher(None, major_keywords.lower(), str(x).lower()).ratio()
        )
    else:
        filtered["major_score"] = 0.5

    # Combine scores
    filtered["match_score"] = (filtered["ec_score"] + filtered["major_score"]) / 2
    filtered = filtered.sort_values("match_score", ascending=False)

    return filtered.head(10)

def display_results(df):
    if df.empty:
        st.warning("No results found with current filters.")
        return
    for _, r in df.iterrows():
        ec_line = f"<br>ECs: {r['parsed_ECs']}" if r['parsed_ECs'] else ""
        st.markdown(f"""
            <div style="font-size:14px; line-height:1.4; margin-bottom:8px;">
              • <a href="{r['url']}" target="_blank">{r['title']}</a><br>
              GPA: {r['GPA']:.2f} | SAT: {r['SAT_Score']} | ACT: {r['ACT_Score']}<br>
              Ethnicity: {r['Ethnicity']} | Gender: {r['Gender']}<br>
              Acceptances: {r.get('acceptances', 'N/A')}{ec_line}
            </div>
            """, unsafe_allow_html=True)

def filter_by_colleges(df, college_input):
    colleges = [c.strip().lower() for c in college_input.split(",")]
    filtered = df[df["acceptances"].str.lower().apply(lambda x: any(col in x for col in colleges))]
    return filtered

def main():
    st.set_page_config(page_title="MatchMyApp - College Application Twin Finder", layout="wide")
    df = load_data()

    st.markdown("""
    <div style='text-align:center; margin-bottom:1.5rem;'>
      <h1 style='color:#6A0DAD; font-size:3em; margin-bottom:0;'>MatchMyApp</h1>
      <p style='color:#DAA520; font-size:1.3em; font-weight:bold;'>Find your college application twin!</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div style='font-size:1.05rem; color:#eee; margin-bottom:2.5rem; line-height:1.7; text-align:left;'>
      Whether you're a rising senior preparing for college applications, a college data enthusiast looking for acceptance data, or a doomscroller on Reddit, this app is for you!
      <br><br>
      Trained on a large dataset of 2900 (and growing!) real applicant profiles sourced from <i>r/collegeresults</i>, the matching algorithm will find you your college application twin, every single time.
      <br><br>
      More features to come, including extracurricular advice, essay review systems, and a fun data corner for stats nerds! All supported by data, and lots of it!
    </div>
    """, unsafe_allow_html=True)

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

        score_choice = st.selectbox("Score filter", ["No filter", "SAT", "ACT"])
        user_sat = user_act = None
        if score_choice == "SAT":
            user_sat = st.number_input("SAT Score", 400, 1600, 1580, 10)
        elif score_choice == "ACT":
            user_act = st.number_input("ACT Score", 1, 36, 35, 1)

        user_eth = st.selectbox("Ethnicity", ["No filter", "Asian", "White", "Black", "Hispanic", "Native American", "Middle Eastern", "Other"])
        user_gen = st.selectbox("Gender", ["No filter", "Male", "Female"])

        ec_query = st.text_area(
            "Describe your extracurriculars:",
            placeholder="e.g., robotics club, varsity soccer, volunteer tutoring",
            height=80,
        )

        res = match_profiles(df, user_gpa, user_sat, user_act, None, ec_query, None, use_gpa=use_gpa)
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

        # --- Run Matching ---
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

                    # Save emails locally (basic signup)
                    with open("emails_collected.txt", "a") as f:
                        f.write(email.strip() + "\n")

if __name__ == "__main__":
    main()
