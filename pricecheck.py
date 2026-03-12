import streamlit as st
import google.generativeai as genai
import pandas as pd

# --- CONFIGURATION ---
try:
    api_key = st.secrets["GOOGLE_API_KEY"]
except:
    api_key = "YOUR_LOCAL_API_KEY_HERE"

genai.configure(api_key=api_key)

st.set_page_config(page_title="Invoice Extractor", layout="wide")
st.title("📄 Universal Invoice Data Extractor")

with st.sidebar:
    st.header("Settings")
    columns_needed = st.text_input("Columns to extract:", "ArtNr, Preis")
    decimal_sep = st.selectbox("Decimal separator:", [",", "."])

uploaded_file = st.file_uploader("Upload Invoice (PDF)", type=["pdf"])

if uploaded_file:
    if st.button("Extract Data"):
        with st.spinner("Processing... please wait."):
            try:
                model = genai.GenerativeModel('gemini-1.5-flash')
                pdf_data = uploaded_file.read()
                
                # Szigorúbb utasítás a modellnek
                prompt = f"""
                Analyze the uploaded invoice and extract these columns: {columns_needed}.
                
                Output Format:
                - Use Tab-Separated Values (TSV).
                - Use '{decimal_sep}' for decimals.
                - Provide ONLY the raw data rows.
                - NO headers, NO markdown code blocks (no backticks), NO talking.
                """
                
                response = model.generate_content([
                    prompt,
                    {"mime_type": "application/pdf", "data": pdf_data}
                ])
                
                # Tisztítjuk a választ (levágjuk a felesleges szóközöket/jeleket)
                result_text = response.text.strip().replace("```", "").replace("tsv", "")

                if result_text:
                    st.subheader("Extracted Results")
                    # Megjelenítés táblázatként (ha lehetséges)
                    st.text_area("Raw Data (Copyable):", result_text, height=250)
                    
                    st.download_button(
                        label="Download Data",
                        data=result_text,
                        file_name="invoice_data.txt"
                    )
                else:
                    st.error("The model returned an empty response. Try changing the column names.")
                    
            except Exception as e:
                st.error(f"Critical Error: {str(e)}")
