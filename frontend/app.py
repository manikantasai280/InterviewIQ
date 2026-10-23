import requests
import streamlit as st

BACKEND_URL = "http://127.0.0.1:8000"

# Configure the website (must be the first Streamlit command)
st.set_page_config(
    page_title="InterviewIQ | AI Interviewer",
    page_icon="🎯",
    layout="wide",
)

# Our website's visual design
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

.stApp {
    background: #F7F8FC;
    color: #172033;
    font-family: 'Inter', sans-serif;
}

.block-container {
    max-width: 1150px;
    padding-top: 2rem;
    padding-bottom: 4rem;
}

#MainMenu, footer {
    visibility: hidden;
}

header[data-testid="stHeader"] {
    background: transparent;
}

.hero {
    background: linear-gradient(135deg, #111B3C, #353B83);
    color: white;
    padding: 64px 48px;
    border-radius: 24px;
    animation: fadeUp 0.8s ease-out both;
}

.eyebrow {
    color: #BFC8FF;
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 2px;
    margin-bottom: 20px;
}

.hero h1 {
    font-size: clamp(34px, 5vw, 58px);
    line-height: 1.12;
    letter-spacing: -2px;
    margin: 0 0 20px 0;
    color: white;
}

.hero h1 span {
    color: #AEB9FF;
}

.hero p {
    color: #E0E5FF;
    font-size: 17px;
    line-height: 1.8;
    max-width: 650px;
}

.section-title {
    font-size: 25px;
    font-weight: 800;
    margin: 38px 0 8px 0;
    color: #172033;
}

.section-subtitle {
    color: #667085;
    margin-bottom: 24px;
    font-size: 15px;
}

.feature-card {
    background: white;
    border: 1px solid #E7EAF2;
    border-radius: 18px;
    padding: 26px;
    min-height: 185px;
    transition: transform 0.2s ease, box-shadow 0.2s ease;
    animation: fadeUp 0.8s ease-out both;
}

.feature-card:hover {
    transform: translateY(-4px);
    box-shadow: 0 12px 30px rgba(28, 39, 85, 0.08);
}

.feature-icon {
    font-size: 29px;
    margin-bottom: 15px;
}

.feature-card h3 {
    font-size: 18px;
    color: #202A44;
    margin-bottom: 10px;
}

.feature-card p {
    color: #667085;
    font-size: 14px;
    line-height: 1.7;
}

@keyframes fadeUp {
    from {
        opacity: 0;
        transform: translateY(14px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}

@media (prefers-reduced-motion: reduce) {
    *, *::before, *::after {
        animation: none !important;
        transition: none !important;
    }
}
</style>
""", unsafe_allow_html=True)

# Main hero section
st.markdown("""
<div class="hero">
    <div class="eyebrow">AI-POWERED INTERVIEW PLATFORM</div>
    <h1>Smarter interviews.<br>
    <span>Better hiring decisions.</span></h1>
    <p>
        Meet InterviewIQ — a platform designed to help recruiters
        create structured interviews, evaluate candidate answers,
        and understand skills through evidence-based AI assistance.
    </p>
</div>
""", unsafe_allow_html=True)

# Features section
st.markdown("""
<div class="section-title">Everything you need to interview smarter</div>
<div class="section-subtitle">
    One platform for structured interviews and clearer evaluation.
</div>
""", unsafe_allow_html=True)

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("""
    <div class="feature-card">
        <div class="feature-icon">✦</div>
        <h3>AI-Generated Questions</h3>
        <p>Create role-focused interview questions
        based on job requirements and required skills.</p>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown("""
    <div class="feature-card">
        <div class="feature-icon">◎</div>
        <h3>Structured Interviews</h3>
        <p>Give candidates a clear interview experience
        with organized questions and progress tracking.</p>
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown("""
    <div class="feature-card">
        <div class="feature-icon">↗</div>
        <h3>Evidence-Based Reports</h3>
        <p>Review answer evidence, strengths, skill gaps,
        and AI-assisted evaluations.</p>
    </div>
    """, unsafe_allow_html=True)

# Backend connection check
st.divider()
st.subheader("Backend connection")

if st.button("Check backend status"):
    try:
        response = requests.get(f"{BACKEND_URL}/health", timeout=5)
        response.raise_for_status()
        data = response.json()
        st.success(f"{data['message']} (environment: {data['environment']})")
    except requests.exceptions.RequestException:
        st.error("Cannot reach the backend. Is the FastAPI server running on port 8000?")

st.caption(
    "InterviewIQ · Smarter Interviews. Evidence-Based Hiring."
)