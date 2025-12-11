"""
影片元數據提取服務
使用 Gemini AI 從影片標題和描述中識別選手資訊
"""
import os
import json
from typing import Dict, Any, Optional

class MetadataExtractor:
    def __init__(self, api_key: str = None):
        import google.generativeai as genai
        from dotenv import load_dotenv
        
        load_dotenv(override=True)
        # Debug: check key source
        env_key = os.getenv('GEMINI_API_KEY')
        print(f"🔍 MetadataExtractor Init - Arg: {api_key is not None}, Env: {env_key[:10] if env_key else 'None'}")
        self.api_key = api_key or env_key
        
        if self.api_key:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel('gemini-3.0-pro-preview')
        else:
            self.model = None
            print("⚠️ Warning: GEMINI_API_KEY not found, auto-detection disabled")

    def extract_players(self, title: str, description: str = "") -> Dict[str, Optional[str]]:
        """
        從標題和描述中提取選手名稱
        
        Returns:
            {
                "player1": "Name or None",
                "player2": "Name or None"
            }
        """
        if not self.model:
            return {"player1": None, "player2": None}

        prompt = f"""
請從以下 YouTube 影片標題和描述中，識別出參與對戰的兩位桌球選手名稱。

標題：{title}
描述：{description[:500]}... (略)

請輸出 JSON 格式：
{{
  "player1": "主要選手名稱 (英文拼音優先，如 Lin Yun-Ju)",
  "player2": "對手名稱 (英文拼音優先，如 Ma Long)"
}}

規則：
1. 如果是雙打，請列出該組合的主要代表或完整組合名。
2. 如果只有一位選手（如訓練影片），player2 填 null。
3. 優先使用英文拼音（如官方賽事寫法），如果沒有則用中文。
4. 去除多餘的 title (如 'WTT', 'Final', 'Highlights')。
5. 只輸出 JSON。
"""
        
        try:
            response = self.model.generate_content(prompt)
            text = response.text.replace('```json', '').replace('```', '').strip()
            data = json.loads(text)
            return {
                "player1": data.get("player1"),
                "player2": data.get("player2")
            }
        except Exception as e:
            print(f"❌ Player extraction failed: {e}")
            return {"player1": None, "player2": None}
