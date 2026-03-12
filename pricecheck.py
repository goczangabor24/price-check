import streamlit as st
import google.generativeai as genai

# 1. API Kulcs tisztítása
api_key = ""
if "GOOGLE_API_KEY" in st.secrets:
    api_key = st.secrets["GOOGLE_API_KEY"].strip().strip('"').strip("'")

if api_key:
    genai.configure(api_key=api_key)

st.set_page_config(page_title="Invoice Extractor", layout="wide")
st.title("📄 Invoice Data Extractor")

# 2. Beállítások a szélen
with st.sidebar:
    st.header("Settings")
    # Ha a flash nem létezik, a pro-val biztosan menni fog
    model_choice = st.selectbox("Model Version:", ["gemini-1.5-flash", "gemini-1.5-pro"])
    columns_needed = st.text_input("Columns to extract:", "ArtNr, Preis")
    decimal_sep = st.selectbox("Decimal separator:", [",", "."])

uploaded_file = st.file_uploader("Upload Invoice (PDF)", type=["pdf"])

if uploaded_file and api_key:
    if st.button("Extract Data"):
        status = st.empty()
        status.info("Processing...")
        
        try:
            # Modell példányosítása
            model = genai.GenerativeModel(model_name=model_choice)
            
            # Fájl beolvasása
            pdf_bytes = uploaded_file.read()
            
            # A kérés összeállítása (ez a legstabilabb formátum)
            prompt = (
                f"Extract these columns from the PDF: {columns_needed}. "
                f"Use Tab-Separated Values (TSV) format. "
                f"Use '{decimal_sep}' as decimal separator. "
                "Return ONLY the raw data rows, no headers, no chat, no markdown blocks."
            )
            
            # Küldés a Google-nek
            response = model.generate_content([
                {"mime_type": "application/pdf", "data": pdf_bytes},
                prompt
            ])
            
            if response.text:
                status.success("Success!")
                # Megszabadulunk a kódblokk jelektől ha a modell mégis betenné
                result = response.text.replace("```tsv", "").replace("```", "").strip()
                
                st.subheader("Extracted Data")
                st.text_area("Copy output:", result, height=400)
                st.download_button("Download as TXT", result, file_name="invoice_data.txt")
            else:
                status.error("AI returned empty text.")

        except Exception as e:
            # Ha 404 hiba jön, adjunk tanácsot a felhasználónak
            err_msg = str(e)
            st.error(f"Error: {err_msg}")
            if "404" in err_msg:
                st.warning("⚠️ The 'Flash' model is currently unavailable in your region or API version. "
                           "Please select 'gemini-1.5-pro' in the sidebar and try again!")

elif not api_key:
    st.warning("Please add your GOOGLE_API_KEY to Streamlit Secrets!")
