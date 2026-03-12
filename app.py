import io
import json
import re
from typing import Any, Dict, List

import pandas as pd
import pdfplumber
import streamlit as st
from openai import OpenAI


st.set_page_config(page_title="PDF → TSV extractor", page_icon="📄", layout="wide")


def get_api_key() -> str:
    try:
        if "OPENAI_API_KEY" in st.secrets:
            return st.secrets["OPENAI_API_KEY"]
    except Exception:
        pass
    return st.session_state.get("manual_api_key", "")


@st.cache_data(show_spinner=False)
def extract_text_from_pdf_bytes(file_bytes: bytes) -> str:
    parts: List[str] = []
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for i, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""
            parts.append(f"\n--- PAGE {i} ---\n{text}")
    return "\n".join(parts).strip()


@st.cache_data(show_spinner=False)
def try_extract_tables_preview(file_bytes: bytes) -> str:
    snippets: List[str] = []
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for i, page in enumerate(pdf.pages[:3], start=1):
            try:
                tables = page.extract_tables() or []
                for t_idx, table in enumerate(tables[:2], start=1):
                    rows = []
                    for row in table[:8]:
                        cleaned = ["" if c is None else str(c) for c in row]
                        rows.append(" | ".join(cleaned))
                    if rows:
                        snippets.append(f"\n[PAGE {i} - TABLE {t_idx}]\n" + "\n".join(rows))
            except Exception:
                continue
    return "\n".join(snippets).strip()


NUMBER_HINTS = {
    "price", "preis", "unit price", "amount", "betrag", "summe", "total",
    "eur", "euro", "net", "netto", "gross", "brutto", "vat", "mwst",
    "tax", "qty", "quantity", "anzahl", "value", "wert", "cost", "kosten"
}


def looks_numeric_column(column_name: str) -> bool:
    name = column_name.lower().strip()
    return any(hint in name for hint in NUMBER_HINTS)



def normalize_eu_number(value: Any) -> str:
    if value is None:
        return ""
    s = str(value).strip()
    if not s:
        return ""

    s = s.replace("\u00a0", " ").replace(" ", "")
    s = re.sub(r"[^0-9,.-]", "", s)
    if not s:
        return ""

    # Keep leading minus only.
    negative = s.startswith("-")
    s = s.replace("-", "")

    if "," in s and "." in s:
        # Last separator is assumed to be the decimal separator.
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "")
        else:
            s = s.replace(",", "")
    elif s.count(",") > 1 and "." not in s:
        s = s.replace(",", "")
    elif s.count(".") > 1 and "," not in s:
        s = s.replace(".", "")

    if "." in s and "," not in s:
        s = s.replace(".", ",")

    if negative and s:
        s = "-" + s
    return s



def sanitize_cell(value: Any, numeric: bool) -> str:
    if value is None:
        return ""
    s = str(value).strip()
    if numeric:
        return normalize_eu_number(s)
    return re.sub(r"\s+", " ", s)



def build_prompt(columns: List[str], include_filename: bool, filename: str, text: str, table_preview: str) -> str:
    col_block = "\n".join(f"- {c}" for c in columns)
    numeric_cols = [c for c in columns if looks_numeric_column(c)]
    numeric_block = "\n".join(f"- {c}" for c in numeric_cols) if numeric_cols else "- none"

    return f"""
You extract structured data from PDF text.

Task:
Return ONLY valid JSON with this exact shape:
{{
  "rows": [
    {{{', '.join(f'"{c}": ""' for c in columns)}}}
  ]
}}

Rules:
1. Extract values only from the requested columns.
2. Each row must represent one logical line item from the PDF.
3. Do not invent values.
4. If a value is missing, use an empty string.
5. Keep codes/article numbers/item IDs exactly as seen.
6. For numeric-looking fields, return only the numeric text, without currency symbols.
7. Ignore summary/footer rows unless they clearly belong to the requested columns.
8. Output JSON only. No markdown. No explanation.
9. Requested columns are exactly:
{col_block}

Numeric columns to treat as numbers:
{numeric_block}

Current file name: {filename if include_filename else 'not needed in output'}

PDF table preview (best-effort):
{table_preview[:12000]}

Full extracted PDF text:
{text[:120000]}
""".strip()



def extract_rows_with_openai(client: OpenAI, model: str, columns: List[str], include_filename: bool, filename: str, text: str, table_preview: str) -> List[Dict[str, str]]:
    prompt = build_prompt(columns, include_filename, filename, text, table_preview)
    response = client.responses.create(
        model=model,
        input=prompt,
        temperature=0,
    )
    raw = getattr(response, "output_text", "") or ""
    raw = raw.strip()

    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?", "", raw).strip()
        raw = re.sub(r"```$", "", raw).strip()

    data = json.loads(raw)
    rows = data.get("rows", [])
    if not isinstance(rows, list):
        raise ValueError("The model response did not contain a rows list.")

    cleaned_rows: List[Dict[str, str]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        cleaned: Dict[str, str] = {}
        for col in columns:
            cleaned[col] = sanitize_cell(row.get(col, ""), looks_numeric_column(col))
        if any(str(v).strip() for v in cleaned.values()):
            cleaned_rows.append(cleaned)
    return cleaned_rows



def dataframe_to_tsv(df: pd.DataFrame) -> str:
    df = df.fillna("")
    return df.to_csv(sep="\t", index=False, lineterminator="\n")


st.title("📄 PDF → TSV extractor")
st.caption("Tölts fel egy vagy több PDF-et, add meg a kívánt oszlopneveket, és az app tab-separated kimenetet ad vissza. A numerikus mezőket európai formára alakítja (tizedesvessző).")

with st.sidebar:
    st.header("Beállítások")
    st.text_input(
        "OpenAI API key",
        type="password",
        key="manual_api_key",
        help="Ha Streamlit secrets-ben már benne van, itt nem kell megadni.",
    )
    model = st.text_input("Model", value="gpt-5-mini")
    include_filename = st.checkbox("Legyen külön source_file oszlop", value=True)
    st.markdown("A deployolt appnál ajánlott a kulcsot `OPENAI_API_KEY` néven a Streamlit Secrets-be tenni.")

uploaded_files = st.file_uploader(
    "PDF-ek feltöltése",
    type=["pdf"],
    accept_multiple_files=True,
)

columns_text = st.text_area(
    "Kért oszlopok",
    value="item_code\nunit_price_wo_vat",
    height=160,
    help="Soronként egy oszlopnév. Példa: item_code, unit_price_wo_vat, amount, customer_id",
)

run = st.button("Kivonatolás indítása", type="primary")

if run:
    api_key = get_api_key()
    if not api_key:
        st.error("Adj meg OpenAI API key-t a sidebarban, vagy tedd be a Streamlit Secrets-be `OPENAI_API_KEY` néven.")
        st.stop()

    if not uploaded_files:
        st.error("Tölts fel legalább egy PDF-et.")
        st.stop()

    requested_columns = [c.strip() for c in columns_text.splitlines() if c.strip()]
    if include_filename and "source_file" not in requested_columns:
        columns = ["source_file"] + requested_columns
    else:
        columns = requested_columns

    if not columns:
        st.error("Adj meg legalább egy oszlopnevet.")
        st.stop()

    client = OpenAI(api_key=api_key)
    all_rows: List[Dict[str, str]] = []
    errors: List[str] = []

    progress = st.progress(0)
    status = st.empty()

    for idx, uploaded in enumerate(uploaded_files, start=1):
        status.write(f"Feldolgozás: {uploaded.name} ({idx}/{len(uploaded_files)})")
        try:
            file_bytes = uploaded.read()
            text = extract_text_from_pdf_bytes(file_bytes)
            table_preview = try_extract_tables_preview(file_bytes)
            row_columns = [c for c in columns if c != "source_file"]
            rows = extract_rows_with_openai(
                client=client,
                model=model,
                columns=row_columns,
                include_filename=include_filename,
                filename=uploaded.name,
                text=text,
                table_preview=table_preview,
            )
            if include_filename:
                for row in rows:
                    row["source_file"] = uploaded.name
            all_rows.extend(rows)
        except Exception as e:
            errors.append(f"{uploaded.name}: {e}")
        progress.progress(idx / len(uploaded_files))

    status.empty()

    if errors:
        with st.expander("Hibák", expanded=True):
            for err in errors:
                st.error(err)

    if not all_rows:
        st.warning("Nem sikerült kinyerni sorokat a megadott oszlopokhoz.")
        st.stop()

    df = pd.DataFrame(all_rows)
    ordered_cols = [c for c in columns if c in df.columns] + [c for c in df.columns if c not in columns]
    df = df[ordered_cols]

    for col in df.columns:
        if looks_numeric_column(col):
            df[col] = df[col].map(lambda x: normalize_eu_number(x) if str(x).strip() else "")

    st.success(f"Kész. {len(df)} sor került kinyerésre.")
    st.dataframe(df, use_container_width=True)

    tsv_text = dataframe_to_tsv(df)
    st.text_area("TSV kimenet", value=tsv_text, height=260)
    st.download_button(
        "TSV letöltése",
        data=tsv_text.encode("utf-8"),
        file_name="extracted.tsv",
        mime="text/tab-separated-values",
    )
