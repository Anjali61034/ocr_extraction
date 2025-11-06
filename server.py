from flask import Flask, request, jsonify
import pytesseract, re, io, base64, os
from PIL import Image

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

        image = Image.open(io.BytesIO(base64.b64decode(image_b64)))
        text = pytesseract.image_to_string(image)

        # Simple scoring logic (you can expand this)
        if "cgpa" in text.lower():
            points = 4
        else:
            points = 1

        return jsonify({"points": points, "text": text, "docType": doc_type}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 8080))  # Railway sets PORT env variable
    app.run(host="0.0.0.0", port=port)

