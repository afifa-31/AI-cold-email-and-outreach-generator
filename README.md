# 📧 AI Cold Email & Outreach Generator

A Streamlit tool that generates personalized cold outreach emails at scale from
a prospect list, with **A/B variant generation** and a built-in
**spam-trigger-word checker**. Built for the Generative AI Hackathon
(Problem Statement 5).

---

## ✨ Features

- Describe your product/service and target audience once
- Add prospects via **CSV upload OR manual entry form** (name, company, role, pain point, etc.)
- Choose a **tone/style** (professional, casual, witty) that shapes every generated email
- AI generates 2–3 **A/B email variants per prospect**, each with a different angle
  (pain-point, curiosity/social-proof, direct value-prop)
- Every variant is **personalized** using prospect-specific details
- Built-in **spam-trigger-word checker** flags risky words/phrases, gives a
  Low/Medium/High deliverability risk score, and suggests a **fix for each flagged word**
- **Edit and approve** each email individually before it counts as "ready to send"
- **Copy-to-clipboard** per email (via the built-in copy icon on each code block)
- **Simulated A/B performance dashboard** (open/reply rate estimates per variant) to
  demonstrate how a real A/B test would surface a winning angle
- **Subject line generator with multiple scored options** — 3 candidate subject lines per
  email, each with a predicted open-rate score and reasoning, ranked best-first; pick
  whichever you want to use
- Export **approved-only** or **all** generated emails to CSV

---

## 🗂️ Project structure

```
cold-email-generator/
├── app.py                  # Main Streamlit app (UI + workflow)
├── email_generator.py      # Prompt building + LLM calls (Gemini/OpenAI) + JSON parsing
├── spam_checker.py         # Spam trigger word list + risk scoring logic
├── utils.py                # CSV loading/validation helpers
├── sample_prospects.csv    # Example prospect list you can use for a demo
├── requirements.txt        # Python dependencies
└── README.md               # This file
```

---

## 🚀 Setup (step by step)

### 1. Install Python
Make sure you have Python 3.9+ installed.

### 2. Extract the zip and open a terminal in the folder
```bash
cd cold-email-generator
```

### 3. Create a virtual environment (recommended)
```bash
python -m venv venv
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate
```

### 4. Install dependencies
```bash
pip install -r requirements.txt
```

### 5. Get a free API key
Pick ONE provider:

- **Google Gemini (recommended, free tier)**: go to https://aistudio.google.com/app/apikey
  and click "Create API key". Free quota is generous — good for hackathon demos.
- **OpenAI**: go to https://platform.openai.com/api-keys (requires billing set up).

You do **not** need to put the key in any file — you'll paste it directly into
the app's sidebar when it's running (nothing is stored or logged).

### 6. Run the app
```bash
streamlit run app.py
```
This opens the app in your browser at `http://localhost:8501`.

---

## 🖱️ How to use the app

1. **Sidebar** → choose your AI provider (Gemini or OpenAI) and paste your API key.
2. **Step 1** → describe your product/service and your target audience in plain English.
3. **Step 2** → upload a prospect CSV. Not sure of the format? Download the sample
   CSV from the sidebar — it has columns: `name, company, role, industry, pain_point`.
   You can add/remove columns freely; whatever columns you include get used for
   personalization.
4. **Step 3** → set how many prospects to generate for (keep it small, e.g. 3-5,
   during your demo to save API quota) and click **Generate Emails**.
5. **Step 4** → for each prospect, review the A/B variants in tabs. Each variant
   shows:
   - The **angle** used
   - Subject line + body
   - A **spam risk badge** (🟢 Low / 🟡 Medium / 🔴 High) with the exact
     trigger words found, if any
6. Click **Download all generated emails (CSV)** to export everything.

---

## 🧠 How it works (for your hackathon presentation)

1. **Prompt engineering**: `email_generator.py` builds a single structured prompt
   per prospect that includes the sender's offer, the target audience, and every
   column from that prospect's CSV row. The model is instructed to return
   **strict JSON** with N variants, each using a different persuasion angle.
2. **Personalization at scale**: the app loops over each row of the uploaded
   CSV, calling the LLM once per prospect (so every email is grounded in real
   prospect data instead of being a generic template).
3. **A/B variant generation**: the prompt explicitly asks for multiple angles
   (e.g. pain-point-led vs. curiosity-led vs. value-prop-led) so you can test
   which angle gets better replies.
4. **Spam-trigger-word checker** (`spam_checker.py`): a curated list of
   ~60 words/phrases known to hurt email deliverability (e.g. "free", "act now",
   "guaranteed", "click here"), plus heuristics for excessive `!!!` and ALL-CAPS.
   Each generated email is scored **before you'd send it**, turning this into a
   pre-send deliverability gate rather than just a generator.

---

## 🎤 Suggested demo flow (2-3 minutes)

1. Show the problem: manually writing personalized cold emails doesn't scale,
   and generic blasts get flagged as spam.
2. Fill in a sample product description + target audience live.
3. Upload `sample_prospects.csv`.
4. Generate for 2-3 prospects live.
5. Open one prospect's result → show the two A/B variants and point out how each
   references a different prospect detail.
6. Point out the spam-risk badge and show a trigger word being flagged
   (you can briefly type "act now" into a body box to show it turn red, if you
   want a live "wow" moment).
7. Download the CSV to show the scale/export angle.

---

## 🔧 Possible extensions (mention these as "future work" if asked)

- Send emails directly via SMTP/Gmail API with a scheduling queue
- Replace simulated open/reply rates with real tracked data once emails are actually sent
- Multi-language support for global outreach
- Plug in a CRM (HubSpot/Salesforce) instead of CSV upload/manual entry
- Subject-line-only generator with multiple scored options

---

## ⚠️ Notes

- Your API key is only used in-session in the sidebar; it is never written to
  disk or logged.
- The spam-trigger word list is a heuristic, not a guarantee of inbox
  placement — real deliverability also depends on sender reputation, domain
  authentication (SPF/DKIM/DMARC), and email service provider rules.
