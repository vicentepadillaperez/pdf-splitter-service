from flask import Flask, request, jsonify, send_file
import os
import tempfile
from PyPDF2 import PdfReader, PdfWriter
import base64
from io import BytesIO

app = Flask(__name__)

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({"status": "healthy", "service": "pdf-splitter"}), 200

@app.route('/split', methods=['POST'])
def split_pdf():
    """
    Split a PDF into individual pages.
    
    Expects JSON:
    {
        "pdf": "base64-encoded-pdf-content",
        "filename": "original-filename.pdf"
    }
    
    Returns JSON:
    {
        "success": true,
        "total_pages": 3,
        "pages": [
            {"page": 1, "data": "base64-page-1"},
            {"page": 2, "data": "base64-page-2"},
            {"page": 3, "data": "base64-page-3"}
        ]
    }
    """
    try:
        # Get request data
        data = request.get_json()
        
        if not data or 'pdf' not in data:
            return jsonify({"error": "Missing 'pdf' in request body"}), 400
        
        pdf_base64 = data['pdf']
        filename = data.get('filename', 'document.pdf')
        
        # Decode base64 PDF
        try:
            pdf_bytes = base64.b64decode(pdf_base64)
        except Exception as e:
            return jsonify({"error": f"Invalid base64: {str(e)}"}), 400
        
        # Read PDF
        pdf_file = BytesIO(pdf_bytes)
        reader = PdfReader(pdf_file)
        total_pages = len(reader.pages)
        
        # Split into individual pages
        pages_data = []
        
        for page_num in range(total_pages):
            # Create a new PDF with just this page
            writer = PdfWriter()
            writer.add_page(reader.pages[page_num])
            
            # Write to BytesIO
            output = BytesIO()
            writer.write(output)
            output.seek(0)
            
            # Encode to base64
            page_base64 = base64.b64encode(output.read()).decode('utf-8')
            
            pages_data.append({
                "page": page_num + 1,
                "data": page_base64,
                "filename": f"page_{page_num + 1}.pdf"
            })
        
        return jsonify({
            "success": True,
            "total_pages": total_pages,
            "original_filename": filename,
            "pages": pages_data
        }), 200
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/split-binary', methods=['POST'])
def split_pdf_binary():
    """
    Alternative endpoint that accepts binary PDF directly.
    Returns first page as binary (for simple use cases).
    """
    try:
        if 'file' not in request.files:
            return jsonify({"error": "No file provided"}), 400
        
        pdf_file = request.files['file']
        
        # Read PDF
        reader = PdfReader(pdf_file)
        total_pages = len(reader.pages)
        
        # Get page number from query param (default: 1)
        page_num = int(request.args.get('page', 1))
        
        if page_num < 1 or page_num > total_pages:
            return jsonify({"error": f"Page {page_num} out of range (1-{total_pages})"}), 400
        
        # Extract requested page
        writer = PdfWriter()
        writer.add_page(reader.pages[page_num - 1])
        
        # Write to BytesIO
        output = BytesIO()
        writer.write(output)
        output.seek(0)
        
        return send_file(
            output,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'page_{page_num}.pdf'
        )
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8000))
    app.run(host='0.0.0.0', port=port, debug=False)
