"""
選手表現分析模組
分析特定選手的得分與失分片段，並進行動作品質標註
"""
import os
import json
import time
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from enum import Enum


class TechniqueType(Enum):
    """技術類型分類"""
    # 攻擊技術 (Offensive)
    FOREHAND_ATTACK = "forehand_attack"     # 正手進攻
    BACKHAND_ATTACK = "backhand_attack"     # 反手進攻
    SMASH = "smash"                         # 扣殺
    LOOP_DRIVE = "loop_drive"               # 弧圈球
    
    # 防守技術 (Defensive)
    BLOCK = "block"                         # 擋球
    CHOP = "chop"                           # 削球
    LOB = "lob"                             # 挑高球
    
    # 發球接發 (Serve & Return)
    SERVE_ACE = "serve_ace"                 # 發球得分
    SERVE_ATTACK = "serve_attack"           # 發球搶攻
    RECEIVE_ATTACK = "receive_attack"       # 接發搶攻
    RECEIVE_CONTROL = "receive_control"     # 接發控制
    
    # 失誤類型 (Errors)
    FOREHAND_ERROR = "forehand_error"       # 正手失誤
    BACKHAND_ERROR = "backhand_error"       # 反手失誤
    SERVE_ERROR = "serve_error"             # 發球失誤
    RECEIVE_ERROR = "receive_error"         # 接發失誤
    NET_ERROR = "net_error"                 # 掛網
    OUT_OF_BOUNDS = "out_of_bounds"         # 出界
    FOOTWORK_ERROR = "footwork_error"       # 腳步不到位
    JUDGMENT_ERROR = "judgment_error"       # 判斷失誤
    
    # 其他
    OTHER = "other"                         # 其他


@dataclass
class AnalyzedClip:
    """分析後的片段"""
    clip_id: int
    timestamp_seconds: int
    timestamp_display: str
    is_point_won: bool           # True=得分, False=失分
    point_type: str              # 得分/失分方式
    description: str             # 情況描述
    
    # AI 動作品質分析
    action_quality: str          # good/normal/bad
    quality_reason: str          # 品質評定原因
    technical_score: int         # 技術評分 1-10
    
    # 動作細節
    footwork_analysis: str       # 腳步分析
    stroke_analysis: str         # 擊球分析
    positioning_analysis: str    # 位置分析
    timing_analysis: str         # 時機分析
    
    # 學習價值
    learning_value: str          # 這個片段的學習價值
    training_suggestion: str     # 訓練建議
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class PlayerPerformanceAnalyzer:
    """選手表現分析器"""
    
    def __init__(self, api_key: str = None):
        import google.generativeai as genai
        from dotenv import load_dotenv
        
        load_dotenv()
        self.api_key = api_key or os.getenv('GEMINI_API_KEY')
        
        if not self.api_key:
            raise ValueError("需要 GEMINI_API_KEY")
        
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel('gemini-2.0-flash')
    
    def analyze_player_performance(
        self, 
        video_path: str, 
        player_name: str,
        player_description: str = None
    ) -> Dict[str, Any]:
        """
        分析特定選手的完整表現
        
        Args:
            video_path: 影片路徑
            player_name: 選手名稱
            player_description: 選手描述（幫助識別，如「穿紅色衣服」）
        
        Returns:
            包含得分和失分分析的完整報告
        """
        import google.generativeai as genai
        
        print(f"📹 正在上傳影片進行 {player_name} 表現分析...")
        
        # 上傳影片
        video_file = genai.upload_file(path=video_path)
        
        # 等待處理
        while video_file.state.name == "PROCESSING":
            print("⏳ 處理中...")
            time.sleep(5)
            video_file = genai.get_file(video_file.name)
        
        if video_file.state.name == "FAILED":
            raise RuntimeError("影片處理失敗")
        
        print(f"🤖 正在分析 {player_name} 的表現...")
        
        # 建立分析提示
        prompt = self._build_player_analysis_prompt(player_name, player_description)
        
        # 呼叫 Gemini
        response = self.model.generate_content(
            [video_file, prompt],
            generation_config={
                "max_output_tokens": 12000,
                "temperature": 0.3,
            }
        )
        
        # 解析結果
        result = self._parse_player_analysis(response.text, player_name)
        
        # 清理
        try:
            genai.delete_file(video_file.name)
        except:
            pass
        
        return result
    
    def _build_player_analysis_prompt(self, player_name: str, player_description: str = None) -> str:
        """建立選手分析提示詞 - 專注於慢動作回放片段"""
        
        player_identify = f"（{player_description}）" if player_description else ""
        
        return f"""你是一位專業的桌球教練和動作分析專家。請仔細觀看這段桌球比賽影片，
針對選手 **{player_name}** {player_identify} 進行表現分析。

## 🎯 核心任務：識別「慢動作回放」片段

⚠️ **非常重要**：我需要的是比賽中的「**慢動作回放**」(Instant Replay) 片段，而**不是**完整的對打過程。

### 什麼是慢動作回放？
- 通常在得分/失分後，轉播會播放**慢動作重播**
- 這些片段通常是**近距離特寫**，不是第三視角俯視圖
- 可以清楚看到球的落點、選手的動作細節
- 畫面可能會有慢動作效果

### 如何識別慢動作回放？
1. 畫面從俯視全景**切換到近距離特寫**
2. 播放速度變**慢**
3. 可能有字幕標示 "REPLAY" 或比分
4. camera 角度通常是**側面或斜角**，可以看清動作

## 請標記的內容

對於每個**慢動作回放片段**，請標記：
- `start_seconds`: 回放開始的時間（畫面切換到特寫的那一刻）
- `end_seconds`: 回放結束的時間（畫面切回正常比賽的那一刻）

## 技術類型分類

### 攻擊技術 (得分)
- `forehand_attack` - 正手進攻
- `backhand_attack` - 反手進攻
- `smash` - 扣殺
- `loop_drive` - 弧圈球

### 發球接發
- `serve_ace` - 發球得分
- `serve_attack` - 發球搶攻
- `receive_attack` - 接發搶攻

### 失誤類型 (失分)
- `forehand_error` - 正手失誤
- `backhand_error` - 反手失誤
- `serve_error` - 發球失誤
- `receive_error` - 接發失誤
- `net_error` - 掛網
- `out_of_bounds` - 出界

## JSON 輸出格式

```json
{{
  "player_name": "{player_name}",
  "match_summary": {{
    "total_points_won": 總得分回放數,
    "total_points_lost": 總失分回放數,
    "overall_performance": "整體表現評價"
  }},
  "points_won": [
    {{
      "clip_id": 1,
      "start_seconds": 回放開始秒數,
      "end_seconds": 回放結束秒數,
      "timestamp_display": "MM:SS",
      "is_point_won": true,
      "is_replay": true,
      "technique_type": "技術類型代碼",
      "point_type": "得分方式描述",
      "description": "這個動作的詳細描述",
      "quality_score": 動作品質1-10
    }}
  ],
  "points_lost": [
    {{
      "clip_id": 1,
      "start_seconds": 回放開始秒數,
      "end_seconds": 回放結束秒數,
      "timestamp_display": "MM:SS",
      "is_point_won": false,
      "is_replay": true,
      "technique_type": "失誤類型代碼",
      "point_type": "失分方式描述",
      "description": "失誤情況描述",
      "quality_score": 動作品質1-10
    }}
  ]
}}
```

## ⚠️ 關鍵提醒

1. **只標記慢動作回放片段** - 不要標記正常速度的對打過程
2. **精確時間戳** - start_seconds 是回放開始，end_seconds 是回放結束
3. **回放通常 3-8 秒** - 如果片段超過 15 秒，可能不是回放
4. **technique_type 使用英文代碼**
5. **只輸出 JSON**
"""

    def _parse_player_analysis(self, response_text: str, player_name: str) -> Dict[str, Any]:
        """解析選手分析結果"""
        import json
        
        try:
            # 清理 markdown 標記
            clean_text = response_text.strip()
            if clean_text.startswith('```json'):
                clean_text = clean_text[7:]
            if clean_text.startswith('```'):
                clean_text = clean_text[3:]
            if clean_text.endswith('```'):
                clean_text = clean_text[:-3]
            clean_text = clean_text.strip()
            
            parsed = json.loads(clean_text)
            
            # 標準化輸出
            return {
                "success": True,
                "player_name": player_name,
                "match_summary": parsed.get("match_summary", {}),
                "points_won": parsed.get("points_won", []),
                "points_lost": parsed.get("points_lost", []),
                "all_clips": self._merge_and_sort_clips(
                    parsed.get("points_won", []),
                    parsed.get("points_lost", [])
                ),
                "training_recommendations": parsed.get("training_recommendations", []),
                "quality_distribution": self._calculate_quality_distribution(
                    parsed.get("points_won", []),
                    parsed.get("points_lost", [])
                ),
                "raw_response": response_text
            }
            
        except json.JSONDecodeError as e:
            print(f"⚠️ JSON 解析失敗: {e}")
            return {
                "success": False,
                "player_name": player_name,
                "error": str(e),
                "raw_response": response_text,
                "points_won": [],
                "points_lost": [],
                "all_clips": []
            }
    
    def _merge_and_sort_clips(self, points_won: List, points_lost: List) -> List[Dict]:
        """合併並按時間排序所有片段"""
        all_clips = []
        
        for clip in points_won:
            clip["is_point_won"] = True
            all_clips.append(clip)
        
        for clip in points_lost:
            clip["is_point_won"] = False
            all_clips.append(clip)
        
        # 按時間排序
        all_clips.sort(key=lambda x: x.get("timestamp_seconds", 0))
        
        return all_clips
    
    def _calculate_quality_distribution(self, points_won: List, points_lost: List) -> Dict[str, Any]:
        """計算動作品質分布"""
        all_clips = points_won + points_lost
        
        distribution = {
            "total": len(all_clips),
            "good": 0,
            "normal": 0,
            "bad": 0,
            "by_result": {
                "won": {"good": 0, "normal": 0, "bad": 0, "total": len(points_won)},
                "lost": {"good": 0, "normal": 0, "bad": 0, "total": len(points_lost)}
            }
        }
        
        for clip in points_won:
            quality = clip.get("action_quality", "normal")
            distribution[quality] = distribution.get(quality, 0) + 1
            distribution["by_result"]["won"][quality] += 1
        
        for clip in points_lost:
            quality = clip.get("action_quality", "normal")
            distribution[quality] = distribution.get(quality, 0) + 1
            distribution["by_result"]["lost"][quality] += 1
        
        return distribution


def analyze_player_from_youtube(
    youtube_url: str,
    player_name: str,
    player_description: str = None
) -> Dict[str, Any]:
    """
    從 YouTube 影片分析選手表現
    
    Args:
        youtube_url: YouTube 影片 URL
        player_name: 選手名稱
        player_description: 選手描述
    
    Returns:
        完整的分析結果
    """
    from youtube_analyzer import YouTubeDownloader
    
    # 下載影片
    downloader = YouTubeDownloader()
    download_result = downloader.download(youtube_url)
    
    if not download_result.get("success"):
        raise RuntimeError("影片下載失敗")
    
    # 分析選手表現
    analyzer = PlayerPerformanceAnalyzer()
    result = analyzer.analyze_player_performance(
        download_result["file_path"],
        player_name,
        player_description
    )
    
    # 加入影片資訊
    result["video_info"] = {
        "url": youtube_url,
        "video_id": download_result.get("video_id"),
        "title": download_result.get("title"),
        "duration": download_result.get("duration")
    }
    
    # 清理暫存檔案
    try:
        os.remove(download_result["file_path"])
    except:
        pass
    
    return result


if __name__ == "__main__":
    # 測試
    analyzer = PlayerPerformanceAnalyzer()
    print("PlayerPerformanceAnalyzer 初始化成功")
