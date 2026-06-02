import requests
import streamlit as st
from google_auth_oauthlib.flow import Flow


BACKEND_URL = st.secrets.get("BACKEND_URL", "http://localhost:8000")
REDIRECT_URI = st.secrets.get("GOOGLE_REDIRECT_URI", "http://localhost:8501")

SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
]


st.set_page_config(
    page_title="Email Summary Dashboard",
    page_icon="mail",
    layout="wide",
)


def create_google_flow():
    return Flow.from_client_config(
        {
            "web": {
                "client_id": st.secrets["GOOGLE_CLIENT_ID"],
                "client_secret": st.secrets["GOOGLE_CLIENT_SECRET"],
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [REDIRECT_URI],
            }
        },
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI,
        autogenerate_code_verifier=False,
    )


def get_auth_url(email: str):
    flow = create_google_flow()

    auth_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
        login_hint=email,
    )

    st.session_state["oauth_state"] = state
    st.session_state["email"] = email

    return auth_url


def exchange_code_for_token(code: str):
    flow = create_google_flow()
    flow.fetch_token(code=code)

    credentials = flow.credentials
    return credentials.token


def start_gmail_processing(access_token: str):
    response = requests.post(
        f"{BACKEND_URL}/process-gmail",
        json={"access_token": access_token},
        timeout=30,
    )

    response.raise_for_status()
    return response.json()


def fetch_summaries(category: str):
    response = requests.get(
        f"{BACKEND_URL}/email-summaries",
        params={"category": category},
        timeout=30,
    )

    response.raise_for_status()
    return response.json().get("summaries", [])


def load_demo_data():
    response = requests.post(
        f"{BACKEND_URL}/load-demo-data",
        timeout=30,
    )

    response.raise_for_status()
    return response.json()


def show_login_page():
    st.title("Email Summary Dashboard")
    st.write("Login with Gmail to process your unread emails and view categorized summaries.")

    email = st.text_input("Enter your Gmail address", placeholder="yourmail@gmail.com")

    if email:
        auth_url = get_auth_url(email)
        st.link_button("Login with Google", auth_url, type="primary")
    else:
        st.button("Login with Google", disabled=True)


def display_summary_card(item: dict):
    summary = item.get("summary") or item.get("content", "")
    full_content = item.get("full_content", "")
    created_at = item.get("created_at", "")

    with st.container(border=True):
        st.subheader("Complaint Summary")

        if created_at:
            st.caption(f"Saved at: {created_at}")

        if full_content:
            st.markdown("**Full Content:**")
            st.write(full_content)

        st.markdown("**Summarized Text:**")
        st.markdown(summary)


def show_category_tab(category: str):
    try:
        summaries = fetch_summaries(category)
    except requests.RequestException as exc:
        st.error(f"Could not load {category} summaries: {exc}")
        return

    if not summaries:
        st.info(f"No {category} summaries found yet.")
        return

    for item in summaries:
        display_summary_card(item)


def show_dashboard():
    st.title("Email Summary Dashboard")

    col1, col2, col3 = st.columns([1, 1, 4])

    with col1:
        if st.button("Refresh"):
            st.rerun()

    with col2:
        if st.button("Load Demo Data"):
            try:
                result = load_demo_data()
                st.success(result.get("message", "Demo data loaded."))
                st.rerun()
            except requests.RequestException as exc:
                st.error(f"Could not load demo data: {exc}")

    with col3:
        st.caption("Your emails are summarized into Mess, Academics, and Hostel categories.")

    mess_tab, academics_tab, hostel_tab = st.tabs(
        ["Mess", "Academics", "Hostel"]
    )

    with mess_tab:
        show_category_tab("display_mess")

    with academics_tab:
        show_category_tab("display_academics")

    with hostel_tab:
        show_category_tab("display_hostel")


code = st.query_params.get("code")

if "access_token" not in st.session_state and code:
    try:
        token = exchange_code_for_token(code)
        st.session_state["access_token"] = token

        result = start_gmail_processing(token)
        st.success(result.get("message", "Email processing started."))

        st.query_params.clear()
        st.rerun()

    except Exception as exc:
        st.error(f"Login worked, but email processing failed: {exc}")


if "access_token" in st.session_state:
    show_dashboard()
else:
    show_login_page()
