from datetime import datetime, time

import requests
import streamlit as st

BACKEND_URL = "http://127.0.0.1:8000"

# trust_env=False makes requests ignore your college proxy for local calls
http = requests.Session()
http.trust_env = False

st.set_page_config(page_title="Recruiter | InterviewIQ", page_icon="🎯", layout="wide")
st.title("🎯 Recruiter Dashboard")

ss = st.session_state
ss.setdefault("token", None)


def api(method: str, path: str, **kwargs):
    """Call the backend with the login token. Returns JSON, or None after showing an error."""
    headers = {"Authorization": f"Bearer {ss.token}"} if ss.token else {}
    try:
        r = http.request(
            method, f"{BACKEND_URL}{path}", headers=headers, timeout=300, **kwargs
        )
    except requests.exceptions.RequestException:
        st.error("Cannot reach the backend. Is it running on port 8000?")
        return None
    if r.status_code == 401 and ss.token:
        ss.token = None
        st.warning("Your session expired. Please log in again.")
        st.rerun()
    if r.status_code >= 400:
        try:
            detail = r.json().get("detail", "Something went wrong.")
        except ValueError:
            detail = "The server had an error. Please try again."
        st.error(detail if isinstance(detail, str) else "Please check your input.")
        return None
    return r.json()


# ---------- Login / register ----------
if ss.token is None:
    login_tab, register_tab = st.tabs(["Log in", "Create account"])
    with login_tab:
        with st.form("login"):
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            go = st.form_submit_button("Log in")
        if go:
            try:
                r = http.post(
                    f"{BACKEND_URL}/auth/login",
                    data={"username": email, "password": password},
                    timeout=30,
                )
            except requests.exceptions.RequestException:
                st.error("Cannot reach the backend.")
            else:
                if r.status_code == 200:
                    ss.token = r.json()["access_token"]
                    st.rerun()
                else:
                    st.error("Incorrect email or password.")
    with register_tab:
        with st.form("register"):
            r_name = st.text_input("Full name")
            r_email = st.text_input("Email ", key="r_email")
            r_pass = st.text_input("Password (8+ characters)", type="password", key="r_pass")
            reg = st.form_submit_button("Create recruiter account")
        if reg:
            try:
                r = http.post(
                    f"{BACKEND_URL}/auth/register",
                    json={"email": r_email, "full_name": r_name,
                          "password": r_pass, "role": "recruiter"},
                    timeout=30,
                )
            except requests.exceptions.RequestException:
                st.error("Cannot reach the backend.")
            else:
                if r.status_code == 201:
                    st.success("Account created. Now log in on the first tab.")
                else:
                    st.error("Could not create the account. Check the email and password.")
    st.stop()

# ---------- Logged in ----------
top_left, top_right = st.columns([6, 1])
me = api("GET", "/auth/me")
if me:
    top_left.caption(f"Logged in as {me['full_name']} ({me['email']})")
if top_right.button("Log out"):
    ss.token = None
    st.rerun()

interviews = api("GET", "/interviews/") or []

tab_create, tab_jd, tab_invite, tab_results = st.tabs(
    ["1. Create interview", "2. Job description", "3. Invite candidates", "4. Results"]
)

with tab_create:
    with st.form("create_interview", clear_on_submit=True):
        title = st.text_input("Interview title", placeholder="AI Engineer Round 1")
        job_role = st.text_input("Job role", placeholder="AI Engineer")
        description = st.text_area("Short description (optional)")
        made = st.form_submit_button("Create interview")
    if made:
        if not title.strip() or not job_role.strip():
            st.warning("Title and job role are required.")
        else:
            # 'skills' is filled in later by the JD analysis agent
            created = api("POST", "/interviews/", json={
                "title": title, "job_role": job_role,
                "description": description or None, "skills": "pending analysis",
            })
            if created:
                st.success(f"Interview created. Its ID is {created['id']}.")
                st.rerun()

    if interviews:
        st.subheader("Your interviews")
        st.dataframe(
            [{"ID": i["id"], "Title": i["title"], "Role": i["job_role"], "Skills": i["skills"]}
             for i in interviews],
            use_container_width=True,
        )


def pick_interview(key: str):
    if not interviews:
        st.info("Create an interview in tab 1 first.")
        return None
    labels = {f"#{i['id']} - {i['title']}": i for i in interviews}
    return labels[st.selectbox("Interview", list(labels), key=key)]


with tab_jd:
    iv = pick_interview("jd_pick")
    if iv:
        pdf = st.file_uploader("Upload the job description (PDF)", type="pdf")
        if pdf and st.button("Upload and index the PDF"):
            with st.spinner("Reading and indexing the PDF..."):
                out = api("POST", f"/interviews/{iv['id']}/jd",
                          files={"file": (pdf.name, pdf.getvalue(), "application/pdf")})
            if out:
                st.success(f"Indexed {out['chunks_stored']} chunks.")
        st.divider()
        if st.button("Analyze job description (AI agent)"):
            with st.spinner("The agent is reading the job description..."):
                out = api("POST", f"/interviews/{iv['id']}/analyze")
            if out:
                st.success(out["role_summary"])
                st.write("**Skills to be tested:** " + ", ".join(out["skills"]))

with tab_invite:
    iv = pick_interview("inv_pick")
    if iv:
        emails_text = st.text_area("Candidate emails (one per line)")
        d = st.date_input("Interview date")
        t = st.time_input("Start time", value=time(10, 0))
        st.caption("Times use your computer's time zone.")
        if st.button("Create invitations"):
            emails = [e.strip() for e in emails_text.splitlines() if e.strip()]
            if not emails:
                st.warning("Enter at least one email.")
            else:
                when = datetime.combine(d, t).astimezone().isoformat()
                out = api("POST", f"/interviews/{iv['id']}/invitations/",
                          json={"emails": emails, "scheduled_at": when})
                if out is not None:
                    st.success(f"Created {len(out)} new invitation(s).")
        if st.button("Send invitation emails (AI agent)"):
            with st.spinner("The agent is writing and sending the emails..."):
                out = api("POST", f"/interviews/{iv['id']}/invitations/send")
            if out:
                mode = "dry-run (printed in the backend terminal)" if out["dry_run"] else "real"
                st.success(f"Sent {len(out['sent'])} email(s), mode: {mode}.")
                if out["failed"]:
                    st.error("Failed: " + ", ".join(out["failed"]))
        invs = api("GET", f"/interviews/{iv['id']}/invitations/") or []
        if invs:
            st.subheader("Invitations")
            st.dataframe(
                [{"Email": i["candidate_email"], "Access code": i["access_code"],
                  "Status": i["status"], "Email sent": i["email_sent"]} for i in invs],
                use_container_width=True,
            )

with tab_results:
    iv = pick_interview("res_pick")
    if iv:
        rows = api("GET", f"/interviews/{iv['id']}/results/") or []
        if not rows:
            st.info("No candidates yet.")
        for row in rows:
            sc = row["scorecard"]
            head = f"{row['email']}  -  {row['status']}"
            if sc:
                head += f"  -  {sc['overall_percent']}%  -  {sc['recommendation']}"
            with st.expander(head):
                if sc:
                    st.write(sc["summary"])
                    c1, c2 = st.columns(2)
                    c1.markdown("**Strengths**\n" + "\n".join(f"- {s}" for s in sc["strengths"]))
                    c2.markdown("**Weaknesses**\n" + "\n".join(f"- {s}" for s in sc["weaknesses"]))
                    st.dataframe(sc["skills"], use_container_width=True)
                elif row["status"] == "completed":
                    st.warning("Interview finished but the scorecard is missing.")
                    if st.button("Rebuild scorecard", key=f"rb{row['invitation_id']}"):
                        with st.spinner("Rebuilding..."):
                            out = api("POST", f"/interviews/{iv['id']}/results/{row['invitation_id']}/rebuild")
                        if out:
                            st.rerun()
                else:
                    st.caption("No scorecard yet.")