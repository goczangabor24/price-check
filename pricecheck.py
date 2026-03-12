import streamlit as st
import google.generativeai as genai
import pandas as pd
import io

# --- CONFIGURATION ---
# When running online, set your API key in Streamlit Cloud: 
# Settings -> Secrets -> GOOGLE_API_KEY = "your_key"
try:
    api_key = st.secrets["GOOGLE_API_KEY"]
except:
    api_key = "YOUR_LOCAL_API_KEY_HERE" # For local testing only

genai.configure(api_key=api_key)

# --- UI SETUP ---
st.set_page_config(page_title="Universal Invoice Extractor", layout="wide")
st.title("📄 Universal Invoice Data Extractor")
st.write("Upload an invoice PDF and specify the columns you want to extract.")

# --- SIDEBAR / INPUTS ---
with st.sidebar:
    st.header("Settings")
    columns_needed = st.text_input(
        "Columns to extract (comma separated):", 
        "ArtNr, Description, Quantity, Price"
    )
    decimal_sep = st.selectbox("Decimal separator in output:", [",", "."])
    st.info("The AI will identify these columns even if they have different names on the invoice.")

uploaded_file = st.file_uploader("Upload Invoice (PDF)", type=["pdf"])

# --- PROCESSING ---
if uploaded_file:
    if st.button("Extract Data"):
        with st.spinner("Analyzing document structure and extracting data..."):
            try:
                # Initialize Gemini 1.5 Flash (fast and cost-effective)
                model = genai.GenerativeModel('gemini-1.5-flash')
                
                # Prepare PDF for the model
                pdf_data = uploaded_file.read()
                
                # Refined prompt for clean output
                prompt = f"""
                Extract the following columns from this invoice: {columns_needed}.
                Instructions:
                1. Return the data in a raw, tab-separated format (TSV).
                2. Use '{decimal_sep}' as the decimal separator for numbers.
                3. Do not include any headers in the response.
                4. Only return the data rows, no conversational text or markdown code blocks.
                5. If a column is missing for a row, leave it empty.
                """
                
                # Generate content
                response = model.generate_content([
                    prompt,
                    {"mime_type": "application/pdf", "data": pdf_data}
                ])
                
                # --- RESULTS ---
                st.subheader("Extracted Data")
                raw_data = response.text.strip()
                
                if raw_data:
                    # Display as text area for easy copying
                    st.text_area("Raw Output (Tab Separated):", raw_data, height=300)
                    
                    # Create a download button
                    st.download_button(
                        label="Download as TSV (for Excel)",
                        data=raw_data,
                        file_name="extracted_invoice_data.txt",
                        mime="text/tab-separated-values"
                    )
                else:
                    st.warning("No data could be extracted. Please check the PDF or column names.")
                    
            except Exception as e:
                st.error(f"An error occurred: {str(e)}")

# --- FOOTER ---
st.divider()
st.caption("Powered by Google Gemini 1.5 & Streamlit")
