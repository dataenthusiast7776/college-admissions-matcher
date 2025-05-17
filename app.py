    df = load_data()
    tabs = st.tabs(["Profile Filter", "Filter by College Acceptances", "Match Wizard"])

    with tabs[0]:
        st.markdown("#### Enter your profile (leave filters blank to skip):")
        ...
        # [unchanged original Profile Filter code]
        ...
        display_results(res)

    with tabs[1]:
        st.markdown("#### Filter profiles accepted to the following college(s) (comma separated):")
        ...
        # [unchanged original College Filter code]
        ...
        display_results(res)

    with tabs[2]:
        st.markdown("#### Match Wizard")
        st.info("Answer a few questions and we’ll find your closest matches.")

        # Wizard: GPA
        gpa_confirm = st.radio("Do you know your GPA?", ["Yes", "No"])
        if gpa_confirm == "Yes":
            wizard_gpa = st.slider("What is your GPA?", 0.0, 4.0, 3.8, 0.01)
        else:
            wizard_gpa = None

        # Wizard: Test Scores
        score_choice = st.radio("Did you take the SAT or ACT?", ["SAT", "ACT", "Neither"])
        wizard_sat = wizard_act = None
        if score_choice == "SAT":
            wizard_sat = st.number_input("Enter SAT Score", 400, 1600, 1400, 10)
        elif score_choice == "ACT":
            wizard_act = st.number_input("Enter ACT Score", 1, 36, 30, 1)

        # Wizard: Ethnicity and Gender
        wizard_eth = st.selectbox("Choose your ethnicity", ["No filter", "Asian", "White", "Black", "Hispanic", "Native American", "Middle Eastern", "Other"])
        wizard_gen = st.selectbox("Choose your gender", ["No filter", "Male", "Female"])

        # Wizard: ECs
        wizard_ecs = st.text_area("Briefly describe your extracurriculars:", height=80)

        # Submit button
        if st.button("Find Matches", key="wizard_submit"):
            res = match_profiles(
                df, wizard_gpa, wizard_sat, wizard_act,
                wizard_eth, wizard_gen, wizard_ecs,
                use_gpa=(wizard_gpa is not None)
            )
            display_results(res)
