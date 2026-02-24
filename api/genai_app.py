import os
import json
import re
from typing import Optional, Dict, Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, HttpUrl
from groq import Groq
from dotenv import load_dotenv

# ======================
# ENV + CONFIG
# ======================
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-70b-versatile")
if not GROQ_API_KEY:
    raise RuntimeError("GROQ_API_KEY missing. Add it to .env")
groq_client = Groq(api_key=GROQ_API_KEY)

# ======================
# FASTAPI APP
# ======================
app = FastAPI(title="PhishGuard AI – GenAI + ML")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app = FastAPI(title="PhishGuard AI – GenAI + ML")
# ======================
# SERVE UI
# ======================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
app.mount(
    "/",
    StaticFiles(directory=STATIC_DIR, html=True),
    name="static"
)

# ======================
# SCHEMAS
# ======================
class ScanRequest(BaseModel):
    url: HttpUrl
    page_title: Optional[str] = None
    page_text_snippet: Optional[str] = None
    brand_claimed: Optional[str] = None
    user_context: Optional[str] = None


class ScanResponse(BaseModel):
    url: str
    verdict: str
    risk_score: float
    ml_score: float
    genai_score: float
    reasons: list[str]
    signals: Dict[str, Any]
    genai_summary: Dict[str, Any]


# ======================
# UTILS
# ======================
SUSPICIOUS_TLDS = {"xyz", "zip", "click", "top", "tk", "ml", "ga", "cf"}

def is_ip(host: str) -> bool:
    return bool(re.fullmatch(r"\d{1,3}(\.\d{1,3}){3}", host))


def get_url_features(url: str) -> Dict[str, Any]:
    ext = tldextract.extract(url)
    host = ext.fqdn

    return {
        "host": host,
        "url_length": len(url),
        "num_dots": host.count("."),
        "num_hyphens": host.count("-"),
        "has_https": url.startswith("https"),
        "looks_like_ip": is_ip(host),
        "suspicious_tld": ext.suffix in SUSPICIOUS_TLDS,
    }


def ml_score_calc(features: Dict[str, Any]) -> tuple[float, list[str]]:
    score = 0
    reasons = []

    if features["looks_like_ip"]:
        score += 20
        reasons.append("IP address used instead of domain")

    if features["suspicious_tld"]:
        score += 15
        reasons.append("Suspicious TLD detected")

    if features["url_length"] > 70:
        score += 10
        reasons.append("Unusually long URL")

    if features["num_hyphens"] >= 3:
        score += 10
        reasons.append("Too many hyphens in domain")

    if not features["has_https"]:
        score += 10
        reasons.append("HTTPS not used")

    return min(score, 100), reasons


GENAI_SYSTEM = """
You are a phishing detection expert.
Return ONLY valid JSON:

{
  "genai_score": number,
  "verdict": "SAFE" | "SUSPICIOUS" | "PHISHING",
  "top_reasons": [string],
  "notes": string
}
"""


def genai_analysis(req: ScanRequest, features: Dict[str, Any]) -> Dict[str, Any]:
    payload = {
        "url": str(req.url),
        "features": features,
        "title": req.page_title,
        "snippet": req.page_text_snippet,
        "brand": req.brand_claimed,
        "context": req.user_context,
    }

    res = groq_client.chat.completions.create(
        model=GROQ_MODEL,
        temperature=0.2,
        messages=[
            {"role": "system", "content": GENAI_SYSTEM},
            {"role": "user", "content": json.dumps(payload)},
        ],
    )

    return json.loads(res.choices[0].message.content)


# ======================
# ROUTES
# ======================
@app.get("/health")
def health():
    return {"status": "ok", "model": GROQ_MODEL}

@app.get("/")
def serve_ui():
    """Serve UI explicitly"""
    with open(os.path.join(STATIC_DIR, "index.html"), encoding="utf-8") as f:
        return f.read()

@app.post("/scan", response_model=ScanResponse)
def scan(req: ScanRequest):
    features = get_url_features(str(req.url))
    ml_score, ml_reasons = ml_score_calc(features)
    genai = genai_analysis(req, features)
    genai_score = genai.get("genai_score", 50)

    final_score = 0.45 * ml_score + 0.55 * genai_score

    if final_score >= 75:
        verdict = "PHISHING"
    elif final_score >= 45:
        verdict = "SUSPICIOUS"
    else:
        verdict = "SAFE"

    reasons = ml_reasons + genai.get("top_reasons", [])

    return ScanResponse(
        url=str(req.url),
        verdict=verdict,
        risk_score=round(final_score, 2),
        ml_score=ml_score,
        genai_score=genai_score,
        reasons=reasons[:6],
        signals={"features": features},
        genai_summary=genai,
    )
