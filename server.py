from flask import Flask, request, jsonify
import pytesseract, re
from PIL import Image
import io, base64

app = Flask(__name__)

@app.route("/extract", methods=["POST"])
def extract():
    data = request.get_json()
    image_b64 = data.get("imageBase64")
    doc_type = data.get("docType", "").lower()

    image = Image.open(io.BytesIO(base64.b64decode(image_b64)))
    text = pytesseract.image_to_string(image)

    # ✅ basic example — replace with your logic
    if "cgpa" in text.lower():
        points = 4
    else:
        points = 1

    return jsonify({"points": points, "text": text})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
