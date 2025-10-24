# components/alt_analysis.py

import streamlit as st
import json
import sys
import os

# Lisää juurihakemisto sys.pathiin
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from src.analysis.alt_analysis import run_alt_analysis, save_analysis_to_json


def show_alt_analysis_ui():
    st.header("Alt-tekstien analyysi (GPT-4o)")

    openai_api_key = st.text_input("Syötä OpenAI API -avain", type="password")

    images_input = st.text_area(
        "Liitä JSON-taulukko kuvista (src ja alt)",
        placeholder='[\n  {"src": "https://example.com/image.jpg", "alt": "vanha alt"}\n]',
        height=200
    )

    if st.button("Analysoi kuvat") and openai_api_key and images_input:
        try:
            images = json.loads(images_input)
            results = run_alt_analysis(images, openai_api_key)
            save_analysis_to_json(results)

            st.success(
                "Analyysi valmis. Tulokset tallennettu tiedostoon alt_analysis.json")
            st.write(results)
        except Exception as e:
            st.error(f"Virhe analysoidessa: {str(e)}")
