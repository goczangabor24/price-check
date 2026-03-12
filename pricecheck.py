import streamlit as st
import google.generativeai as genai
import time

# --- CONFIGURATION ---
try:
    api_key = st.secrets["GOOGLE_API_KEY"]
except:
    api_key = "YOUR_LOCAL_API_KEY_HERE"

genai.configure(api_key=api_key)

st.set_page_config(page_title="Invoice Extractor", layout="wide")
st.title("📄 Universal Invoice Data Extractor")

with st.sidebar:
    st.header("Settings")
    columns_needed = st.text_input("Columns to extract:", "ArtNr, Preis")
    decimal_sep = st.selectbox("Decimal separator:", [",", "."])
    show_debug = st.checkbox("Show technical details (Debug)")

uploaded_file = st.file_uploader("Upload Invoice (PDF)", type=["pdf"])

if uploaded_file:
    if st.button("Extract Data"):
        status_container = st.empty()
        status_container.info("Initializing Gemini AI...")
        
        try:
            model = genai.GenerativeModel('gemini-1.5-flash')
            pdf_data = uploaded_file.read()
            
            prompt = f"""
            Analyze the uploaded invoice and extract these columns: {columns_needed}.
            Format: Tab-Separated Values (TSV). Use '{decimal_sep}' for decimals.
            Provide ONLY raw data rows, no headers, no conversational text.
            """
            
            status_container.info("Sending file to Google servers... (this may take 10-20 seconds)")
            
            # Időmérés a biztonság kedvéért
            start_time = time.time()
            
            response = model.generate_content([
                prompt,
                {"mime_type": "application/pdf", "data": pdf_data}
            ])
            
            end_time = time.time()
            
            if show_debug:
                st.write(f"Response time: {end_time - start_time:.2f} seconds")

            # Válasz tisztítása
            result_text = response.text.strip().replace("```", "").replace("tsv", "")

            if result_text:
                status_container.success("Extraction complete!")
                st.subheader("Extracted Results")
                st.text_area("Raw Data (Copyable):", result_text, height=300)
                
                st.download_button(
                    label="Download Results",
                    data=result_text,
                    file_name="invoice_data.txt"
                )
            else:
                status_container.error("The AI returned an empty response. Try more specific column names.")
                
        except Exception as e:
            status_container.error(f"An error occurred during processing.")
            st.exception(e) # Ez kiírja a pontos hibaüzenetet
