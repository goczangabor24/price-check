import streamlit as st
import google.generativeai as genai

# --- API KEY CLEANUP ---
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

# --- MODELL BEÁLLÍTÁSA ---
# Megpróbáljuk a legstabilabb módon betölteni
def get_model():
    return genai.GenerativeModel('gemini-1.5-flash')

with st.sidebar:
    st.header("Settings")
    columns_needed = st.text_input("Columns to extract:", "ArtNr, Preis")
    decimal_sep = st.selectbox("Decimal separator:", [",", "."])

uploaded_file = st.file_uploader("Upload Invoice (PDF)", type=["pdf"])

if uploaded_file and api_key:
    if st.button("Extract Data"):
        status = st.empty()
        status.info("Connecting to Google AI...")
        
        try:
            # Itt történik a változtatás: explicit hívás
            model = get_model()
            
            # PDF adat előkészítése
            file_data = uploaded_file.getvalue()
            
            prompt = f"""
            Analyze this invoice and extract: {columns_needed}.
            Format: Tab-Separated Values (TSV).
            Decimal separator: '{decimal_sep}'.
            Return ONLY raw data rows. No markdown, no headers.
            """
            
            status.info("Analyzing document... (this can take 15-30 seconds)")
            
            # A generálás folyamata
            response = model.generate_content([
                prompt,
                {"mime_type": "application/pdf", "data": file_data}
            ])
            
            if response.text:
                status.success("Done!")
                # Kitakarítjuk a választ
                clean_text = response.text.replace("```tsv", "").replace("```", "").strip()
                st.text_area("Extracted Data:", clean_text, height=400)
                st.download_button("Download Data", clean_text, file_name="invoice_data.txt")
            else:
                status.error("AI returned empty result.")
                
        except Exception as e:
            # Ha még mindig 404, kiírjuk a részleteket
            st.error(f"Error: {str(e)}")
            if "404" in str(e):
                st.warning("The model name might have changed. Try 'gemini-1.5-pro' in the code if 'flash' fails.")
