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
        file.file.seek(0)  # Reset file pointer
        doc = docx.Document(BytesIO(file.file.read()))
        return '\n'.join([para.text for para in doc.paragraphs])
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error reading DOCX file: {e}")

def extract_text_from_pdf(file: UploadFile):
    """Extract text from PDF file"""
    try:
        file.file.seek(0)  # Reset file pointer
        pdf_text = ""
        with pdfplumber.open(BytesIO(file.file.read())) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    pdf_text += text
        return pdf_text
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error reading PDF file: {e}")

def extract_text_from_txt(file: UploadFile):
    """Extract text from TXT file"""
    try:
        file.file.seek(0)  # Reset file pointer
        content = file.file.read()
        # Try to decode with UTF-8, fall back to other encodings if needed
        try:
            return content.decode('utf-8')
        except UnicodeDecodeError:
            try:
                return content.decode('latin-1')
            except UnicodeDecodeError:
                return content.decode('utf-8', errors='ignore')
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error reading TXT file: {e}")

def extract_text_from_file(file: UploadFile):
    """Extract text from different file formats (.pdf, .docx, .txt)"""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")
        
    filename_lower = file.filename.lower()
    if filename_lower.endswith((".docx", ".doc")):
        return extract_text_from_docx(file)
    elif filename_lower.endswith(".pdf"):
        return extract_text_from_pdf(file)
    elif filename_lower.endswith(".txt"):
        return extract_text_from_txt(file)
    else:
        raise HTTPException(status_code=400, detail="Unsupported file format. Please upload a .pdf, .docx, .doc, or .txt file.")

import re

@app.post("/analyze")
async def analyze(
    resume_file: UploadFile = File(...),
    jd_file: UploadFile = File(...)
):
    # Validate files are provided
    if not resume_file.filename:
        raise HTTPException(status_code=400, detail="Resume file is required")
    if not jd_file.filename:
        raise HTTPException(status_code=400, detail="Job description file is required")
    
    try:
        # Extract text from both files
        resume_text = extract_text_from_file(resume_file)
        jd_text = extract_text_from_file(jd_file)
        
        # Validate that text was extracted
        if not resume_text.strip():
            raise HTTPException(status_code=400, detail="Could not extract text from resume file. Please check the file format and content.")
        if not jd_text.strip():
            raise HTTPException(status_code=400, detail="Could not extract text from job description file. Please check the file format and content.")

        prompt = f"""
        You are a resume analyzer. Compare the resume and job description:
        Resume:
        {resume_text}

        Job Description:
        {jd_text}

        1. Give a match score between 0 to 100.
        2. List missing important skills or keywords in the resume.
        3. Give a short explanation for the score.
        Return the result in clean plain text without any bullet marks or markdown syntax.
        """

        response = model.generate_content(prompt)
        # Remove bullet marks and markdown stars
        cleaned_text = re.sub(r'\*\*|\*|•|-', '', response.text)
        return {"result": cleaned_text.strip()}
    except HTTPException:
        # Re-raise HTTP exceptions as they are
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing files: {str(e)}")

