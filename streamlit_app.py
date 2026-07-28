import os
import tempfile

import streamlit as st

from matcher_pipeline import run_matching

st.set_page_config(page_title="SKU Image Matcher", page_icon="🔎", layout="centered")

st.title("SKU Image Matcher")
st.caption("Match low-quality AIAS images back to their real client SKU by visual similarity.")

st.header("1. Get the template")
st.write("Download the template, fill in the `Client_Data` and `AIAS` sheets, then upload it below.")

TEMPLATE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "Image_Matching_Template.xlsx")
with open(TEMPLATE_PATH, "rb") as f:
    st.download_button(
        "Download Template",
        data=f.read(),
        file_name="Image_Matching_Template.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

st.header("2. Upload your filled-in workbook")
uploaded_file = st.file_uploader("Choose an .xlsx file", type=["xlsx"])

if uploaded_file is not None:
    if st.button("Run Matching"):
        with tempfile.TemporaryDirectory() as tmp_dir:
            input_path = os.path.join(tmp_dir, "input.xlsx")
            output_path = os.path.join(tmp_dir, "output.xlsx")

            with open(input_path, "wb") as f:
                f.write(uploaded_file.getbuffer())

            progress_bar = st.progress(0, text="Starting...")

            def update_progress(done, total):
                pct = int(done / total * 100) if total else 100
                progress_bar.progress(pct, text=f"Comparing images... {done}/{total}")

            try:
                summary = run_matching(input_path, output_path, progress_callback=update_progress)
            except Exception as e:
                st.error(f"Error: {e}")
                st.stop()

            progress_bar.progress(100, text="Done")

            st.success("Matching complete")
            col1, col2, col3 = st.columns(3)
            col1.metric("Matched", summary["matched"])
            col2.metric("Unmatched AIAS", summary["unmatched_aias"])
            col3.metric("Unmatched Client", summary["unmatched_client"])

            with open(output_path, "rb") as f:
                st.download_button(
                    "Download Results",
                    data=f.read(),
                    file_name="Matched_Results.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
