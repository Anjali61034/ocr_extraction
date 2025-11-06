from flask import Flask, request, jsonify
import pytesseract, io, base64, re, os
from PIL import Image

# ✅ Auto-install tesseract if missing (Railway safe)
if not os.path.exists("/usr/bin/tesseract"):
    os.system("apt-get update && apt-get install -y tesseract-ocr")

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

        # ✅ Decode and extract text
        image = Image.open(io.BytesIO(base64.b64decode(image_b64)))
        text = pytesseract.image_to_string(image)

        # Normalize text for regex
        clean_text = text.replace("|", " ").replace(";", ":").replace("l", "I")

        # ---------- MARKSHEET LOGIC ----------
        def extract_sgpa_cgpas(text):
            pattern = r'([1IVX]+)[\s\.\)\-:]*\s*\d+\s+\d+\s+([\d.]+)\s*([\d.]+)?\s*(PASSED|FAILED|Pass|Fail)?'
            matches = re.findall(pattern, text, flags=re.IGNORECASE)
            results = []
            for m in matches:
                sem_label = m[0].upper().replace("1", "I")
                sgpa = float(m[1]) if m[1] else None
                cgpa = float(m[2]) if m[2] else None
                results.append((sem_label, sgpa, cgpa))
            cgpa_matches = re.findall(r'cgpa[:\s]*([\d.]+)', text, flags=re.IGNORECASE)
            final_cgpa = float(cgpa_matches[-1]) if cgpa_matches else None
            return results, final_cgpa

        def cgpa_points(cgpa):
            if not cgpa:
                return 0
            if cgpa >= 9: return 5
            if cgpa >= 8: return 4
            if cgpa >= 7: return 3
            if cgpa >= 6: return 2
            return 1

        # ---------- CERTIFICATE LOGIC ----------
        CATEGORY_KEYWORDS = {
            "Industry Experience": ["intern", "training", "placement", "industrial"],
            "Sports": ["sport", "match", "tournament", "athletics", "cricket", "football"],
            "Outreach Activities": ["outreach", "community", "volunteer", "donation", "drive"],
            "Academic Engagement": ["research", "seminar", "paper", "presentation", "conference"],
            "Extra-Curricular": ["cultural", "dance", "music", "debate", "competition", "club"],
        }

        def detect_category(text):
            t = text.lower()
            for category, words in CATEGORY_KEYWORDS.items():
                for w in words:
                    if w in t:
                        return category
            return "Extra-Curricular"

        def detect_rank_leadership(text):
            t = text.lower()
            is_lead = any(x in t for x in ["captain", "president", "organizer", "head", "leader"])
            rank = None
            if re.search(r'\b(1st|first|winner|gold)\b', t): rank = "1"
            elif re.search(r'\b(2nd|second|silver|runner)\b', t): rank = "2"
            elif re.search(r'\b(3rd|third|bronze)\b', t): rank = "3"
            return rank, is_lead

        def certificate_points(rank, is_lead, category):
            pts = 0
            if rank == "1": pts += 2
            elif rank == "2": pts += 1.5
            elif rank == "3": pts += 1
            if is_lead: pts += 1
            if category == "Industry Experience": pts += 1.5
            return min(5, pts)

        # ---------- DETECTION ----------
        if doc_type == "marksheet":
            sgpas, final_cgpa = extract_sgpa_cgpas(clean_text)
            points = cgpa_points(final_cgpa)
            result = {
                "docType": "marksheet",
                "points": points,
                "cgpa": final_cgpa,
                "sgpas": sgpas,
                "text": clean_text
            }

        elif doc_type == "certificate":
            category = detect_category(clean_text)
            rank, is_lead = detect_rank_leadership(clean_text)
            points = certificate_points(rank, is_lead, category)
            result = {
                "docType": "certificate",
                "points": points,
                "category": category,
                "rank": rank,
                "is_lead": is_lead,
                "text": clean_text
            }

        else:
            result = {"error": "Unknown document type", "points": 0}

        return jsonify(result), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
