# 📁 /backend/main.py
from fastapi import FastAPI, HTTPException, File, UploadFile, Form

from fastapi.middleware.cors import CORSMiddleware
import os
import google.generativeai as genai
from dotenv import load_dotenv
from io import BytesIO
import docx
import pdfplumber

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

GEMINI_API_KEY = "AIzaSyCtuOKC0ykaMkTzQfiTrqIGmh-qxm_Sr-Y"
if not GEMINI_API_KEY:
    raise ValueError("Missing GEMINI_API_KEY")

# Update to Gemini 2.0 Flash
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.0-flash")  # Change this to use Gemini 2.0 Flash

def extract_text_from_docx(file: UploadFile):
    """Extract text from DOCX file"""
    try:
        doc = docx.Document(BytesIO(file.file.read()))
        return '\n'.join([para.text for para in doc.paragraphs])
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error reading DOCX file: {e}")

def extract_text_from_pdf(file: UploadFile):
    """Extract text from PDF file"""
    try:
        pdf_text = ""
        with pdfplumber.open(BytesIO(file.file.read())) as pdf:
            for page in pdf.pages:
                pdf_text += page.extract_text()
        return pdf_text
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error reading PDF file: {e}")

def extract_text_from_file(file: UploadFile):
    """Extract text from different file formats (.pdf, .docx)"""
    if file.filename.endswith(".docx"):
        return extract_text_from_docx(file)
    elif file.filename.endswith(".pdf"):
        return extract_text_from_pdf(file)
    else:
        raise HTTPException(status_code=400, detail="Unsupported file format. Please upload a .pdf or .docx file.")

import re

@app.post("/analyze")
async def analyze(
    jdText: str = Form(...),
    resume_file: UploadFile = File(...)
):
    resume_text = extract_text_from_file(resume_file)

    prompt = f"""
    You are a resume analyzer. Compare the resume and job description:
    Resume:
    {resume_text}

    Job Description:
    {jdText}

    1. Give a match score between 0 to 100.
    2. List missing important skills or keywords in the resume.
    3. Give a short explanation for the score.
    Return the result in clean plain text without any bullet marks or markdown syntax.
    """

    try:
        response = model.generate_content(prompt)
        # Remove bullet marks and markdown stars
        cleaned_text = re.sub(r'\*\*|\*|•|-', '', response.text)
        return {"result": cleaned_text.strip()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

