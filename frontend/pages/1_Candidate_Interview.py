import requests
import streamlit as st

BACKEND_URL = "http://127.0.0.1:8000"

# trust_env=False makes requests ignore your college proxy for local calls
http = requests.Session()
http.trust_env = False

st.set_page_config(page_title="Candidate Interview | InterviewIQ", page_icon="🎯")
st.title("🎯 Candidate Interview")

ss = st.session_state
ss.setdefault("access", None)    # interview id + access code, once entered
ss.setdefault("question", None)  # the question currently shown
ss.setdefault("finished", False)


def call(path: str, payload: dict):
    """Send one request to the backend. Returns the JSON, or None after showing an error."""
    try:
        r = http.post(f"{BACKEND_URL}{path}", json=payload, timeout=180)
    except requests.exceptions.RequestException:
        st.error("Cannot reach the backend. Is it running on port 8000?")
        return None
    if r.status_code != 200:
        try:
            st.error(r.json().get("detail", "Something went wrong."))
        except ValueError:
            st.error("The server had an error. Please try again.")
        return None
    return r.json()


# Screen 1: enter ID and code
if ss.access is None:
    with st.form("login"):
        interview_id = st.number_input("Interview ID", min_value=1, step=1)
        code = st.text_input("Access code")
        go = st.form_submit_button("Start interview")

    if go:
        access = {"interview_id": int(interview_id), "access_code": code.strip()}
        status = call("/candidate/status", access)
        if status:
            if status["status"] == "waiting":
                mins = status["seconds_until_start"] // 60
                st.info(f"Your interview has not started yet. It begins in about {mins} minutes.")
            elif status["status"] == "completed":
                ss.access, ss.finished = access, True
                st.rerun()
            else:
                with st.spinner("Preparing your first question..."):
                    started = call("/candidate/start", access)
                if started:
                    ss.access = access
                    ss.finished = started["finished"]
                    ss.question = started.get("question")
                    st.rerun()

# Screen 3: interview finished
elif ss.finished:
    st.success("Thank you! Your interview is complete. The recruiter will review your results.")

# Screen 2: question and answer
else:
    st.subheader("Question")
    st.write(ss.question)
    with st.form("answer", clear_on_submit=True):
        answer = st.text_area("Your answer", height=200)
        sent = st.form_submit_button("Submit answer")

    if sent:
        if not answer.strip():
            st.warning("Please type an answer first.")
        else:
            with st.spinner("Evaluating your answer... this can take up to 30 seconds"):
                reply = call("/candidate/answer", {**ss.access, "answer": answer})
            if reply:
                ss.finished = reply["finished"]
                ss.question = reply.get("question")
                st.rerun()
                