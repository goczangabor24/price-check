import streamlit as st
import requests
import base64

# --- CONFIGURATION ---
api_key = ""
if "GOOGLE_API_KEY" in st.secrets:
    api_key = st.secrets["GOOGLE_API_KEY"].strip().strip('"').strip("'")

st.set_page_config(page_title="Invoice Extractor", layout="wide")
st.title("📄 Direct Invoice Data Extractor")

with st.sidebar:
    st.header("Settings")
    # Két különböző végpontot is kipróbálhatunk
    model_version = st.selectbox("Model:", ["gemini-1.5-flash", "gemini-1.5-pro"])
    columns_needed = st.text_input("Columns:", "ArtNr, Preis")
    decimal_sep = st.selectbox("Decimal separator:", [",", "."])

uploaded_file = st.file_uploader("Upload Invoice (PDF)", type=["pdf"])

if uploaded_file and api_key:
    if st.button("Extract Data"):
        status = st.empty()
        status.info("Sending direct request to Google API...")
        
        try:
            # PDF átalakítása Base64 formátumba
            pdf_base64 = base64.b64encode(uploaded_file.read()).decode('utf-8')
            
            # Közvetlen URL a Google API-hoz (v1 stabil verzió!)
            url = f"https://generativelanguage.googleapis.com/v1/models/{model_version}:generateContent?key={api_key}"
            
            headers = {'Content-Type': 'application/json'}
            
            payload = {
                "contents": [{
                    "parts": [
                        {"text": f"Extract these columns: {columns_needed}. Format: TSV. Decimal: '{decimal_sep}'. Only raw data rows, no headers."},
                        {
                            "inline_data": {
                                "mime_type": "application/pdf",
                                "data": pdf_base64
                            }
                        }
                    ]
                }],
                "generationConfig": {
                    "temperature": 0.1,
                    "topP": 0.95,
                }
            }

            response = requests.post(url, json=payload, headers=headers)
            res_json = response.json()

            if response.status_code == 200:
                # Kinyerjük a szöveget a válaszból
                raw_text = res_json['candidates'][0]['content']['parts'][0]['text']
                status.success("Done!")
                
                clean_output = raw_text.replace("```tsv", "").replace("```", "").strip()
                st.text_area("Extracted Results:", clean_output, height=400)
                st.download_button("Download TSV", clean_output, file_name="data.txt")
            else:
                # Itt kiírjuk a pontos hibát, ha a Google nemet mond
                st.error(f"API Error {response.status_code}: {res_json.get('error', {}).get('message', 'Unknown error')}")
                
        except Exception as e:
            st.error(f"System Error: {str(e)}")

elif not api_key:
    st.warning("Please set your GOOGLE_API_KEY in Streamlit Secrets!")
