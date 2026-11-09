import os, re
from werkzeug.utils import secure_filename
import fitz
from docx import Document

ALLOWED={".pdf",".docx"}
def extract_text(path):
    ext=os.path.splitext(path)[1].lower()
    if ext==".pdf":
        doc=fitz.open(path)
        return "\n".join(page.get_text("text") for page in doc).strip()
    if ext==".docx":
        doc=Document(path)
        return "\n".join(p.text for p in doc.paragraphs).strip()
    raise ValueError("Only PDF and DOCX files are supported")

def parse_profile(text, filename):
    clean=" ".join((text or "").split())
    email=re.search(r'[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}',clean)
    phone=re.search(r'(?:\+?\d[\d\s()-]{8,}\d)',clean)
    exp=re.search(r'(\d+(?:\.\d+)?)\s*\+?\s*(?:years?|yrs?)\s+(?:of\s+)?experience',clean,re.I)
    skills=["Java","Spring Boot","Microservices","Hibernate","REST APIs","Python","React","SQL","Excel","KYC","AML","Node.js"]
    found=[s for s in skills if re.search(re.escape(s),clean,re.I)]
    # Keep names conservative: parsed from filename; recruiter can edit/verify.
    name=os.path.splitext(secure_filename(filename))[0].replace("_"," ").replace("-"," ").title()
    return {"name":name or "Unidentified candidate","experience":float(exp.group(1)) if exp else 0,
            "skills":found,"email":email.group(0) if email else None,
            "phone":phone.group(0) if phone else None,"cv_text":text or ""}
