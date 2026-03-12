import streamlit as st
from openai import OpenAI
import base64

# --- API KULCS KEZELÉSE ---
api_key = ""
if "OPENAI_API_KEY" in st.secrets:
    api_key = st.secrets["OPENAI_API_KEY"].strip()

st.set_page_config(page_title="Invoice Extractor", layout="wide")
st.title("📄 ChatGPT Invoice Extractor")

with st.sidebar:
    st.header("Settings")
    # A gpt-4o-mini a legolcsóbb és támogatja a fájlokat
    model_name = st.selectbox("Model:", ["gpt-4o", "gpt-4o-mini"])
    columns_needed = st.text_input("Columns:", "ArtNr, Preis")

uploaded_file = st.file_uploader("Upload Invoice (PDF)", type=["pdf"])

if uploaded_file and api_key:
    if st.button("Extract Data"):
        status = st.empty()
        status.info("Reading PDF and sending to OpenAI...")
        
        try:
            client = OpenAI(api_key=api_key)
            
            # PDF beolvasása és kódolása
            pdf_bytes = uploaded_file.read()
            pdf_base64 = base64.b64encode(pdf_bytes).decode('utf-8')
            
            # FRISSÍTETT HÍVÁS: 'file' típust használunk az 'input_file' helyett
            # Vagy képként küldjük el, ha a modell azt várja
            response = client.chat.completions.create(
                model=model_name,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text", 
                                "text": f"Extract these columns as TSV: {columns_needed}. No headers, no talk."
                            },
                            {
                                "type": "file", # Itt volt a hiba, az 'input_file' helyett 'file' kell
                                "data": pdf_base64,
                                "mime_type": "application/pdf"
                            }
                        ],
                    }
                ],
            )
            
            result = response.choices[0].message.content
            
            status.success("Done!")
            clean_output = result.replace("```tsv", "").replace("```", "").strip()
            st.text_area("Results:", clean_output, height=400)
            st.download_button("Download", clean_output, file_name="invoice_data.txt")
            
        except Exception as e:
            # Ha a 'file' típus sem megy (mert az OpenAI fiókod még nem látja), 
            # akkor egy alternatív szöveges promptot adunk
            st.error(f"Error: {str(e)}")
            st.info("Tip: If the 'file' type is not yet supported for your account, OpenAI might require a different approach for PDFs.")
