import streamlit as st
import google.generativeai as genai
from PIL import Image

# --- API KULCS ---
api_key = ""
if "GOOGLE_API_KEY" in st.secrets:
    api_key = st.secrets["GOOGLE_API_KEY"].strip().replace('"', '').replace("'", "")

if api_key:
    genai.configure(api_key=api_key)

st.set_page_config(page_title="Invoice Extractor", layout="wide")
st.title("🖼️ Image-Based Invoice Extractor")

with st.sidebar:
    st.header("Settings")
    columns_needed = st.text_input("Columns:", "ArtNr, Preis")

# Most KÉPET várunk (JPG, PNG)
uploaded_file = st.file_uploader("Upload Invoice (IMAGE - JPG/PNG)", type=["jpg", "jpeg", "png"])

if uploaded_file and api_key:
    # Megjelenítjük a képet kicsiben
    image = Image.open(uploaded_file)
    st.image(image, caption="Uploaded Invoice", width=300)
    
    if st.button("Extract Data"):
        status = st.empty()
        status.info("Gemini is reading the image...")
        
        try:
            model = genai.GenerativeModel('gemini-1.5-flash')
            
            prompt = f"""
            Extract the following columns from this image: {columns_needed}. 
            Format: Tab-Separated Values (TSV). 
            Return ONLY the raw data rows, no headers, no intro.
            """
            
            # Kép küldése a Gemini-nek
            response = model.generate_content([prompt, image])
            
            if response.text:
                status.success("Done!")
                clean_output = response.text.replace("```tsv", "").replace("```", "").strip()
                st.text_area("Results:", clean_output, height=400)
            else:
                st.warning("No data found on the image.")
                
        except Exception as e:
            st.error(f"Error: {str(e)}")

elif not api_key:
    st.warning("Please add GOOGLE_API_KEY to Secrets!")
