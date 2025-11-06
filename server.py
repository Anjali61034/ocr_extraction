from flask import Flask, request, jsonify
import pytesseract, io, base64, re, os
from PIL import Image

# ✅ Ensure Tesseract OCR is installed (important for Railway/Render)
if not os.path.exists("/usr/bin/tesseract"):
    os.system("apt-get update && apt-get install -y tesseract-ocr")

app = Flask(__name__)

# ---------------------- HELPERS ----------------------

def normalize_text(img_text: str) -> str:
    t = img_text.replace("|", " ").replace(";", ":")
    t = t.replace("W", "II").replace("mM", "III").replace("Vv", "IV")
    t = t.replace("l", "I")
    return t

def extract_sgpa_cgpas(text: str):
    pattern = r'([1IVX]+)[\s\.\)\-:]*\s*\d+\s+\d+\s+([\d.]+)\s*([\d.]+)?\s*(PASSED|FAILED|Pass|Fail)?'
    matches = re.findall(pattern, text, flags=re.IGNORECASE)
    results = []
    for m in matches:
        sem_label = m[0].upper().replace("1", "I")
        sgpa = None
        cgpa = None
        try:
            sgpa = float(m[1])
        except:
            pass
        if m[2]:
            try:
                cgpa = float(m[2])
            except:
                pass
        results.append((sem_label, sgpa, cgpa, m[3] if m[3] else None))

    cgpa_matches = re.findall(r'cgpa[:\s]*([\d.]+)', text, flags=re.IGNORECASE)
    final_cgpa = float(cgpa_matches[-1]) if cgpa_matches else None
    return results, final_cgpa

def cgpa_points(cgpa: float, stream="Sciences") -> float:
    if cgpa is None:
        return 0.0
    if stream.lower() == "humanities":
        if cgpa >= 8: return 5
        if cgpa >= 7: return 4
        if cgpa >= 6: return 3
    else:
        if cgpa >= 9: return 5
        if cgpa >= 8: return 4
        if cgpa >= 7: return 3
        if cgpa >= 6: return 2
    return 0.0

# --- Certificate Logic ---

CATEGORY_KEYWORDS = {
    "Industry Experience": ["intern", "internship", "industrial", "industry", "placement", "training"],
    "National Cadet Corps": ["ncc", "national cadet", "cadet corps"],
    "Sports": ["sport", "tournament", "match", "football", "cricket", "athletics", "badminton"],
    "Outreach Activities": ["outreach", "community", "volunteer", "social service", "blood donation", "drive"],
    "Academic Engagement and Research": ["research", "paper", "presentation", "conference", "seminar", "workshop", "project"],
    "Extra-Curricular Activities": ["cultural", "dance", "music", "debate", "drama", "competition", "club", "talent"],
}

CATEGORY_ORDER = list(CATEGORY_KEYWORDS.keys())

def detect_certificate_category(text: str):
    low = text.lower()
    for cat in CATEGORY_ORDER:
        for kw in CATEGORY_KEYWORDS[cat]:
            if kw in low:
                return cat
    return "Extra-Curricular Activities"

def detect_certificate_type_rank_lead(text: str):
    t = text.lower()
    is_lead = any(w in t for w in ["captain", "president", "organizer", "coordinator", "head", "incharge"])
    rank = None
    if re.search(r'\b(1st|first|winner|gold)\b', t): rank = "1"
    elif re.search(r'\b(2nd|second|runner|silver)\b', t): rank = "2"
    elif re.search(r'\b(3rd|third|bronze)\b', t): rank = "3"
    return rank, is_lead

def certificate_points_for_category(rank, is_lead, category, cert_type="Participation"):
    pts = 0.5
    if rank == "1": pts += 2
    elif rank == "2": pts += 1.5
    elif rank == "3": pts += 1
    if is_lead: pts += 1
    if category == "Industry Experience": pts += 1
    return min(pts, 5)

# ---------------------- ROUTES ----------------------

@app.route("/")
def home():
    return jsonify({"status": "OCR Service Running"}), 200

@app.route("/extract", methods=["POST"])
def extract():
    try:
        data = request.get_json()
        image_b64 = data.get("imageBase64")
        doc_type = (data.get("docType") or "").lower()
        stream = data.get("stream", "Sciences")

        if not image_b64:
            return jsonify({"error": "No image provided"}), 400

        # Decode image
        image = Image.open(io.BytesIO(base64.b64decode(image_b64)))
        text = pytesseract.image_to_string(image)
        clean_text = normalize_text(text)

        # ---------------------- MARKSHEET ----------------------
        if doc_type == "marksheet":
            rows, final_cgpa_match = extract_sgpa_cgpas(clean_text)
            final_cgpa = final_cgpa_match or (next((r[2] for r in reversed(rows) if r[2]), None))
            points = cgpa_points(final_cgpa, stream)
            sgpas_with_sem = [f"{r[0]}: {r[1]}" for r in rows[-4:] if r[1] is not None]

            return jsonify({
                "type": "marksheet",
                "points": points,
                "cgpa": final_cgpa,
                "sgpas": sgpas_with_sem,
                "text": clean_text
            })

        # ---------------------- CERTIFICATE ----------------------
        elif doc_type == "certificate":
            category = detect_certificate_category(clean_text)
            rank, is_lead = detect_certificate_type_rank_lead(clean_text)
            points = certificate_points_for_category(rank, is_lead, category)

            return jsonify({
                "type": "certificate",
                "points": points,
                "category": category,
                "rank": rank,
                "is_lead": is_lead,
                "text": clean_text
            })

        else:
            return jsonify({"error": "Unknown document type"}), 400

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ---------------------- RUN ----------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

