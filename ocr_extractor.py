#!/usr/bin/env python3
import sys, json, re, pytesseract
from PIL import Image
from typing import Optional, Tuple

# ---------- Helper functions ----------
def normalize_text(img_text: str) -> str:
    t = img_text.replace("|", " ").replace(";", ":")
    t = t.replace("W", "II").replace("mM", "III").replace("Vv", "IV")
    t = t.replace("l", "I")
    return t

# ---------- Marksheets ----------
def extract_sgpa_cgpas(text: str):
    pattern = r'([1IVX]+)[\s\.\)\-:]*\s*\d+\s+\d+\s+([\d.]+)\s*([\d.]+)?\s*(PASSED|FAILED|Pass|Fail)?'
    matches = re.findall(pattern, text, flags=re.IGNORECASE)
    results = []
    for m in matches:
        sem_label = m[0].upper().replace("1", "I")
        try:
            sgpa = float(m[1])
        except:
            sgpa = None
        cgpa = None
        if m[2]:
            try:
                cgpa = float(m[2])
            except:
                cgpa = None
        result = m[3] if m[3] else None
        results.append((sem_label, sgpa, cgpa, result))
    cgpa_matches = re.findall(r'cgpa[:\s]*([\d.]+)', text, flags=re.IGNORECASE)
    final_cgpa = float(cgpa_matches[-1]) if cgpa_matches else None
    return results, final_cgpa

def cgpa_points(cgpa: float, stream: str) -> float:
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

# ---------- Certificates ----------
CATEGORY_KEYWORDS = {
    "Industry Experience": ["intern", "internship", "industrial", "industry", "placement", "training"],
    "National Cadet Corps": ["ncc", "national cadet", "cadet corps"],
    "Sports": ["sport", "tournament", "match", "football", "cricket", "athletics", "badminton"],
    "Outreach Activities": ["outreach", "community", "volunteer", "social service", "blood donation", "drive"],
    "Academic Engagement and Research": ["research", "paper", "presentation", "conference", "seminar", "workshop", "project"],
    "Extra-Curricular Activities": ["cultural", "dance", "music", "debate", "drama", "competition", "club", "talent"],
}
CATEGORY_ORDER = [
    "Industry Experience",
    "National Cadet Corps",
    "Sports",
    "Outreach Activities",
    "Academic Engagement and Research",
    "Extra-Curricular Activities",
]

def detect_certificate_type_rank_lead(event_text: str) -> Tuple[str, Optional[str], bool]:
    t = event_text.lower()
    t = re.sub(r"[^a-z0-9\s]", " ", t)
    t = re.sub(r"\s+", " ", t)

    # Detect leadership role
    is_lead = any(w in t for w in [
        "captain", "president", "organizer", "coordinator", "leadership", "head", "incharge"
    ])

    # Detect participation
    participation_words = ["participation", "participated", "participating",
                           "completed", "completion", "participate"]
    if any(w in t for w in participation_words):
        return "Participation", None, is_lead

    # Appreciation / Merit
    if any(w in t for w in ["appreciation", "appreciated"]):
        cert_type = "Appreciation"
    elif any(w in t for w in ["merit", "meritorious", "excellence", "outstanding"]):
        cert_type = "Merit"
    else:
        cert_type = "Other"

    # Detect rank
    rank = None
    if re.search(r'\b(1st|first|winner|gold)\b', t):
        rank = "1"
    elif re.search(r'\b(2nd|second|runner|silver)\b', t):
        rank = "2"
    elif re.search(r'\b(3rd|third|bronze)\b', t):
        rank = "3"
    else:
        m = re.search(r'(?:position|rank)[:\s]*([0-9]+|first|second|third|1st|2nd|3rd)', t)
        if m:
            val = m.group(1).lower()
            val = val.replace("first","1").replace("second","2").replace("third","3")
            val = val.replace("1st","1").replace("2nd","2").replace("3rd","3")
            if val.isdigit(): rank = val
    return cert_type, rank, is_lead

def detect_certificate_category(text: str) -> Optional[str]:
    low = text.lower()
    for cat in CATEGORY_ORDER:
        for kw in CATEGORY_KEYWORDS[cat]:
            if kw in low:
                return cat
    return None

def certificate_points_for_category(cert_type: str, rank: Optional[str], is_lead: bool, category: str, cert_text_low: str) -> float:
    if category == "Industry Experience":
        pts = 0
        if any(w in cert_text_low for w in ["international","abroad","overseas"]): pts += 2
        elif "national" in cert_text_low: pts += 1.5
        elif any(w in cert_text_low for w in ["university","college","local","state"]): pts += 1
        if is_lead: pts += 1
        return min(pts, 5)

    pts = 0
    if cert_type == "Participation": pts += 0.5
    else:
        if rank == "1": pts += 2
        elif rank == "2": pts += 1.5
        elif rank == "3": pts += 1
    if is_lead: pts += 1
    return min(pts, 5)

# ---------- Main ----------
if len(sys.argv) < 3:
    print(json.dumps({"error": "Usage: ocr_extractor.py <image_path> <doc_type>"}))
    sys.exit(1)

image_path = sys.argv[1]
doc_type = sys.argv[2].lower()
stream = "Sciences"

try:
    img = Image.open(image_path)
except FileNotFoundError:
    print(json.dumps({"error": f"File missing at runtime: {image_path}", "points": 0}))
    sys.exit(1)

text = pytesseract.image_to_string(img)
clean_text = normalize_text(text)

# ---------- Marksheets ----------
if doc_type == "marksheet":
    rows, final_cgpa_match = extract_sgpa_cgpas(clean_text)
    final_cgpa = final_cgpa_match or (next((r[2] for r in reversed(rows) if r[2]), None))
    points = cgpa_points(final_cgpa, stream)
    last_rows = rows[-4:]
    sgpas_with_sem = [f"{r[0]}: {r[1]}" for r in last_rows if r[1] is not None]

    result = {
        "type": "marksheet",
        "points": points,
        "cgpa": final_cgpa,
        "sgpas": sgpas_with_sem,
        "text": clean_text,
    }

# ---------- Certificates ----------
elif doc_type == "certificate":
    cert_type, rank, is_lead = detect_certificate_type_rank_lead(clean_text)
    category = detect_certificate_category(clean_text)
    if not category: category = "Extra-Curricular Activities"
    points = certificate_points_for_category(cert_type, rank, is_lead, category, clean_text.lower())

    result = {
        "type": "certificate",
        "points": points,
        "category": category,
        "cert_type": cert_type,
        "rank": rank,
        "is_lead": is_lead,
        "text": clean_text,
    }

else:
    result = {"error": "Unknown document type", "points": 0}

print(json.dumps(result))
