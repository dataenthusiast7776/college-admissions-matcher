import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Fun Data Corner", layout="wide")

@st.cache_data
def load_data():
    df = pd.read_csv("master_data.csv")

    # Adjust SAT/ACT
    df['SAT_Adjusted'] = df.apply(
        lambda r: r['SAT_Score'] if pd.notna(r['SAT_Score']) else (
            r['ACT_Score'] * 45 if pd.notna(r['ACT_Score']) else None
        ),
        axis=1
    )
    return df

def scatter_ivy(df):
    ivies = ['Harvard', 'Yale', 'Princeton', 'Columbia', 'Cornell',
             'Brown', 'Dartmouth', 'Upenn']

    selected = st.selectbox("Choose an Ivy League school:", ivies)

    school_df = df[df['acceptances'].str.contains(selected, case=False, na=False)]
    school_df = school_df.dropna(subset=['GPA', 'SAT_Adjusted', 'url'])
    if school_df.empty:
        st.warning(f"No data available for {selected}")
        return

    fig = px.scatter(
        school_df,
        x='GPA',
        y='SAT_Adjusted',
        custom_data=['url'],
        title=f"GPA vs SAT/ACT (converted) — {selected}",
        labels={'GPA': 'GPA', 'SAT_Adjusted': 'SAT or ACT*45'},
        template='plotly_dark'
    )

    fig.update_traces(
        marker=dict(size=10, line=dict(width=1, color='white')),
        hovertemplate="<b>GPA:</b> %{x}<br><b>SAT:</b> %{y}<br><b>Click to open post</b>",
    )

    fig.update_layout(
        xaxis=dict(range=[3.0, 4.0]),
        yaxis_title="SAT or ACT*45",
        plot_bgcolor='rgb(17,17,17)',
        paper_bgcolor='rgb(17,17,17)',
        font_color='white'
    )

    st.plotly_chart(fig, use_container_width=True)

    st.markdown("Click any point on the graph to open its Reddit post:")

    clicked = st.session_state.get("clicked_url", None)
    if clicked:
        st.markdown(f"[Open Reddit Post]({clicked})")

    # JS to capture click event
    st.markdown("""
        <script>
        const plots = window.parent.document.querySelectorAll(".js-plotly-plot");
        plots.forEach(plot => {
            plot.on('plotly_click', function(data){
                const url = data.points[0].customdata[0];
                window.open(url, '_blank');
            });
        });
        </script>
    """, unsafe_allow_html=True)

def main():
    st.title("🎲 Fun Data Corner")

    st.markdown("""
    Hello fellow data nerds! Here you can find numerous different angles of data visualization from the dataset I am using, updated as my dataset improves.

    I do want to note that since the data were taken from a subreddit dedicated to college results, there is a volunteer response bias in play that definitely overestimates all metrics for the typical student. Nevertheless, there aren't any better sources for this data that I could find, so we will have to roll with it!
    """)

    st.subheader("2. GPA vs SAT/ACT Scores (clickable by school)")

    df = load_data()
    scatter_ivy(df)

if __name__ == "__main__":
    main()
