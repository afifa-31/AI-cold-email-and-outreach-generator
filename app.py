"""
app.py
------
AI Cold Email & Outreach Generator - Streamlit app.

Users describe their product/service and target audience, provide a
prospect list (CSV upload or manual entry), and the app generates
personalized A/B email variants per prospect using an LLM. Every
variant is run through a spam-trigger-word checker (with fix
suggestions) and must be explicitly approved before it counts as
"ready to send". Approved emails can be exported or copied.
"""

import streamlit as st
import pandas as pd
import time
import random

from utils import load_prospects_csv, validate_prospects_df, row_to_prospect_dict, sample_prospects_csv_bytes
from email_generator import generate_email_variants
from spam_checker import check_spam_words

# Small pause between prospects to stay under the AI provider's free-tier
# requests-per-minute limit (avoids 429 rate-limit errors on bigger batches).
SECONDS_BETWEEN_REQUESTS = 5

st.set_page_config(page_title="AI Cold Email & Outreach Generator", page_icon="📧", layout="wide")

# ---------------------------------------------------------------------------
# Session state init
# ---------------------------------------------------------------------------
if "results" not in st.session_state:
    st.session_state.results = []  # list of {prospect, variants}
if "manual_prospects" not in st.session_state:
    st.session_state.manual_prospects = []  # list of dicts entered manually
if "approvals" not in st.session_state:
    st.session_state.approvals = {}  # key: f"{prospect}_{variant_label}" -> bool

# ---------------------------------------------------------------------------
# Sidebar - API & settings
# ---------------------------------------------------------------------------
st.sidebar.title("⚙️ Settings")

provider = st.sidebar.selectbox(
    "AI Provider",
    options=["gemini", "openai"],
    format_func=lambda x: "Google Gemini (free tier)" if x == "gemini" else "OpenAI (GPT)",
)

def _get_secret_key(name: str) -> str:
    """Safely reads a key from Streamlit secrets if configured; returns '' if not set."""
    try:
        return st.secrets.get(name, "")
    except Exception:
        return ""


secret_key_name = "GEMINI_API_KEY" if provider == "gemini" else "OPENAI_API_KEY"
default_key = _get_secret_key(secret_key_name)

api_key = st.sidebar.text_input(
    f"{'Gemini' if provider == 'gemini' else 'OpenAI'} API Key",
    value=default_key,
    type="password",
    help="Auto-filled from Streamlit Secrets if configured. You can also paste your own here for this session only.",
)

num_variants = st.sidebar.slider("Number of A/B variants per prospect", min_value=2, max_value=3, value=2)

tone = st.sidebar.selectbox(
    "Tone / style",
    options=["professional", "casual", "witty"],
    help="Changes the writing style of every generated email.",
)

st.sidebar.markdown("---")
st.sidebar.download_button(
    "⬇️ Download sample prospects.csv",
    data=sample_prospects_csv_bytes(),
    file_name="sample_prospects.csv",
    mime="text/csv",
)
st.sidebar.caption("Not sure about the CSV format? Grab the sample above.")

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.title("📧 AI Cold Email & Outreach Generator")
st.caption("Describe your offer, add your prospects, and generate personalized, spam-checked cold emails at scale.")

# ---------------------------------------------------------------------------
# Step 1: Offer + audience description
# ---------------------------------------------------------------------------
st.header("1️⃣ Describe your product/service & audience")

col1, col2 = st.columns(2)
with col1:
    sender_name = st.text_input("Your name", placeholder="e.g. Afifa Shaik")
    sender_company = st.text_input("Your company", placeholder="e.g. Nimbus AI")
with col2:
    product_description = st.text_area(
        "Describe your product/service",
        placeholder="e.g. We provide an AI-powered inventory forecasting tool for D2C brands that cuts stockouts by 30%.",
        height=100,
    )
    target_audience = st.text_area(
        "Describe your target audience",
        placeholder="e.g. Founders and operations heads at D2C e-commerce brands with $1M-$10M revenue.",
        height=100,
    )

# ---------------------------------------------------------------------------
# Step 2: Prospect list - CSV upload OR manual entry
# ---------------------------------------------------------------------------
st.header("2️⃣ Add your prospect list")

csv_tab, manual_tab = st.tabs(["📁 Upload CSV", "✍️ Enter manually"])

prospects_df = None

with csv_tab:
    uploaded_file = st.file_uploader(
        "CSV should include at least a 'name' column. Extra columns (company, role, pain_point, industry, etc.) improve personalization.",
        type=["csv"],
    )
    if uploaded_file is not None:
        try:
            prospects_df = load_prospects_csv(uploaded_file)
            is_valid, msg = validate_prospects_df(prospects_df)
            if not is_valid:
                st.error(msg)
                prospects_df = None
            else:
                st.success(f"Loaded {len(prospects_df)} prospects.")
                st.dataframe(prospects_df, use_container_width=True)
        except Exception as e:
            st.error(f"Couldn't read that CSV: {e}")

with manual_tab:
    st.caption("Add prospects one at a time — useful if you don't have a CSV handy.")
    with st.form("manual_add_form", clear_on_submit=True):
        mcol1, mcol2 = st.columns(2)
        with mcol1:
            m_name = st.text_input("Name*")
            m_company = st.text_input("Company")
            m_role = st.text_input("Role")
        with mcol2:
            m_industry = st.text_input("Industry")
            m_pain_point = st.text_input("Pain point / note")
        add_clicked = st.form_submit_button("➕ Add prospect")
        if add_clicked:
            if not m_name.strip():
                st.warning("Name is required.")
            else:
                st.session_state.manual_prospects.append({
                    "name": m_name.strip(),
                    "company": m_company.strip(),
                    "role": m_role.strip(),
                    "industry": m_industry.strip(),
                    "pain_point": m_pain_point.strip(),
                })

    if st.session_state.manual_prospects:
        manual_df = pd.DataFrame(st.session_state.manual_prospects)
        st.dataframe(manual_df, use_container_width=True)
        if st.button("🗑️ Clear manually entered prospects"):
            st.session_state.manual_prospects = []
            st.rerun()

# Combine CSV + manual prospects into one working dataframe
combined_frames = []
if prospects_df is not None:
    combined_frames.append(prospects_df)
if st.session_state.manual_prospects:
    combined_frames.append(pd.DataFrame(st.session_state.manual_prospects))

final_prospects_df = pd.concat(combined_frames, ignore_index=True) if combined_frames else None

# ---------------------------------------------------------------------------
# Step 3: Generate
# ---------------------------------------------------------------------------
st.header("3️⃣ Generate personalized emails")

max_prospects = st.number_input(
    "Limit number of prospects to generate for (useful for demos / API quota)",
    min_value=1, max_value=100, value=5,
)

generate_clicked = st.button("🚀 Generate Emails", type="primary", use_container_width=True)

if generate_clicked:
    if not api_key:
        st.warning("Please enter your API key in the sidebar first.")
    elif not product_description or not target_audience:
        st.warning("Please fill in both the product/service and target audience descriptions.")
    elif final_prospects_df is None or final_prospects_df.empty:
        st.warning("Please add at least one prospect — upload a CSV or enter one manually.")
    else:
        st.session_state.results = []
        st.session_state.approvals = {}
        rows = final_prospects_df.head(int(max_prospects))
        progress = st.progress(0, text="Starting generation...")

        for i, (_, row) in enumerate(rows.iterrows()):
            prospect = row_to_prospect_dict(row)
            display_name = prospect.get("name") or prospect.get("first_name") or f"Prospect {i+1}"
            progress.progress((i) / len(rows), text=f"Generating emails for {display_name}...")

            try:
                variants = generate_email_variants(
                    provider=provider,
                    api_key=api_key,
                    product_description=product_description,
                    target_audience=target_audience,
                    sender_name=sender_name,
                    sender_company=sender_company,
                    prospect_details=prospect,
                    num_variants=num_variants,
                    tone=tone,
                )
                for v in variants:
                    spam_report = check_spam_words(f"{v.get('subject','')} {v.get('body','')}")
                    v["spam_report"] = spam_report
                    # Simulated performance metrics for the A/B testing story
                    # (clearly a demo estimate, not real send data).
                    v["sim_open_rate"] = round(random.uniform(28, 55), 1)
                    v["sim_reply_rate"] = round(random.uniform(3, 15), 1)

                st.session_state.results.append({
                    "prospect": prospect,
                    "display_name": display_name,
                    "variants": variants,
                    "error": None,
                })
            except Exception as e:
                st.session_state.results.append({
                    "prospect": prospect,
                    "display_name": display_name,
                    "variants": [],
                    "error": str(e),
                })

            if i < len(rows) - 1:
                time.sleep(SECONDS_BETWEEN_REQUESTS)

        progress.progress(1.0, text="Done!")
        time.sleep(0.3)
        progress.empty()

# ---------------------------------------------------------------------------
# Step 4: Display results, spam-fix suggestions, and approval
# ---------------------------------------------------------------------------
if st.session_state.results:
    st.header("4️⃣ Review, fix, and approve emails")
    st.caption("Tweak the text if needed, review the spam-risk suggestions, then check **Approve** before exporting.")

    risk_colors = {"Low": "🟢", "Medium": "🟡", "High": "🔴"}

    for item in st.session_state.results:
        with st.expander(f"📨 {item['display_name']}", expanded=False):
            if item["error"]:
                st.error(f"Generation failed: {item['error']}")
                continue

            tabs = st.tabs([v.get("label", f"Variant {idx+1}") for idx, v in enumerate(item["variants"])])
            for tab, v in zip(tabs, item["variants"]):
                with tab:
                    approval_key = f"{item['display_name']}_{v.get('label')}"

                    st.markdown(f"**Angle:** {v.get('angle', '-')}")

                    # --- Subject line options, ranked by predicted open rate ---
                    subject_options = v.get("subject_options", [])
                    if subject_options:
                        st.markdown("**Subject line options (ranked by predicted open rate):**")
                        subject_labels = [
                            f"{opt['predicted_open_rate']}% predicted open rate — \"{opt['subject']}\""
                            for opt in subject_options
                        ]
                        chosen_idx = st.radio(
                            "Pick the subject line to use",
                            options=range(len(subject_options)),
                            format_func=lambda i: subject_labels[i],
                            key=f"{approval_key}_subject_choice",
                            index=0,
                        )
                        for opt in subject_options:
                            if opt.get("reason"):
                                st.caption(f"💡 \"{opt['subject']}\" — {opt['reason']}")
                        chosen_subject = subject_options[chosen_idx]["subject"]
                    else:
                        chosen_subject = v.get("subject", "-")
                        st.markdown(f"**Subject:** {chosen_subject}")

                    edited_body = st.text_area(
                        "Body (editable)", value=v.get("body", ""), height=180,
                        key=f"{approval_key}_body",
                    )

                    # Re-run the spam check live against any edits the user made.
                    report = check_spam_words(f"{chosen_subject} {edited_body}")
                    risk = report.get("risk_level", "Low")
                    st.markdown(f"**Spam risk:** {risk_colors.get(risk, '')} {risk}")

                    if report.get("matches"):
                        st.warning("Spam-trigger words found — suggested fixes:")
                        for word in report["matches"]:
                            fix = report["suggestions"].get(word, "consider rewording")
                            st.markdown(f"- ~~`{word}`~~ → try **\"{fix}\"**")
                    if report.get("excessive_exclamation"):
                        st.info("Tip: too many exclamation marks can hurt deliverability.")
                    if report.get("excessive_caps"):
                        st.info("Tip: too many ALL-CAPS words can hurt deliverability.")
                    if risk == "Low" and not report.get("matches"):
                        st.success("No spam-trigger words detected.")

                    st.markdown("**Copy this email:**")
                    st.code(f"Subject: {chosen_subject}\n\n{edited_body}", language=None)

                    sim_col1, sim_col2 = st.columns(2)
                    sim_col1.metric("Simulated open rate", f"{v.get('sim_open_rate', 0)}%")
                    sim_col2.metric("Simulated reply rate", f"{v.get('sim_reply_rate', 0)}%")
                    st.caption("Simulated metrics for demo purposes — not from real sends.")

                    approved = st.checkbox(
                        "✅ Approve this email for sending",
                        key=f"{approval_key}_approve",
                        value=st.session_state.approvals.get(approval_key, False),
                    )
                    st.session_state.approvals[approval_key] = approved

                    # Keep the (possibly edited) body / chosen subject / spam report in sync for export.
                    v["body"] = edited_body
                    v["subject"] = chosen_subject
                    v["spam_report"] = report

    # -----------------------------------------------------------------
    # Mock analytics dashboard - simulated A/B performance across all
    # generated variants, grouped by angle, purely for the demo story.
    # -----------------------------------------------------------------
    st.subheader("📊 Simulated A/B performance (demo)")
    chart_rows = []
    for item in st.session_state.results:
        for v in item.get("variants", []):
            chart_rows.append({
                "Variant": v.get("label", "-"),
                "Open rate %": v.get("sim_open_rate", 0),
                "Reply rate %": v.get("sim_reply_rate", 0),
            })
    if chart_rows:
        chart_df = pd.DataFrame(chart_rows).groupby("Variant").mean(numeric_only=True)
        st.bar_chart(chart_df)
        st.caption("Averaged simulated rates per variant label — illustrates how A/B testing would surface a winning angle once real replies come in.")

    # -----------------------------------------------------------------
    # Export - approved only, or everything
    # -----------------------------------------------------------------
    def build_export_df(approved_only: bool) -> pd.DataFrame:
        export_rows = []
        for item in st.session_state.results:
            for v in item.get("variants", []):
                approval_key = f"{item['display_name']}_{v.get('label')}"
                is_approved = st.session_state.approvals.get(approval_key, False)
                if approved_only and not is_approved:
                    continue
                export_rows.append({
                    "prospect": item["display_name"],
                    "variant": v.get("label"),
                    "angle": v.get("angle"),
                    "subject": v.get("subject"),
                    "body": v.get("body"),
                    "approved": is_approved,
                    "spam_risk": v.get("spam_report", {}).get("risk_level"),
                    "spam_words_found": ", ".join(v.get("spam_report", {}).get("matches", [])),
                    "sim_open_rate": v.get("sim_open_rate"),
                    "sim_reply_rate": v.get("sim_reply_rate"),
                })
        return pd.DataFrame(export_rows)

    st.subheader("⬇️ Export")
    exp_col1, exp_col2 = st.columns(2)

    approved_df = build_export_df(approved_only=True)
    with exp_col1:
        if not approved_df.empty:
            st.download_button(
                "⬇️ Download APPROVED emails only (CSV)",
                data=approved_df.to_csv(index=False).encode("utf-8"),
                file_name="approved_cold_emails.csv",
                mime="text/csv",
                use_container_width=True,
            )
        else:
            st.button("⬇️ Download APPROVED emails only (CSV)", disabled=True, use_container_width=True,
                       help="Approve at least one email above first.")

    all_df = build_export_df(approved_only=False)
    with exp_col2:
        if not all_df.empty:
            st.download_button(
                "⬇️ Download ALL generated emails (CSV)",
                data=all_df.to_csv(index=False).encode("utf-8"),
                file_name="all_generated_cold_emails.csv",
                mime="text/csv",
                use_container_width=True,
            )

st.markdown("---")
st.caption("Built for the Generative AI Hackathon · AI Cold Email & Outreach Generator")
