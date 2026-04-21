import streamlit as st
import PyPDF2 
import os
import io
from openai import OpenAI
from dotenv import load_dotenv
from collections import Counter
import re


load_dotenv()

# ---------------- Session State Initialization ----------------
if "analysis_done" not in st.session_state:
    st.session_state.analysis_done = False

if "file_content" not in st.session_state:
    st.session_state.file_content = ""

st.set_page_config(page_title = "AI Resume Critiquer", page_icon= "📄", layout="wide")

st.title("AI resume Critiquer")
st.markdown("Upload your resume and get AI-powered, job specific feedback tailored to your needs!")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY)


#User Interface
st.sidebar.header("Options")

st.sidebar.markdown("### Job Context")
job_description = st.sidebar.text_area(
    "Paste Job Description (optional)",
    placeholder="Paste the full job description here to get tailored feedback...",
    height=200
)


job_role = st.sidebar.text_area(
    "Target Role (optional)",
    placeholder="e.g. Backend Software Engineer, Data Scientist",
    height=60
)
uploaded_file = st.file_uploader("Upload your resume (PDF or TXT)", type = ["pdf", "txt"])
analyze = st.button("Analyze Resume")


#Helper functions
def extract_text_from_pdf(pdf_file):
    pdf_reader = PyPDF2.PdfReader(pdf_file)
    text = ""
    for page in pdf_reader.pages:
        page_text = page.extract_text()
        if page_text:
            text += page_text + "\n"
    return text

def extract_text_from_file(uploaded_file):
    if uploaded_file.type == "application/pdf":
        return extract_text_from_pdf(io.BytesIO(uploaded_file.read()))
    return uploaded_file.read().decode("utf-8")

def extract_keywords(text):
    words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
    return Counter(words)



#Main logic
if analyze and uploaded_file:
    try:
        with st.spinner("Analyzing resume..."):
            file_content = extract_text_from_file(uploaded_file)
            st.session_state.file_content = file_content
            st.session_state.analysis_done = True

            if not file_content.strip():
                st.error("File does not have any content...")
                st.stop()

            # -------- Keyword Analysis --------
            resume_keywords = extract_keywords(file_content)

            jd_keywords = {}
            if job_description:
                jd_keywords = extract_keywords(job_description)

            matched = set(resume_keywords.keys()) & set(jd_keywords.keys())
            missing = set(jd_keywords.keys()) - set(resume_keywords.keys())

            # AI prompt
            prompt  = f"""
            You are an expert resume reviewer.

            Analyze the resume based on:
            - Content clarity and impact
            - Skills presentation
            - Experience quality
            - Alignment with job role: {job_role if job_role else "General"}

            If a job description is provided, compare against it.

            Provide:
            1. Strengths
            2. Weaknesses
            3. Specific improvements
            4. Bullet-point rewrite suggestions
            5. A score out of 100 broken into:
               - Skills Match
               - Experience
               - Impact
               - Formatting

                
            Resume:
            {file_content}

            Job Description:
            {job_description if job_description else "Not provided"}               
            """
            

            response = client.chat.completions.create(
                model= "gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are an expert resume reviewer with years of experience in HR and recruitment" },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=1200
            )

        # Output UI
        tab1, tab2, tab3 = st.tabs(["Summary", "Keyword Analysis", "Full Feedback"])

        with tab1:
            st.markdown("## Resume Summary & Score")
            st.markdown(response.choices[0].message.content)

        with tab2:
            st.markdown("## Keyword Analysis")

            if job_description:
                st.write("### Matched Keywords")
                st.write(", ".join(list(matched)[:20]))

                st.write("### Missing Keywords")
                st.write(", ".join(list(missing)[:20]))
            else:
                st.info("Add a job description to see keyword matching.")

        with tab3:
            st.markdown("## Detailed Feedback")
            st.markdown(response.choices[0].message.content)

        
    except Exception as e:
        st.error(f"An error occured: {str(e)}")


# Improve Resume feature
# ---------------- Improve Resume Feature ----------------
if st.session_state.get("analysis_done", False):

    st.divider()

    st.markdown("## Improve Your Resume")

    if "improved_text" not in st.session_state:
        st.session_state.improved_text = ""

    if st.button("Generate Improved Bullet Points"):

        with st.spinner("Rewriting resume content..."):

            improve_prompt = f"""
            Rewrite the following resume content into strong, impact-driven bullet points.
            Use action verbs and include measurable results where possible.

            Resume:
            {st.session_state.file_content}
            """

            improved = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are an expert resume writer."},
                    {"role": "user", "content": improve_prompt}
                ],
                temperature=0.6,
                max_tokens=800
            )

            # STORE RESULT
            st.session_state.improved_text = improved.choices[0].message.content

            st.success("Improved version generated below 👇")

    # ALWAYS DISPLAY IF AVAILABLE
    if st.session_state.improved_text:
        st.markdown(st.session_state.improved_text)

        st.download_button(
            "Download Improved Version",
            st.session_state.improved_text,
            file_name="improved_resume.txt"
        )