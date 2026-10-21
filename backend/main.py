from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional
import os, random, httpx, re
from dotenv import load_dotenv

try:
    from speeches import SPEECHES, normalize_tod, sanitize_speech, validate_tod_speech, MICRO
except ImportError:
    from backend.speeches import SPEECHES, normalize_tod, sanitize_speech, validate_tod_speech, MICRO

load_dotenv()

app = FastAPI(title="Motivate API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class MotivateRequest(BaseModel):
    name: str
    tone: str
    mood: str
    reason: Optional[str] = None
    time_of_day: Optional[str] = None
    streak: int = 1

TONE_LABELS = {
    "support": "бережная поддержка",
    "push": "дружеский пинок",
    "zen": "стоический дзен",
    "humor": "лёгкий юмор",
}
MOOD_LABELS = {
    "charged": "заряжен на 100%",
    "drained": "батарейка на нуле",
}
TOD_PHRASE = {
    "утро": "утром",
    "день": "днём",
    "вечер": "вечером",
    "ночь": "ночью",
}

def build_mock(req: MotivateRequest):
    tod = normalize_tod(req.time_of_day)
    reason = req.reason or "Просто так"
    tone_dict = SPEECHES.get(req.tone, SPEECHES["support"])
    mood_dict = tone_dict.get(req.mood, tone_dict["charged"])
    tod_dict = mood_dict.get(tod, mood_dict.get("утро", {}))
    pool = tod_dict.get(reason, tod_dict.get("Просто так", []))
    if not pool:
        pool = list(tod_dict.values())[0] if tod_dict else ["{name}, всё получится!"]
    
    raw_text = random.choice(pool)
    user_name = req.name.strip() if req.name and req.name.strip() else "Друг"
    text = raw_text.replace("{name}", user_name)
    text = sanitize_speech(text)
    if len(text) > 320:
        text = text[:317] + "..."
    micro = random.choice(MICRO.get(req.mood, MICRO["drained"]))
    return {"text": text, "micro_action": micro}

async def try_llm(req: MotivateRequest, tod: str):
    tod_str = TOD_PHRASE.get(tod, tod)
    user_name = req.name.strip() if req.name and req.name.strip() else "Друг"
    prompt = (
        f"Ты мотиватор. Пиши 3-4 коротких предложения на русском языке без клише. "
        f"Имя: {user_name}, Тон: {TONE_LABELS.get(req.tone, req.tone)}, "
        f"Настроение: {MOOD_LABELS.get(req.mood, req.mood)}, Причина: {req.reason or 'не указана'}, "
        f"Время суток СТРОГО: {tod_str}. "
        f"ВАЖНО: говори ТОЛЬКО про {tod_str}, ни слова про другое время суток. "
        f"Никаких скобок рода вроде сделал(-а)."
    )

    # Gemini
    gk = os.getenv("GEMINI_API_KEY")
    if gk:
        try:
            async with httpx.AsyncClient(timeout=3.5) as client:
                r = await client.post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={gk}",
                    json={"contents": [{"parts": [{"text": prompt}]}]}
                )
                if r.status_code == 200:
                    t = r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
                    t = sanitize_speech(t)
                    if 30 <= len(t) <= 350 and validate_tod_speech(t, tod) and re.fullmatch(r"[\w\s.,!?…—–-ёЁа-яА-Яa-zA-Z]+", t):
                        return t
        except Exception:
            pass

    # Groq
    qk = os.getenv("GROQ_API_KEY")
    if qk:
        try:
            async with httpx.AsyncClient(timeout=3.5) as client:
                r = await client.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {qk}"},
                    json={
                        "model": "llama-3.1-8b-instant",
                        "messages": [
                            {"role": "system", "content": "Ты эмпатичный мотиватор. Пиши строго на русском без клише и без скобок рода."},
                            {"role": "user", "content": prompt}
                        ],
                        "max_tokens": 200
                    }
                )
                if r.status_code == 200:
                    t = r.json()["choices"][0]["message"]["content"].strip()
                    t = sanitize_speech(t)
                    if 30 <= len(t) <= 350 and validate_tod_speech(t, tod) and re.fullmatch(r"[\w\s.,!?…—–-ёЁа-яА-Яa-zA-Z]+", t):
                        return t
        except Exception:
            pass

    return None

@app.post("/api/motivate")
async def motivate(req: MotivateRequest):
    tod = normalize_tod(req.time_of_day)
    tod_str = TOD_PHRASE.get(tod, tod)
    user_name = req.name.strip() if req.name and req.name.strip() else "Друг"

    # Pollinations
    system = (
        "Ты эмпатичный мотиватор. Отвечай ТОЛЬКО на русском языке. 3-4 коротких естественных предложения без клише. "
        f"Имя: {user_name}. Тон: {TONE_LABELS.get(req.tone, req.tone)}. "
        f"Настроение: {MOOD_LABELS.get(req.mood, req.mood)}. Причина: {req.reason or 'не указана'}. "
        f"Время суток СТРОГО: {tod_str}. Никаких других времен суток! Категорически запрещены скобки рода вроде сделал(-а)."
    )
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            r = await client.post(
                "https://text.pollinations.ai/",
                json={"messages": [{"role": "system", "content": system}, {"role": "user", "content": "Сгенерируй персональную мотивацию."}], "model": "openai"}
            )
            if r.status_code == 200:
                text = sanitize_speech(r.text.strip())
                if 30 <= len(text) <= 350 and validate_tod_speech(text, tod) and re.fullmatch(r"[\w\s.,!?…—–-ёЁа-яА-Яa-zA-Z]+", text):
                    micro = random.choice(MICRO.get(req.mood, MICRO["drained"]))
                    if len(text) > 320:
                        text = text[:317] + "..."
                    return {"text": text, "micro_action": micro}
    except Exception:
        pass

    # Gemini / Groq fallback
    t = await try_llm(req, tod)
    if t:
        micro = random.choice(MICRO.get(req.mood, MICRO["drained"]))
        if len(t) > 320:
            t = t[:317] + "..."
        return {"text": t, "micro_action": micro}

    # Curated mock dictionary (strictly matching TOD, tone, mood, reason)
    return build_mock(req)

# Static & PWA Routes
base_dir = os.path.dirname(os.path.abspath(__file__))
static_dir = os.path.join(base_dir, "static")

app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/")
async def root():
    return FileResponse(os.path.join(static_dir, "index.html"))

@app.get("/manifest.json")
async def manifest():
    return FileResponse(
        os.path.join(static_dir, "manifest.json"),
        media_type="application/manifest+json",
        headers={"Cache-Control": "no-cache"}
    )

@app.get("/sw.js")
async def sw():
    return FileResponse(
        os.path.join(static_dir, "sw.js"),
        media_type="application/javascript",
        headers={"Service-Worker-Allowed": "/", "Cache-Control": "no-cache"}
    )

@app.get("/apple-touch-icon.png")
@app.get("/apple-touch-icon-precomposed.png")
async def apple_touch_icon():
    return FileResponse(os.path.join(static_dir, "apple-touch-icon.png"), media_type="image/png")

@app.get("/icon-192.png")
async def icon_192():
    return FileResponse(os.path.join(static_dir, "icon-192.png"), media_type="image/png")

@app.get("/icon-512.png")
async def icon_512():
    return FileResponse(os.path.join(static_dir, "icon-512.png"), media_type="image/png")

@app.get("/icon.svg")
async def icon():
    return FileResponse(os.path.join(static_dir, "icon.svg"), media_type="image/svg+xml")

@app.get("/favicon.ico")
async def favicon():
    return FileResponse(os.path.join(static_dir, "icon.svg"), media_type="image/svg+xml")

@app.get("/health")
async def health():
    return {"status": "ok"}
