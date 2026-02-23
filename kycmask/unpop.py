import streamlit as st
import cv2
import numpy as np
import io
import os
import re
import fitz  # PyMuPDF for PDF processing
from google.cloud import vision
from PyPDF2 import PdfReader, PdfWriter
import img2pdf
from PIL import Image
from streamlit_image_comparison import image_comparison
import time
from google.oauth2 import service_account

# Set page config as the first Streamlit command
st.set_page_config(layout="wide", page_title="Privacy Shield", page_icon="🛡️")

# Custom CSS for a modern design
st.markdown("""
<style>
    .main {
        background-color: #f0f2f6;
        font-family: 'Roboto', sans-serif;
        color: #333333;
    }
    .stApp {
        max-width: 1200px;
        margin: 0 auto;
    }
    h1, h2, h3 {
        color: #1e3a8a;
    }
    p, li, .stMarkdown {
        color: #333333;
    }
    .stButton>button {
        background-color: #3b82f6;
        color: white !important;  /* Ensure white font color */
        border-radius: 8px;
        padding: 0.5rem 1rem;
        font-weight: bold;
        transition: all 0.3s;
    }
    .stButton>button:hover {
        background-color: #2563eb;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1),
                    0 2px 4px -1px rgba(0, 0, 0, 0.06);
    }
    .upload-area {
        padding: 2rem;
        text-align: center;
        margin-bottom: 1rem;
    }
    .info-box {
        background-color: #e0f2fe;
        border-left: 5px solid #3b82f6;
        padding: 1rem;
        margin-bottom: 1rem;
        border-radius: 0 8px 8px 0;
        color: #1e3a8a;
    }
    .footer {
        text-align: center;
        margin-top: 2rem;
        color: #6b7280;
        font-size: 0.875rem;
    }
    /* Additional styles to ensure text visibility */
    .stTextInput>div>div>input {
        color: #333333;
    }
    .stSelectbox>div>div>div {
        color: #333333;
    }
    /* Style for all download buttons */
    .stDownloadButton > button {
        color: #ffffff !important;  /* White text */
        background-color: #3b82f6 !important;
        border-radius: 8px !important;
        padding: 0.5rem 1rem !important;
        font-weight: bold !important;
        transition: all 0.3s;
    }
    .stDownloadButton > button:hover {
        background-color: #2563eb !important;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1),
                    0 2px 4px -1px rgba(0, 0, 0, 0.06);
    }
    /* Remove all focus indicators from the file uploader */
    .stFileUploader > div > div > button:focus {
        outline: none !important;
        box-shadow: none !important;
        border-color: inherit !important;
    }
</style>
""", unsafe_allow_html=True)

# Function to extract text using Google Cloud Vision API
def extract_text(image_content):
    # Use Streamlit secrets to get the credentials
    credentials = service_account.Credentials.from_service_account_info(
        st.secrets["gcp_service_account"]
    )
    client = vision.ImageAnnotatorClient(credentials=credentials)
    if isinstance(image_content, bytes):
        image = vision.Image(content=image_content)
    else:
        # Convert PIL Image to bytes
        with io.BytesIO() as output:
            image_content.save(output, format='JPEG')
            image_bytes = output.getvalue()
        image = vision.Image(content=image_bytes)
    response = client.document_text_detection(image=image)
    if response.error.message:
        raise Exception(f'Vision API Error: {response.error.message}')
    text = response.full_text_annotation.text
    return text, response

# Function to detect sensitive information
def detect_sensitive_info(text):
    pan_pattern = r'\b[A-Z]{5}[0-9]{4}[A-Z]\b'
    aadhaar_pattern = r'\b[0-9]{4}\s?[0-9]{4}\s?[0-9]{4}\b'

    pan_numbers = re.findall(pan_pattern, text)
    aadhaar_numbers = re.findall(aadhaar_pattern, text)

    return pan_numbers, aadhaar_numbers

# Function to mask sensitive information in the image
def mask_text_in_image(image_content, response, pan_numbers, aadhaar_numbers):
    if isinstance(image_content, bytes):
        nparr = np.frombuffer(image_content, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    else:
        # Convert PIL Image to OpenCV format
        image = cv2.cvtColor(np.array(image_content), cv2.COLOR_RGB2BGR)

    words_with_boxes = []
    for page in response.full_text_annotation.pages:
        for block in page.blocks:
            for paragraph in block.paragraphs:
                for word in paragraph.words:
                    word_text = ''.join([symbol.text for symbol in word.symbols])
                    vertices = [(vertex.x, vertex.y) for vertex in word.bounding_box.vertices]
                    words_with_boxes.append({'text': word_text, 'vertices': vertices})

    num_words = len(words_with_boxes)
    for i in range(num_words):
        for j in range(i + 1, min(i + 5, num_words + 1)):
            sequence_text = ''.join([w['text'] for w in words_with_boxes[i:j]])
            sequence_text_clean = ''.join(filter(str.isalnum, sequence_text))

            for pan in pan_numbers:
                if pan == sequence_text_clean:
                    x_min = min([min(v[0] for v in w['vertices']) for w in words_with_boxes[i:j]])
                    y_min = min([min(v[1] for v in w['vertices']) for w in words_with_boxes[i:j]])
                    x_max = max([max(v[0] for v in w['vertices']) for w in words_with_boxes[i:j]])
                    y_max = max([max(v[1] for v in w['vertices']) for w in words_with_boxes[i:j]])
                    cv2.rectangle(image, (int(x_min), int(y_min)), (int(x_max), int(y_max)), (255, 255, 255), -1)

                    masked_text = 'XXXXX' + pan[-4:]
                    text_size = cv2.getTextSize(masked_text, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)[0]
                    text_x = int(x_min + (x_max - x_min - text_size[0]) // 2)
                    text_y = int(y_min + (y_max - y_min + text_size[1]) // 2)
                    cv2.putText(image, masked_text, (text_x, text_y),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
                    break

            for aadhaar in aadhaar_numbers:
                aadhaar_clean = ''.join(filter(str.isdigit, aadhaar))
                if aadhaar_clean == sequence_text_clean:
                    x_min = min([min(v[0] for v in w['vertices']) for w in words_with_boxes[i:j]])
                    y_min = min([min(v[1] for v in w['vertices']) for w in words_with_boxes[i:j]])
                    x_max = max([max(v[0] for v in w['vertices']) for w in words_with_boxes[i:j]])
                    y_max = max([max(v[1] for v in w['vertices']) for w in words_with_boxes[i:j]])
                    cv2.rectangle(image, (int(x_min), int(y_min)), (int(x_max), int(y_max)),
                                  (255, 255, 255), -1)

                    masked_text = 'XXXX XXXX ' + aadhaar_clean[-4:]
                    text_size = cv2.getTextSize(masked_text, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)[0]
                    text_x = int(x_min + (x_max - x_min - text_size[0]) // 2)
                    text_y = int(y_min + (y_max - y_min + text_size[1]) // 2)
                    cv2.putText(image, masked_text, (text_x, text_y),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
                    break

    # Return masked image bytes
    retval, buffer = cv2.imencode('.jpg', image)
    return buffer.tobytes()

# Main content
st.title("🛡️ MaskMate Privacy Shield")
st.markdown("<p class='info-box'>Protect your sensitive information with ease.</p>", unsafe_allow_html=True)

col1, col2 = st.columns([2, 1])

with col1:
    uploaded_files = st.file_uploader(
        "Drop your files here or click to browse",
        type=["jpg", "jpeg", "png", "pdf"],
        accept_multiple_files=True)

with col2:
    st.markdown("### How it works")
    st.markdown("1. Upload images or PDFs")
    st.markdown("2. We detect and mask sensitive KYC related info")
    st.markdown("3. Download protected versions")

if uploaded_files:
    st.success(f"{len(uploaded_files)} file(s) uploaded successfully!")

    for idx, uploaded_file in enumerate(uploaded_files):
        st.markdown(f"## File {idx + 1}: {uploaded_file.name}")
        filename = uploaded_file.name
        file_extension = filename.split('.')[-1].lower()

        if file_extension in ['jpg', 'jpeg', 'png']:
            # Process as image
            image_bytes = uploaded_file.read()

            with st.spinner("Shielding your information..."):
                progress_bar = st.progress(0)
                for i in range(100):
                    time.sleep(0.005)
                    progress_bar.progress(i + 1)

                text, response = extract_text(image_bytes)
                pan_numbers, aadhaar_numbers = detect_sensitive_info(text)
                masked_image_bytes = mask_text_in_image(
                    image_bytes, response, pan_numbers, aadhaar_numbers)

            # Use image comparison slider
            st.markdown("### Original vs Protected Image")
            image_comparison(
                img1=Image.open(io.BytesIO(image_bytes)),
                img2=Image.open(io.BytesIO(masked_image_bytes)),
                label1="Original",
                label2="Protected",
                width=700,
            )

            # Display detected sensitive information
            if pan_numbers or aadhaar_numbers:
                st.markdown('<div class="sensitive-info">', unsafe_allow_html=True)
                st.markdown('<h3 style="color: #d32f2f;">🚨 Sensitive Information Detected</h3>',
                            unsafe_allow_html=True)
                col1, col2 = st.columns(2)
                with col1:
                    if pan_numbers:
                        st.markdown('<p style="color: #d32f2f;"><strong>PAN Numbers:</strong></p>',
                                    unsafe_allow_html=True)
                        for pan in pan_numbers:
                            st.markdown(f'<span class="sensitive-item">{pan[:2]}XXXXX{pan[-3:]}</span>',
                                        unsafe_allow_html=True)
                with col2:
                    if aadhaar_numbers:
                        st.markdown('<p style="color: #d32f2f;"><strong>Aadhaar Numbers:</strong></p>',
                                    unsafe_allow_html=True)
                        for aadhaar in aadhaar_numbers:
                            st.markdown(f'<span class="sensitive-item">XXXX XXXX {aadhaar[-4:]}</span>',
                                        unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)
            else:
                st.info("No PAN or Aadhaar numbers detected.")

            # Download options with improved buttons
            col1, col2 = st.columns(2)
            with col1:
                st.download_button(
                    label="⬇️ Download Masked Image",
                    data=masked_image_bytes,
                    file_name=f"protected_{filename}",
                    mime="image/jpeg",
                    key=f"download_masked_image_{idx}"
                )
            with col2:
                # Create password-protected PDF for original image
                with io.BytesIO() as f:
                    f.write(img2pdf.convert(image_bytes))
                    reader = PdfReader(f)
                    writer = PdfWriter()
                    writer.append_pages_from_reader(reader)
                    writer.encrypt('test123')
                    with io.BytesIO() as pdf_output:
                        writer.write(pdf_output)
                        protected_pdf_bytes = pdf_output.getvalue()
                st.download_button(
                    label="⬇️ Download Secure Original PDF",
                    data=protected_pdf_bytes,
                    file_name=f"original_protected_{filename}.pdf",
                    mime="application/pdf",
                    key=f"download_secure_pdf_{idx}"
                )

        elif file_extension == 'pdf':
            # Process as PDF using PyMuPDF
            pdf_bytes = uploaded_file.read()
            with st.spinner("Shielding your information..."):
                with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
                    num_pages = len(doc)
                    if num_pages > 2:
                        st.error("PAN and Aadhaar not detected. Please recheck your document.")
                        continue  # Skip processing this file
                    images = []
                    for page_num in range(len(doc)):
                        page = doc[page_num]
                        pix = page.get_pixmap()
                        img_data = pix.tobytes()
                        img = Image.open(io.BytesIO(img_data))
                        images.append(img)

                # Process each image
                masked_images = []
                all_pan_numbers = set()
                all_aadhaar_numbers = set()
                progress_bar = st.progress(0)
                for i, pil_image in enumerate(images):
                    text, response = extract_text(pil_image)
                    pan_numbers, aadhaar_numbers = detect_sensitive_info(text)
                    all_pan_numbers.update(pan_numbers)
                    all_aadhaar_numbers.update(aadhaar_numbers)
                    masked_image_bytes = mask_text_in_image(
                        pil_image, response, pan_numbers, aadhaar_numbers)
                    masked_image = Image.open(io.BytesIO(masked_image_bytes))
                    masked_images.append(masked_image)
                    progress_bar.progress((i + 1) / len(images))
                progress_bar.empty()

                # Display the images
                st.markdown("### Original vs Protected Document")
                image_comparison(
                    img1=images[0],
                    img2=masked_images[0],
                    label1="Original",
                    label2="Protected",
                    width=700,
                )

                # Provide download buttons
                col1, col2 = st.columns(2)
                with col1:
                    # Save masked images to PDF
                    with io.BytesIO() as pdf_output:
                        masked_images[0].save(pdf_output, format='PDF',
                                              save_all=True, append_images=masked_images[1:])
                        masked_pdf_bytes = pdf_output.getvalue()
                    st.download_button(
                        "⬇️ Download Masked PDF",
                        data=masked_pdf_bytes,
                        file_name=f"protected_{filename}",
                        mime="application/pdf",
                        key=f"download_masked_pdf_{idx}"
                    )
                with col2:
                    # Create password-protected PDF for original document
                    reader = PdfReader(io.BytesIO(pdf_bytes))
                    writer = PdfWriter()
                    writer.append_pages_from_reader(reader)
                    writer.encrypt('test123')
                    with io.BytesIO() as protected_pdf_output:
                        writer.write(protected_pdf_output)
                        protected_pdf_bytes = protected_pdf_output.getvalue()
                    st.download_button(
                        "⬇️ Download Secure Original PDF",
                        data=protected_pdf_bytes,
                        file_name=f"original_protected_{filename}",
                        mime="application/pdf",
                        key=f"download_protected_pdf_{idx}"
                    )

                # Display detected sensitive information
                if all_pan_numbers or all_aadhaar_numbers:
                    st.markdown('<div class="sensitive-info">', unsafe_allow_html=True)
                    st.markdown('<h3 style="color: #d32f2f;">🚨 Sensitive Information Detected</h3>',
                                unsafe_allow_html=True)
                    col1, col2 = st.columns(2)
                    with col1:
                        if all_pan_numbers:
                            st.markdown('<p style="color: #d32f2f;"><strong>PAN Numbers:</strong></p>',
                                        unsafe_allow_html=True)
                            for pan in all_pan_numbers:
                                st.markdown(f'<span class="sensitive-item">{pan[:2]}XXXXX{pan[-3:]}</span>',
                                            unsafe_allow_html=True)
                    with col2:
                        if all_aadhaar_numbers:
                            st.markdown('<p style="color: #d32f2f;"><strong>Aadhaar Numbers:</strong></p>',
                                        unsafe_allow_html=True)
                            for aadhaar in all_aadhaar_numbers:
                                st.markdown(f'<span class="sensitive-item">XXXX XXXX {aadhaar[-4:]}</span>',
                                            unsafe_allow_html=True)
                    st.markdown('</div>', unsafe_allow_html=True)
                else:
                    st.info("No PAN or Aadhaar numbers detected.")
        else:
            st.error(f"Unsupported file type: {file_extension}")

# Footer
st.markdown("<div class='footer'>Made with ❤️<br>© Amlan 2024 All rights reserved</div>",
            unsafe_allow_html=True)
