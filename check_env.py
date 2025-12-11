import os

path = r'c:\Users\hank\Desktop\programing\Table-tennis-AI\backend\.env'

if not os.path.exists(path):
    print("File not found")
else:
    with open(path, 'rb') as f:
        raw = f.read()
    
    print(f"First 20 bytes: {raw[:20]}")
    
    # Try decoding
    text = ""
    try:
        text = raw.decode('utf-8')
        print("Decoded as UTF-8")
    except:
        try:
            text = raw.decode('utf-16')
            print("Decoded as UTF-16")
        except:
            print("Unknown encoding")
            
    if "AIzaSyBJSqri3L" in text:
        print("⚠️ OLD KEY FOUND in .env!")
    elif "GEMINI_API_KEY" in text:
        # Find the line
        for line in text.splitlines():
            if "GEMINI_API_KEY" in line:
                print(f"Found line: {line.strip()}")
    else:
        print("Key not found in text")
