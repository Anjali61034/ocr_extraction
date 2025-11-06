from flask import Flask, request, jsonify
import pytesseract, io, base64
from PIL import Image
import os

app = Flask(__name__)

@app.route("/")
def home():
    return jsonify({"status": "OCR Service Running"}), 200

@app.route("/extract", methods=["POST"])
def extract():
    try:
        data = request.get_json()
        image_b64 = data.get("imageBase64")
        doc_type = (data.get("docType") or "").lower()

        if not image_b64:
            return jsonify({"error": "No image provided"}), 400

        # decode and OCR
        image = Image.open(io.BytesIO(base64.b64decode(image_b64)))
        text = pytesseract.image_to_string(image)

        points = 4 if "cgpa" in text.lower() else 1
        return jsonify({"points": points, "text": text, "docType": doc_type}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
