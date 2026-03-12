import io
import json
import re
from typing import Dict, List, Tuple

import pandas as pd
import pdfplumber
import streamlit as st
from openai import OpenAI


st.set_page_config(page_title="PDF Column Extractor", page_icon="📄", layout="wide")


# ---------------------------
# Helpers
# ---------------------------

def get_api_key() -> str:
    key = ""
    try:
        key = st.secrets.get("OPENAI_API_KEY", "")
    except Exception:
        key = ""

    sidebar_key = st.sidebar.text_input("OpenAI API key", type="password")
    if sidebar_key.strip():
        key = sidebar_key.strip()

    return key


def looks_numeric_column(column_name: str) -> bool:
    name = column_name.strip().lower()
    numeric_keywords = [
        "price",
        "amount",
        "unit price",
        "total",
        "sum",
        "qty",
        "quantity",
        "cost",
        "value",
        "vat",
        "eur",
        "net",
        "gross",
        "number",
        "code",
        "id",
    ]
    return any(keyword in name for keyword in numeric_keywords)


def normalize_european_number(value: str) -> str:
    """
    Convert numeric-looking strings into European format:
    1234.56 -> 1234,56
    1,234.56 -> 1234,56
    1.234,56 -> 1234,56
    Keeps integers unchanged except cleanup.
    """
    if value is None:
        return ""

    s = str(value).strip()
    if not s:
        return ""

    s = s.replace("\u00a0", " ").strip()

    # Remove currency text/symbols but keep digits, separators, minus
    s = re.sub(r"\bEUR\b", "", s, flags=re.IGNORECASE)
    s = s.replace("€", "").strip()

    # If nothing numeric remains, return original stripped text
    if not re.search(r"\d", s):
        return s

    # Remove spaces inside numbers
    s = s.replace(" ", "")

    # Cases:
    # 1) 1.234,56 -> decimal is comma, dots are thousand separators
    if "," in s and "." in s:
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "")
            s = s.replace(",", ".")
        else:
            s = s.replace(",", "")

    # 2) only comma present
    elif "," in s:
        # If exactly 1-2 digits after comma, treat as decimal comma
        parts = s.split(",")
        if len(parts) == 2 and len(parts[1]) in (1, 2, 3):
            s = s.replace(",", ".")
        else:
            s = s.replace(",", "")

    # 3) only dot present
    elif "." in s:
        parts = s.split(".")
        # If multiple dots and last part looks decimal, remove thousand separators
        if len(parts) > 2:
            decimal_part = parts[-1]
            int_part = "".join(parts[:-1])
            if len(decimal_part) in (1, 2, 3):
                s = f"{int_part}.{decimal_part}"
            else:
                s = "".join(parts)
        # Else leave as is

    try:
        num = float(s)
        # Preserve decimals only when needed
        if num.is_integer():
            return str(int(num))
        formatted = f"{num:.2f}".rstrip("0").rstrip(".")
        return formatted.replace(".", ",")
    except Exception:
        return str(value).strip()


def sanitize_cell(value: str, numeric: bool) -> str:
    if value is None:
        return ""
    text = str(value).strip()

    if not text:
        return ""

    if numeric:
        return normalize_european_number(text)

    return re.sub(r"\s+", " ", text).strip()


def extract_text_and_tables_from_pdf(file_bytes: bytes) -> Tuple[str, str]:
    all_text: List[str] = []
    all_tables: List[str] = []

    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page_num, page in enumerate(pdf.pages, start=1):
            page_text = page.extract_text() or ""
            if page_text.strip():
                all_text.append(f"\n--- PAGE {page_num} ---\n{page_text}")

            try:
                tables = page.extract_tables() or []
            except Exception:
                tables = []

            for table_idx, table in enumerate(tables, start=1):
                if not table:
                    continue

                cleaned_rows = []
                for row in table:
                    if not row:
                        continue
                    cleaned = [
                        re.sub(r"\s+", " ", str(cell).strip()) if cell is not None else ""
                        for cell in row
                    ]
                    cleaned_rows.append(" | ".join(cleaned))

                if cleaned_rows:
                    all_tables.append(
                        f"\n--- PAGE {page_num} TABLE {table_idx} ---\n" + "\n".join(cleaned_rows)
                    )

    return "\n".join(all_text), "\n".join(all_tables)


def build_prompt(
    columns: List[str],
    include_filename: bool,
    filename: str,
    text: str,
    table_preview: str
) -> str:
    columns_text = ", ".join(columns)

    filename_instruction = (
        f'Include a column called "source_file" with value "{filename}" in every row.'
        if include_filename
        else "Do not include any source filename unless it is one of the requested columns."
    )

    return f"""
You are extracting structured row-based data from a PDF.

Requested columns:
{columns_text}

Rules:
1. Return only rows that you can infer from the PDF content.
2. Match the requested columns as closely as possible, even if the PDF uses slightly different labels.
3. Do not invent values.
4. If a value is missing for a row, return an empty string for that field.
5. Return only JSON matching the required schema.
6. Prices and amounts should be returned as plain numeric strings without currency symbols.
7. For codes / IDs / article numbers, return only the relevant code value.
8. {filename_instruction}

PDF text:
{text[:25000]}

Extracted table preview:
{table_preview[:20000]}
""".strip()


def extract_rows_with_openai(
    client: OpenAI,
    model: str,
    columns: List[str],
    include_filename: bool,
    filename: str,
    text: str,
    table_preview: str
) -> List[Dict[str, str]]:
    final_columns = columns[:]
    if include_filename and "source_file" not in final_columns:
        final_columns = ["source_file"] + final_columns

    prompt = build_prompt(final_columns, include_filename, filename, text, table_preview)

    schema = {
        "type": "object",
        "properties": {
            "rows": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {col: {"type": "string"} for col in final_columns},
                    "required": final_columns,
                    "additionalProperties": False,
                },
            }
        },
        "required": ["rows"],
        "additionalProperties": False,
    }

    response = client.responses.create(
        model=model,
        instructions="You extract structured data from PDF text and return only valid JSON.",
        input=prompt,
        text={
            "format": {
                "type": "json_schema",
                "name": "pdf_rows",
                "schema": schema,
                "strict": True,
            }
        },
    )

    raw = (getattr(response, "output_text", "") or "").strip()

    if not raw:
        raise ValueError("The model returned an empty response.")

    data = json.loads(raw)
    rows = data.get("rows", [])

    if not isinstance(rows, list):
        raise ValueError("The model response does not contain a valid 'rows' list.")

    cleaned_rows: List[Dict[str, str]] = []

    for row in rows:
        if not isinstance(row, dict):
            continue

        cleaned: Dict[str, str] = {}
        for col in final_columns:
            value = row.get(col, "")
            cleaned[col] = sanitize_cell(value, looks_numeric_column(col))

        if any(str(v).strip() for v in cleaned.values()):
            cleaned_rows.append(cleaned)

    return cleaned_rows


def dataframe_to_tsv(df: pd.DataFrame) -> str:
    return df.to_csv(sep="\t", index=False)


# ---------------------------
# UI
# ---------------------------

st.title("PDF Column Extractor to TSV")
st.write(
    "Upload one or more PDF files, specify the columns you want to extract, "
    "and get a tab-separated output with European decimal formatting."
)

with st.sidebar:
    st.header("Settings")
    api_key = get_api_key()
    model = st.text_input("Model", value="gpt-4.1-mini")
    include_filename = st.checkbox("Include source filename column", value=True)

st.markdown("### 1. Upload PDF files")
uploaded_files = st.file_uploader(
    "Choose PDF files",
    type=["pdf"],
    accept_multiple_files=True,
)

st.markdown("### 2. Enter the columns to extract")
columns_input = st.text_area(
    "One column per line",
    value="item code\nunit price w/o VAT",
    height=120,
)

run = st.button("Extract data", type="primary")

if run:
    if not api_key:
        st.error("Please provide your OpenAI API key in the sidebar or in Streamlit secrets.")
        st.stop()

    if not uploaded_files:
        st.error("Please upload at least one PDF file.")
        st.stop()

    columns = [line.strip() for line in columns_input.splitlines() if line.strip()]
    if not columns:
        st.error("Please provide at least one column name.")
        st.stop()

    client = OpenAI(api_key=api_key)
    all_rows: List[Dict[str, str]] = []
    progress = st.progress(0)
    status = st.empty()

    for idx, uploaded_file in enumerate(uploaded_files, start=1):
        try:
            status.write(f"Processing: **{uploaded_file.name}**")

            file_bytes = uploaded_file.read()
            text, table_preview = extract_text_and_tables_from_pdf(file_bytes)

            if not text.strip() and not table_preview.strip():
                raise ValueError(
                    "No readable text or tables could be extracted from this PDF. "
                    "It may be a scanned image PDF."
                )

            rows = extract_rows_with_openai(
                client=client,
                model=model,
                columns=columns,
                include_filename=include_filename,
                filename=uploaded_file.name,
                text=text,
                table_preview=table_preview,
            )

            if not rows:
                st.warning(
                    f"{uploaded_file.name}: No rows could be extracted for the requested columns."
                )
            else:
                all_rows.extend(rows)
                st.success(f"{uploaded_file.name}: Extracted {len(rows)} row(s).")

        except Exception as e:
            st.error(f"{uploaded_file.name}: {str(e)}")

        progress.progress(idx / len(uploaded_files))

    status.empty()

    if all_rows:
        df = pd.DataFrame(all_rows)

        # Keep column order stable
        desired_columns = columns[:]
        if include_filename:
            desired_columns = ["source_file"] + desired_columns

        for col in desired_columns:
            if col not in df.columns:
                df[col] = ""

        df = df[desired_columns]

        st.markdown("### 3. Preview")
        st.dataframe(df, use_container_width=True)

        tsv_output = dataframe_to_tsv(df)

        st.markdown("### 4. TSV output")
        st.text_area("Copy this tab-separated output", value=tsv_output, height=300)

        st.download_button(
            label="Download TSV",
            data=tsv_output.encode("utf-8"),
            file_name="extracted_data.tsv",
            mime="text/tab-separated-values",
        )
    else:
        st.warning("No extractable rows were found in the uploaded files.")
