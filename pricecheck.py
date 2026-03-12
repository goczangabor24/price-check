import streamlit as st
import requests
import base64

# --- API KULCS TISZTÍTÁSA ---
api_key = ""
if "GOOGLE_API_KEY" in st.secrets:
    api_key = st.secrets["GOOGLE_API_KEY"].strip().replace('"', '').replace("'", "")

st.set_page_config(page_title="Invoice Extractor", layout="wide")
st.title("📄 Smart Invoice Extractor")

with st.sidebar:
    st.header("Settings")
    # Kipróbáljuk az összes lehetséges variációt
    model_options = [
        "gemini-1.5-flash-latest", 
        "gemini-1.5-flash", 
        "gemini-1.5-pro-latest",
        "gemini-1.5-flash-001"
    ]
    model_name = st.selectbox("Select Model Variant:", model_options)
    columns_needed = st.text_input("Columns:", "ArtNr, Preis")

uploaded_file = st.file_uploader("Upload Invoice (PDF)", type=["pdf"])

if uploaded_file and api_key:
    if st.button("Extract Data"):
        status = st.empty()
        
        try:
            pdf_base64 = base64.b64encode(uploaded_file.read()).decode('utf-8')
            
            # Próbálkozunk a v1beta végponttal (ez a legvalószínűbb a PDF-hez)
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
            
            status.info(f"Trying model: {model_name}...")
            
            payload = {
                "contents": [{
                    "parts": [
                        {"text": f"Extract {columns_needed} from this invoice as TSV rows. No headers."},
                        {"inline_data": {"mime_type": "application/pdf", "data": pdf_base64}}
                    ]
                }]
            }

            response = requests.post(url, json=payload)
            
            if response.status_code == 200:
                res_data = response.json()
                text = res_data['candidates'][0]['content']['parts'][0]['text']
                status.success(f"Success with {model_name}!")
                st.text_area("Results:", text.replace("```", "").strip(), height=400)
            else:
                # Ha 404, kiírjuk a pontos választ a Google-től
                st.error(f"Model {model_name} failed (Error {response.status_code})")
                st.write("Google's reason:", response.json().get('error', {}).get('message'))
                st.info("💡 Try selecting a different model variant from the sidebar!")
                
        except Exception as e:
            st.error(f"Fatal error: {str(e)}")

elif not api_key:
    st.warning("API Key missing from Streamlit Secrets!")
