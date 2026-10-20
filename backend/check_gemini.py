"""
check_gemini.py - tests your Gemini key BEFORE you rely on it in the app.

Run from the backend folder (with the venv active):   python check_gemini.py

For each model it sends a tiny test picture (a red circle) and asks for JSON,
which is the same kind of request the app makes, and prints OK or the reason
it failed. It then tells you what to put in GEMINI_MODEL in backend/.env.
"""
import io
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")

from google import genai  # noqa: E402
from google.genai import types  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402

from matching import DEFAULT_MODEL  # noqa: E402

FALLBACK_MODELS = ["gemini-3.8-flash", "gemini-3.6-flash", "gemini-3.1-flash-lite"]


def test_image():
    img = Image.new("RGB", (256, 256), "white")
    ImageDraw.Draw(img).ellipse((48, 48, 208, 208), fill=(220, 20, 20))
    buf = io.BytesIO()
    img.save(buf, "JPEG")
    return types.Part.from_bytes(data=buf.getvalue(), mime_type="image/jpeg")


def try_model(client, model, api_key):
    started = time.time()
    try:
        response = client.models.generate_content(
            model=model,
            contents=[test_image(), "What color is the circle? Answer as JSON."],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema={
                    "type": "OBJECT",
                    "properties": {"color": {"type": "STRING"}},
                    "required": ["color"],
                },
            ),
        )
        took = time.time() - started
        return True, f"saw the picture and answered {response.text.strip()}  ({took:.1f}s)"
    except Exception as err:
        message = f"{type(err).__name__}: {err}".replace(api_key, "***")
        return False, message[:300]


def main():
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        print("GEMINI_API_KEY is empty. Add it to backend/.env (the line GEMINI_API_KEY=...) and save.")
        sys.exit(1)
    print(f"Key found ({len(api_key)} characters). Testing models with a real image request.\n")

    configured = os.environ.get("GEMINI_MODEL", "").strip() or DEFAULT_MODEL
    models = [configured] + [m for m in FALLBACK_MODELS if m != configured]

    client = genai.Client(api_key=api_key)
    working = []
    for model in models:
        ok, detail = try_model(client, model, api_key)
        print(f"  {'OK    ' if ok else 'FAILED'}  {model}\n          {detail}\n")
        if ok:
            working.append(model)

    if not working:
        print("No model worked. Read the FAILED reasons above:")
        print("  - 'API key not valid' / 403: re-copy the key into .env (no quotes, no spaces).")
        print("  - 404 / 'not found': the model name is outdated. See https://ai.google.dev/gemini-api/docs/models")
        print("  - 429 / quota: your key's limit is used up or has no access to that model.")
        sys.exit(1)

    if configured in working:
        print(f"Your configured model ({configured}) works. You're ready for Step 3.")
    else:
        print(f"Your configured model ({configured}) did NOT work, but others did.")
        print(f"Put this line in backend/.env and save:\n\n    GEMINI_MODEL={working[0]}\n")


if __name__ == "__main__":
    main()
