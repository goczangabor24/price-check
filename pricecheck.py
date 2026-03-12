import streamlit as st
import google.generativeai as genai

# --- API KULCS TISZTÍTÁSA ÉS BETÖLTÉSE ---
raw_key = ""
try:
    if "GOOGLE_API_KEY" in st.secrets:
        raw_key = st.secrets["GOOGLE_API_KEY"]
    else:
        st.error("Missing API Key in Secrets!")
except:
    raw_key = "YOUR_LOCAL_KEY"

# Eltávolítja az esetleges szóközöket vagy idézőjeleket, amik a hibát okozzák
api_key = raw_key.strip().strip('"').strip("'")

if api_key:
    genai.configure(api_key=api_key)

st.set_page_config(page_title="Invoice Extractor", layout="wide")
st.title("📄 Universal Invoice Data Extractor")

with st.sidebar:
    st.header("Settings")
    columns_needed = st.text_input("Columns to extract:", "ArtNr, Preis")
    decimal_sep = st.selectbox("Decimal separator:", [",", "."])

uploaded_file = st.file_uploader("Upload Invoice (PDF)", type=["pdf"])

if uploaded_file and api_key:
    if st.button("Extract Data"):
        # Egy üres helyfoglaló a státuszüzeneteknek
        status = st.empty()
        status.info("Connecting to Google AI...")
        
        try:
            model = genai.GenerativeModel('gemini-1.5-flash')
            pdf_parts = [
                {
                    "mime_type": "application/pdf",
                    "data": uploaded_file.getvalue()
                }
            ]
            
            prompt = f"""
            Extract these columns: {columns_needed}.
            Format: Tab-Separated Values (TSV). Use '{decimal_sep}' for decimals.
            Return ONLY raw rows. No headers, no markdown blocks.
            """
            
            status.info("Analyzing document... (this can take 15-30 seconds)")
            response = model.generate_content([prompt, pdf_parts[0]])
            
            # Válasz megjelenítése
            if response.text:
                status.success("Done!")
                clean_text = response.text.strip().replace("```", "").replace("tsv", "")
                st.text_area("Results:", clean_text, height=400)
                st.download_button("Download TSV", clean_text, file_name="invoice.txt")
            else:
                status.error("AI returned empty result.")
                
        except Exception as e:
            status.error(f"API Error: {str(e)}")
            st.warning("Tip: Check if your API key has leading/trailing spaces in Streamlit Secrets.")
