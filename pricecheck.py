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
    # Megjegyzés: A GPT-4o a legalkalmasabb PDF-ekhez
    model_name = st.selectbox("Model:", ["gpt-4o", "gpt-4o-mini"])
    columns_needed = st.text_input("Columns:", "ArtNr, Preis")

uploaded_file = st.file_uploader("Upload Invoice (PDF)", type=["pdf"])

if uploaded_file and api_key:
    if st.button("Extract Data"):
        status = st.empty()
        status.info("Analysing PDF...")
        
        try:
            client = OpenAI(api_key=api_key)
            
            # PDF beolvasása és kódolása
            pdf_bytes = uploaded_file.read()
            pdf_base64 = base64.b64encode(pdf_bytes).decode('utf-8')
            
            # Ez a formátum a legstabilabb a GPT-4o-nál PDF-ekhez
            response = client.chat.completions.create(
                model=model_name,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text", 
                                "text": f"Extract these columns as TSV: {columns_needed}. Only data rows, no headers."
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:application/pdf;base64,{pdf_base64}"
                                }
                            }
                        ],
                    }
                ],
                max_tokens=2000,
            )
            
            result = response.choices[0].message.content
            
            status.success("Success!")
            # Megtisztítjuk a markdown kódblokkoktól
            clean_output = result.replace("```tsv", "").replace("```", "").replace("`", "").strip()
            
            st.subheader("Extracted Data")
            st.text_area("Result:", clean_output, height=400)
            st.download_button("Download TSV", clean_output, file_name="invoice_data.txt")
            
        except Exception as e:
            st.error(f"Error: {str(e)}")
            st.info("Ensure your OpenAI account has credits and you are using GPT-4o.")

elif not api_key:
    st.warning("Please set OPENAI_API_KEY in Streamlit Secrets!")
