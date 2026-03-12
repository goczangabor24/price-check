import streamlit as st
import google.generativeai as genai
import os

# --- API KULCS ÉS KONFIGURÁCIÓ ---
api_key = ""
try:
    if "GOOGLE_API_KEY" in st.secrets:
        api_key = st.secrets["GOOGLE_API_KEY"].strip().strip('"').strip("'")
except:
    api_key = "YOUR_LOCAL_KEY"

if api_key:
    # Itt a lényeg: konfiguráljuk az API-t
    genai.configure(api_key=api_key)

st.set_page_config(page_title="Invoice Extractor", layout="wide")
st.title("📄 Universal Invoice Data Extractor")

with st.sidebar:
    st.header("Settings")
    # A stabil Gemini 1.5 Flash modellt használjuk
    model_choice = st.selectbox("Select Model:", ["gemini-1.5-flash", "gemini-1.5-pro"])
    columns_needed = st.text_input("Columns to extract:", "ArtNr, Preis")
    decimal_sep = st.selectbox("Decimal separator:", [",", "."])

uploaded_file = st.file_uploader("Upload Invoice (PDF)", type=["pdf"])

if uploaded_file and api_key:
    if st.button("Extract Data"):
        status = st.empty()
        status.info("Connecting to Gemini API...")
        
        try:
            # Modell inicializálása
            model = genai.GenerativeModel(model_name=model_choice)
            
            # PDF beolvasása
            pdf_data = uploaded_file.read()
            
            # Összeállítjuk a kérést az ÚJ formátum szerint
            content_payload = [
                {
                    "mime_type": "application/pdf",
                    "data": pdf_data
                },
                f"Extract the following columns from this invoice: {columns_needed}. "
                f"Format the output as Tab-Separated Values (TSV). "
                f"Use '{decimal_sep}' as decimal separator. "
                f"Return ONLY the data rows, no headers, no intro text, no markdown code blocks."
            ]
            
            status.info("AI is reading the document...")
            
            # Generálás - a legstabilabb metódussal
            response = model.generate_content(content_payload)
            
            if response.text:
                status.success("Extraction successful!")
                # Tisztítás: néha a modell mégis tesz bele ```jeleket
                clean_result = response.text.replace("```tsv", "").replace("```", "").strip()
                
                st.subheader("Extracted Data")
                st.text_area("Copy/Paste version:", clean_result, height=400)
                
                st.download_button(
                    label="Download as TSV",
                    data=clean_result,
                    file_name="invoice_extract.txt",
                    mime="text/tab-separated-values"
                )
            else:
                status.error("The AI could not find any data. Try different column names.")
                
        except Exception as e:
            st.error("Technical Error Occurred")
            st.code(str(e)) # Ez kiírja a pontos hibaüzenetet a képernyőre
