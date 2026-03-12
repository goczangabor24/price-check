import streamlit as st
import requests
import base64
import json

# --- API KULCS TISZTÍTÁSA ---
api_key = ""
if "GOOGLE_API_KEY" in st.secrets:
    # Nagyon fontos: minden felesleges karaktert leirtunk
    api_key = st.secrets["GOOGLE_API_KEY"].strip().replace('"', '').replace("'", "")

st.set_page_config(page_title="Invoice Extractor", layout="wide")
st.title("📄 Direct PDF Extractor (v1beta)")

with st.sidebar:
    st.header("Settings")
    # Itt a v1beta-t használjuk, mert a 1.5-ös modellek ott laknak
    model_name = st.selectbox("Model:", ["gemini-1.5-flash", "gemini-1.5-pro"])
    columns_needed = st.text_input("Columns:", "ArtNr, Preis")

uploaded_file = st.file_uploader("Upload Invoice (PDF)", type=["pdf"])

if uploaded_file and api_key:
    if st.button("Extract Data"):
        status = st.empty()
        status.info("Processing via v1beta endpoint...")
        
        try:
            pdf_base64 = base64.b64encode(uploaded_file.read()).decode('utf-8')
            
            # A TITOK: v1 helyett v1beta kell a PDF-hez!
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
            
            payload = {
                "contents": [{
                    "parts": [
                        {"text": f"Extract these columns as TSV: {columns_needed}. Only rows, no headers."},
                        {
                            "inline_data": {
                                "mime_type": "application/pdf",
                                "data": pdf_base64
                            }
                        }
                    ]
                }]
            }

            response = requests.post(url, json=payload)
            res_data = response.json()

            if response.status_code == 200:
                if 'candidates' in res_data:
                    text = res_data['candidates'][0]['content']['parts'][0]['text']
                    status.success("Success!")
                    st.text_area("Result:", text.replace("```", "").strip(), height=400)
                else:
                    st.error("Unexpected response format.")
                    st.json(res_data)
            else:
                st.error(f"Error {response.status_code}: {res_data.get('error', {}).get('message')}")
                
        except Exception as e:
            st.error(f"Fatal error: {str(e)}")

elif not api_key:
    st.warning("Please check your API Key in Streamlit Secrets!")
