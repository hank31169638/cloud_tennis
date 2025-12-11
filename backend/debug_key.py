import os
import sys
from dotenv import load_dotenv
import google.generativeai as genai

# 強制載入並覆寫
load_dotenv('.env', override=True)

key = os.getenv('GEMINI_API_KEY')
print(f"🔑 Key from .env: {key[:10] if key else 'None'}...")

if not key or "AIzaSyBJS" in key:
    print("❌ CRITICAL: Loaded Key is the OLD one or Missing!")
    print("Checking .env file content directly...")
    with open('.env', 'r') as f:
        print(f.read())
else:
    print("✅ Loaded Key appears to be NEW.")

print("\nConfiguring GenAI...")
genai.configure(api_key=key)

print("Listing Models...")
try:
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(f" - Found model: {m.name}")
            break
    print("✅ GenAI API Call Successful!")
except Exception as e:
    print(f"❌ GenAI API Call Failed: {e}")
