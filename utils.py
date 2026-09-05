"""
utils.py
--------
Helper functions for loading and validating the prospect list CSV.
"""

import pandas as pd
import io


REQUIRED_COLUMN_HINTS = ["name"]  # at minimum we want a name column


def load_prospects_csv(uploaded_file) -> pd.DataFrame:
    """
    Load an uploaded CSV file (Streamlit UploadedFile object or path)
    into a pandas DataFrame. Cleans column names (lowercase, stripped).
    """
    if hasattr(uploaded_file, "read"):
        content = uploaded_file.read()
        df = pd.read_csv(io.BytesIO(content))
    else:
        df = pd.read_csv(uploaded_file)

    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
    df = df.fillna("")
    return df


def validate_prospects_df(df: pd.DataFrame):
    """
    Basic validation - checks the dataframe isn't empty and has at
    least a name-like column. Returns (is_valid, message).
    """
    if df is None or df.empty:
        return False, "The uploaded CSV is empty."

    has_name_col = any(col in df.columns for col in ["name", "full_name", "first_name"])
    if not has_name_col:
        return False, "CSV must include at least a 'name' (or 'first_name') column."

    return True, "OK"


def row_to_prospect_dict(row) -> dict:
    """
    Convert a DataFrame row into a plain dict of prospect details,
    used to fill the personalization prompt.
    """
    return {col: str(row[col]) for col in row.index}


def sample_prospects_csv_bytes() -> bytes:
    """Returns bytes for a small sample CSV, used for the demo download button."""
    sample = pd.DataFrame([
        {
            "name": "Priya Sharma",
            "company": "Nimbus Retail",
            "role": "Head of Marketing",
            "industry": "E-commerce",
            "pain_point": "low email open rates on promo campaigns",
        },
        {
            "name": "Rahul Verma",
            "company": "Cloudforge Technologies",
            "role": "VP of Sales",
            "industry": "SaaS",
            "pain_point": "long sales cycles and manual lead qualification",
        },
        {
            "name": "Ananya Iyer",
            "company": "Greenleaf Foods",
            "role": "Founder",
            "industry": "D2C food & beverage",
            "pain_point": "scaling outbound without a big sales team",
        },
    ])
    return sample.to_csv(index=False).encode("utf-8")
