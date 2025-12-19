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
    
    # 學習價值與訓練適合度
    learning_value: str          # 這個片段的學習價值
    training_suggestion: str     # 訓練建議
    
    # 訓練模型適合度分析
    is_suitable_for_training: bool # 是否適合訓練模型
    suitability_score: int         # 適合度評分 1-10
    suitability_reason: str        # 適合或不適合的原因 (如：畫面晃動、視角不佳)
    camera_angle: str              # 鏡頭視角 (front/side/top/back/unknown)
    
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
        model_name = os.getenv('GEMINI_MODEL', 'gemini-2.0-flash')
        self.model = genai.GenerativeModel(model_name)
    
    def analyze_player_performance(
        self, 
        video_path: str, 
        player_name: str,
        player_description: str = None,
        video_duration: int = None
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
        prompt = self._build_player_analysis_prompt(player_name, player_description, video_duration)
        
        # 呼叫 Gemini（使用結構化 JSON 輸出模式）
        response = self.model.generate_content(
            [video_file, prompt],
            generation_config={
                "max_output_tokens": 12000,
                "temperature": 0.3,
                "response_mime_type": "application/json",  # 強制 JSON 輸出
            }
        )
        
        # 解析結果
        result = self._parse_player_analysis(response.text, player_name, video_duration)
        
        # 清理
        try:
            genai.delete_file(video_file.name)
        except:
            pass
        
        return result
    
    def _build_player_analysis_prompt(self, player_name: str, player_description: str = None, video_duration: int = None) -> str:
        """建立選手分析提示詞 - 專注於得分/失分片段"""
        
        player_identify = f"（{player_description}）" if player_description else ""
        
        # 計算影片時長描述
        duration_info = ""
        if video_duration:
            minutes = video_duration // 60
            seconds = video_duration % 60
            duration_info = f"""
## ⚠️ 影片時長限制 (CRITICAL)

此影片總長度為 **{minutes} 分 {seconds} 秒** (共 {video_duration} 秒)。
- 所有 `start_seconds` 必須在 0 到 {video_duration} 秒之間。
- 所有 `end_seconds` 必須在 0 到 {video_duration} 秒之間。
- 絕對不可輸出超過 {video_duration} 秒的時間戳！
"""
        
        return f"""你是一位專業的桌球教練和動作分析專家。請仔細觀看這段桌球比賽影片，
針對選手 **{player_name}** {player_identify} 進行表現分析。
{duration_info}
## 🎯 核心任務：識別得分與失分片段

請標註影片中所有明顯的得分或失分瞬間，包括：
1. **慢動作回放 (Instant Replay)** - 這是最有價值的片段
2. **正常速度的得分/失分瞬間** - 如果沒有慢動作回放，也請標註

### 識別特徵
- 比分變化 (如果可見)
- 球落地或出界
- 選手慶祝或失望的肢體語言
- 裁判手勢或判定

### 如何識別慢動作回放？
1. 畫面從俯視全景**切換到近距離特寫**
2. 播放速度變**慢**
3. 可能有字幕標示 "REPLAY" 或比分
4. camera 角度通常是**側面或斜角**，可以看清動作

## 請標記的內容

對於每個**慢動作回放片段**，請標記：
- `start_seconds`: 回放開始的時間（畫面切換到特寫的那一刻）。請精確到秒，確保該時間點確實落在影片總長度之內。
- `end_seconds`: 回放結束的時間（畫面切回正常比賽的那一刻）。
- **⚠️ 嚴格檢查**：所有時間戳 (`start_seconds`, `end_seconds`) 必須為有效數字且不可超過影片的實際總時長。

## 🎬 訓練資料篩選標準 (CRITICAL)

請評估該片段是否適合作為「標準化 AI 訓練素材」：
1. **穩定度 (Stability)**：鏡頭必須穩定。如果畫面劇烈晃動、模糊或失焦，請標記為不適合。
2. **視角 (View Angle)**：優先選擇「正面 (Front)」或「清晰側面 (Side)」的特寫，避開純俯視視角。
3. **慢動作 (Slow Motion)**：強烈建議篩選慢動作回放，這對運動姿態分析最有價值。
4. **排除干擾**：如果畫面上被大型圖卡遮擋關鍵動作，則不適合。

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
      "start_seconds": 片段開始秒數,
      "end_seconds": 片段結束秒數,
      "timestamp_display": "MM:SS",
      "score": "11:9",
      "is_point_won": true,
      "is_replay": true,
      "technique_type": "技術類型代碼",
      "point_type": "得分方式描述",
      "description": "這個動作的詳細描述",
      "quality_score": 動作品質1-10,
      "is_suitable_for_training": true/false,
      "suitability_score": 適合度1-10,
      "suitability_reason": "為什麼適合或不適合",
      "camera_angle": "front/side/top/unknown"
    }}
  ],
  "points_lost": [
    {{
      "clip_id": 1,
      "start_seconds": 片段開始秒數,
      "end_seconds": 片段結束秒數,
      "timestamp_display": "MM:SS",
      "score": "9:11",
      "is_point_won": false,
      "is_replay": true,
      "technique_type": "失誤類型代碼",
      "point_type": "失分方式描述",
      "description": "失誤情況描述",
      "quality_score": 動作品質1-10,
      "is_suitable_for_training": true/false,
      "suitability_score": 適合度1-10,
      "suitability_reason": "說明原因",
      "camera_angle": "front/side/top/unknown"
    }}
  ]
}}
```

## ⚠️ 關鍵提醒

1. **標註所有得分/失分片段** - 包括慢動作回放和正常速度片段
2. **精確時間戳** - start_seconds 是片段開始，end_seconds 是片段結束
3. **片段通常 3-15 秒**
4. **technique_type 使用英文代碼**
5. **時間戳極限** - 絕對不可以標註超過影片結束的時間點
6. **只輸出 JSON**
"""

    def _parse_player_analysis(self, response_text: str, player_name: str, video_duration: int = None) -> Dict[str, Any]:
        """解析選手分析結果"""
        import json
        
        def validate_clip_timestamps(clips: list, max_duration: int = None) -> list:
            """驗證並修正時間戳"""
            if not max_duration:
                return clips
            
            validated = []
            for clip in clips:
                start = clip.get('start_seconds', 0)
                end = clip.get('end_seconds', start + 5)
                
                # 如果超過總長度，跳過這個 clip
                if start >= max_duration:
                    print(f"⚠️ 跳過無效片段: start_seconds={start} > video_duration={max_duration}")
                    continue
                
                # 修正 end 時間
                if end > max_duration:
                    clip['end_seconds'] = max_duration
                    print(f"ℹ️ 修正 end_seconds: {end} -> {max_duration}")
                
                validated.append(clip)
            
            return validated
        
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
            
            # DEBUG: 輸出 AI 回傳的原始資料
            print("=" * 60)
            print("🔍 [DEBUG] AI 回傳原始資料:")
            print("-" * 60)
            print(response_text[:2000])  # 只印前 2000 字元避免過長
            if len(response_text) > 2000:
                print(f"... (共 {len(response_text)} 字元，已截斷)")
            print("=" * 60)
            
            parsed = json.loads(clean_text)
            
            # DEBUG: 輸出解析後的片段數量
            print(f"📊 [DEBUG] 解析結果: points_won={len(parsed.get('points_won', []))}, points_lost={len(parsed.get('points_lost', []))}")
            
            # 驗證時間戳
            points_won = validate_clip_timestamps(parsed.get("points_won", []), video_duration)
            points_lost = validate_clip_timestamps(parsed.get("points_lost", []), video_duration)
            
            # 標準化輸出
            return {
                "success": True,
                "player_name": player_name,
                "match_summary": parsed.get("match_summary", {}),
                "points_won": points_won,
                "points_lost": points_lost,
                "all_clips": self._merge_and_sort_clips(points_won, points_lost),
                "training_recommendations": parsed.get("training_recommendations", []),
                "quality_distribution": self._calculate_quality_distribution(points_won, points_lost),
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
        player_description,
        video_duration=download_result.get("duration")
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
