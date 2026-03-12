import streamlit as st
from openai import OpenAI
import base64

# --- API KULCS KEZELÉSE ---
api_key = ""
if "OPENAI_API_KEY" in st.secrets:
    api_key = st.secrets["OPENAI_API_KEY"].strip()

st.set_page_config(page_title="Invoice Extractor (ChatGPT)", layout="wide")
st.title("📄 ChatGPT Invoice Data Extractor")

with st.sidebar:
    st.header("Settings")
    # A gpt-4o a legjobb a dokumentumokhoz
    model_name = st.selectbox("Model:", ["gpt-4o", "gpt-4o-mini"])
    columns_needed = st.text_input("Columns to extract:", "ArtNr, Preis")

uploaded_file = st.file_uploader("Upload Invoice (PDF)", type=["pdf"])

if uploaded_file and api_key:
    if st.button("Extract Data"):
        status = st.empty()
        status.info("Connecting to OpenAI...")
        
        try:
            client = OpenAI(api_key=api_key)
            
            # PDF átalakítása Base64-be
            pdf_base64 = base64.b64encode(uploaded_file.read()).decode('utf-8')
            
            # ChatGPT kérés összeállítása
            response = client.chat.completions.create(
                model=model_name,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": f"Extract these columns as TSV data: {columns_needed}. No headers, no talk."},
                            {
                                "type": "input_file",
                                "input_file": {
                                    "data": pdf_base64,
                                    "format": "pdf"
                                }
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
            st.error(f"Error: {str(e)}")

elif not api_key:
    st.warning("Add your OPENAI_API_KEY to Streamlit Secrets!")
