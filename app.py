from flask import Flask, request, render_template, jsonify, send_file
import pytesseract
import os
from PIL import Image
import ollama
from ollama import chat
import docx
import PyPDF2
import markdown
import io

app = Flask(__name__)

pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

FEEDBACK_DATA = {}  # Store feedback and position

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_resume():
    if 'resume' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files['resume']
    position = request.form['position']

    if file.filename == '':
        return jsonify({"error": "No file selected"}), 400

    file_path = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(file_path)

    extracted_text = extract_text_from_resume(file_path)

    if "Error extracting text" in extracted_text:
        os.remove(file_path)
        return jsonify({"error": extracted_text}), 500

    print("Extracted Text:", extracted_text)

    feedback = get_resume_feedback(extracted_text, position)

    try:
        os.remove(file_path)
    except Exception as remove_error:
        print(f"Error deleting file: {remove_error}")

    FEEDBACK_DATA['feedback'] = feedback
    FEEDBACK_DATA['position'] = position

    return jsonify({"feedback": feedback})

def extract_text_from_resume(file_path):
    file_ext = os.path.splitext(file_path)[1].lower()

    try:
        if file_ext == '.docx':
            doc = docx.Document(file_path)
            full_text = []
            for paragraph in doc.paragraphs:
                full_text.append(paragraph.text)
            return '\n'.join(full_text)

        elif file_ext == '.pdf':
            pdf_reader = PyPDF2.PdfFileReader(open(file_path, 'rb'))
            full_text = []
            for page_num in range(pdf_reader.numPages):
                page = pdf_reader.getPage(page_num)
                full_text.append(page.extract_text())
            return '\n'.join(full_text)

        elif file_ext in ['.png', '.jpg', '.jpeg']:
            img = Image.open(file_path)
            return pytesseract.image_to_string(img)

        else:
            return "Unsupported file type"

    except Exception as e:
        return f"Error extracting text: {e}"

def get_resume_feedback(resume_text, position):
    prompt = f"Analyze the following resume for the position '{position}' and provide feedback for improvement:\n\n{resume_text} in two to three lines and also say does i fit for this job and what are the practical difficulties i might face all of this should be in few lines"

    try:
        response = ollama.chat(model="llama3.2:3b", messages=[{"role": "user", "content": prompt}])

        if isinstance(response, dict) and 'message' in response and 'content' in response['message']:
            return response['message']['content']
        else:
            return "Unexpected response format from Ollama."

    except Exception as e:
        return f"Error processing resume feedback: {e}"

@app.route('/create-resume')
def create_resume():
    if 'feedback' not in FEEDBACK_DATA or 'position' not in FEEDBACK_DATA:
        return "No feedback available. Please upload a resume first."

    feedback = FEEDBACK_DATA['feedback']
    position = FEEDBACK_DATA['position']

    prompt = f"Using this feedback: '{feedback}' and for the position: '{position}', generate a revised resume in markdown format."

    try:
        response = ollama.chat(model="llama3.2:3b", messages=[{"role": "user", "content": prompt}])

        if isinstance(response, dict) and 'message' in response and 'content' in response['message']:
            markdown_resume = response['message']['content']
            md_file = io.BytesIO(markdown_resume.encode('utf-8'))
            return send_file(md_file, download_name='revised_resume.md', as_attachment=True)

        else:
            return "Unexpected response format from Ollama."

    except Exception as e:
        return f"Error creating resume: {e}"

@app.route('/interview-prep')
def interview_prep():
    if 'position' not in FEEDBACK_DATA:
        return jsonify({"error": "Please upload a resume first."}), 400

    position = FEEDBACK_DATA['position']
    prompt = f"Provide interview preparation tips for a '{position}' role in markdown format."

    try:
        response = ollama.chat(model="llama3.2:3b", messages=[{"role": "user", "content": prompt}])
        if isinstance(response, dict) and 'message' in response and 'content' in response['message']:
            markdown_prep = response['message']['content']
            return jsonify({"prep": markdown_prep})
        else:
            return jsonify({"error": "Unexpected response format from Ollama."}), 500

    except Exception as e:
        return jsonify({"error": f"Error processing interview prep: {e}"}), 500

if __name__ == '__main__':
    app.run(debug=True)