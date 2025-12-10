# backend/utils.py
import os
from pathlib import Path
from werkzeug.utils import secure_filename
from config import ALLOWED_EXTENSIONS, UPLOAD_FOLDER, logger
from PyPDF2 import PdfReader
from docx import Document
import time

def allowed_file(filename):
    """检查文件是否允许"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_upload_file(file):
    """保存上传的文件"""
    try:
        if not allowed_file(file.filename):
            return None, f"不支持的文件类型：{file.filename.rsplit('.', 1)[1]}"
        
        filename = secure_filename(file.filename)
        filename = f"{int(time.time())}_{filename}"
        
        file_path = UPLOAD_FOLDER / filename
        file.save(str(file_path))
        
        logger.info(f"文件保存成功：{filename}")
        return str(file_path), None
    except Exception as e:
        logger.error(f"文件保存失败：{str(e)}")
        return None, str(e)

def extract_text_from_pdf(file_path):
    """从 PDF 提取文本"""
    try:
        text = ""
        with open(file_path, 'rb') as f:
            pdf_reader = PdfReader(f)
            for page_num, page in enumerate(pdf_reader.pages):
                text += f"\n--- 第 {page_num + 1} 页 ---\n"
                text += page.extract_text()
        return text
    except Exception as e:
        logger.error(f"PDF 提取失败：{str(e)}")
        raise

def extract_text_from_docx(file_path):
    """从 DOCX 提取文本"""
    try:
        doc = Document(file_path)
        text = ""
        for para in doc.paragraphs:
            text += para.text + "\n"
        return text
    except Exception as e:
        logger.error(f"DOCX 提取失败：{str(e)}")
        raise

def extract_text_from_markdown(file_path):
    """从 Markdown 提取文本"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            text = f.read()
        return text
    except Exception as e:
        logger.error(f"Markdown 提取失败：{str(e)}")
        raise

def extract_text_from_txt(file_path):
    """从 TXT 提取文本"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            text = f.read()
        return text
    except Exception as e:
        logger.error(f"TXT 提取失败：{str(e)}")
        raise

def extract_text(file_path):
    """根据文件类型提取文本"""
    file_ext = Path(file_path).suffix.lower()
    
    if file_ext == '.pdf':
        return extract_text_from_pdf(file_path)
    elif file_ext == '.docx':
        return extract_text_from_docx(file_path)
    elif file_ext == '.md':
        return extract_text_from_markdown(file_path)
    elif file_ext == '.txt':
        return extract_text_from_txt(file_path)
    else:
        raise ValueError(f"不支持的文件格式：{file_ext}")
