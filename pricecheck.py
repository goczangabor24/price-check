import streamlit as st
import google.generativeai as genai

# --- API KULCS KEZELÉSE ---
api_key = ""
try:
    if "GOOGLE_API_KEY" in st.secrets:
        api_key = st.secrets["GOOGLE_API_KEY"].strip().strip('"').strip("'")
except:
    api_key = "YOUR_LOCAL_KEY"

if api_key:
    genai.configure(api_key=api_key)

st.set_page_config(page_title="Invoice Extractor", layout="wide")
st.title("📄 Universal Invoice Data Extractor")

with st.sidebar:
    st.header("Settings")
    # Megadjuk a modell nevét fixen
    model_name = st.selectbox("Model:", ["gemini-1.5-flash", "gemini-1.5-pro"])
    columns_needed = st.text_input("Columns to extract:", "ArtNr, Preis")
    decimal_sep = st.selectbox("Decimal separator:", [",", "."])

uploaded_file = st.file_uploader("Upload Invoice (PDF)", type=["pdf"])

if uploaded_file and api_key:
    if st.button("Extract Data"):
        status = st.empty()
        status.info("Processing...")
        
        try:
            # A legstabilabb hívási mód
            model = genai.GenerativeModel(model_name)
            
            # PDF beolvasása binárisként
            pdf_bytes = uploaded_file.read()
            
            pdf_parts = [
                {
                    "mime_type": "application/pdf",
                    "data": pdf_bytes
                }
            ]
            
            prompt = f"""
            Extract the following columns from the invoice: {columns_needed}.
            Format: Tab-Separated Values (TSV).
            Decimal separator: '{decimal_sep}'.
            Return ONLY the data rows, no headers, no markdown blocks.
            """
            
            # Generálás
            response = model.generate_content([prompt, pdf_parts[0]])
            
            if response.text:
                status.success("Success!")
                # Megtisztítjuk a szöveget a felesleges sallangoktól
                clean_output = response.text.replace("```tsv", "").replace("```", "").strip()
                
                st.subheader("Results")
                st.text_area("Copy data from here:", clean_output, height=400)
                st.download_button("Download as Text", clean_output, file_name="invoice.txt")
            else:
                status.warning("The AI returned an empty response. Check the PDF content.")
                
        except Exception as e:
            st.error(f"Error details: {str(e)}")
            if "404" in str(e):
                st.info("💡 Tip: Try switching to 'gemini-1.5-pro' in the sidebar.")
