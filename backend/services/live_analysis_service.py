"""
即時比賽分析服務
使用 Gemini 進行串流分析 + MediaPipe 骨架偵測
"""
import os
import asyncio
import base64
import time
import json
import cv2
import numpy as np
from typing import Optional, Callable, Dict, Any, List
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
import google.generativeai as genai
from dotenv import load_dotenv

# 延遲載入 mediapipe 以避免啟動時間過長
mp_pose = None
mp_drawing = None
mp_drawing_styles = None

load_dotenv()


class AlertType(Enum):
    """提醒類型"""
    INFO = "info"           # 一般資訊
    WARNING = "warning"     # 警告（發現弱點）
    CRITICAL = "critical"   # 嚴重（連續失誤）
    SUCCESS = "success"     # 正面（好球）
    TACTIC = "tactic"       # 戰術建議


@dataclass
class LiveAlert:
    """即時提醒"""
    id: str
    timestamp: float
    alert_type: AlertType
    title: str
    message: str
    suggestion: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'timestamp': self.timestamp,
            'alert_type': self.alert_type.value,
            'title': self.title,
            'message': self.message,
            'suggestion': self.suggestion
        }


@dataclass
class MatchState:
    """比賽狀態追蹤"""
    player1_score: int = 0
    player2_score: int = 0
    current_set: int = 1
    player1_sets: int = 0
    player2_sets: int = 0
    consecutive_errors: int = 0
    last_point_type: str = ""  # "win" or "lose"
    weakness_detected: List[str] = None
    
    def __post_init__(self):
        if self.weakness_detected is None:
            self.weakness_detected = []
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class LiveAnalysisService:
    """即時分析服務"""
    
    def __init__(self):
        self.api_key = os.getenv('GEMINI_API_KEY')
        if not self.api_key:
            raise ValueError("需要 GEMINI_API_KEY")
        
        genai.configure(api_key=self.api_key)
        
        # 使用 Gemini 2.0 Flash 進行即時分析
        self.model = genai.GenerativeModel('gemini-2.0-flash-exp')
        
        # 初始化 MediaPipe Pose
        self.pose = None
        self._init_pose_detector()
        
        # 分析狀態
        self.is_analyzing = False
        self.match_state = MatchState()
        self.alerts: List[LiveAlert] = []
        self.alert_callback: Optional[Callable] = None
        self.frame_buffer: List[bytes] = []
        self.last_analysis_time = 0
        self.analysis_interval = 3  # 每 3 秒分析一次
        
    def _init_pose_detector(self):
        """初始化姿態偵測器"""
        global mp_pose, mp_drawing, mp_drawing_styles
        try:
            import mediapipe as mp
            mp_pose = mp.solutions.pose
            mp_drawing = mp.solutions.drawing_utils
            mp_drawing_styles = mp.solutions.drawing_styles
            
            self.pose = mp_pose.Pose(
                static_image_mode=False,
                model_complexity=1,
                smooth_landmarks=True,
                enable_segmentation=False,
                min_detection_confidence=0.5,
                min_tracking_confidence=0.5
            )
            print("✅ MediaPipe Pose 初始化成功")
        except Exception as e:
            print(f"⚠️ MediaPipe Pose 初始化失敗: {e}")
            self.pose = None
        
    def set_alert_callback(self, callback: Callable[[LiveAlert], None]):
        """設定提醒回調函數"""
        self.alert_callback = callback
        
    def start_session(self, player_focus: str = None):
        """開始分析會話"""
        self.is_analyzing = True
        self.match_state = MatchState()
        self.alerts = []
        self.player_focus = player_focus
        self.frame_buffer = []
        self.last_analysis_time = time.time()
        
        # 發送開始提醒
        self._emit_alert(
            AlertType.INFO,
            "🎬 開始即時分析",
            f"正在監控比賽{'，關注選手：' + player_focus if player_focus else ''}",
            "請確保畫面清晰，AI 將自動分析每個回合"
        )
        
    def stop_session(self):
        """停止分析會話"""
        self.is_analyzing = False
        
        # 發送結束提醒
        self._emit_alert(
            AlertType.INFO,
            "📊 分析結束",
            f"共產生 {len(self.alerts)} 條分析提醒",
            self._generate_summary()
        )
        
    def _generate_summary(self) -> str:
        """生成分析摘要"""
        warnings = sum(1 for a in self.alerts if a.alert_type == AlertType.WARNING)
        criticals = sum(1 for a in self.alerts if a.alert_type == AlertType.CRITICAL)
        tactics = sum(1 for a in self.alerts if a.alert_type == AlertType.TACTIC)
        
        return f"警告 {warnings} 次，嚴重 {criticals} 次，戰術建議 {tactics} 條"
    
    async def process_frame(self, frame_data: bytes) -> Optional[Dict[str, Any]]:
        """
        處理視訊幀
        
        Args:
            frame_data: 影像幀的 bytes 數據（base64 編碼的圖片）
            
        Returns:
            分析結果（如果有的話）
        """
        if not self.is_analyzing:
            return None
            
        # 加入緩衝區
        self.frame_buffer.append(frame_data)
        
        # 保持最近 10 幀
        if len(self.frame_buffer) > 10:
            self.frame_buffer = self.frame_buffer[-10:]
        
        # 檢查是否需要分析
        current_time = time.time()
        if current_time - self.last_analysis_time < self.analysis_interval:
            return None
            
        self.last_analysis_time = current_time
        
        # 執行分析
        try:
            result = await self._analyze_frames()
            return result
        except Exception as e:
            print(f"分析錯誤: {e}")
            return None
    
    async def _analyze_frames(self) -> Optional[Dict[str, Any]]:
        """分析緩衝區中的幀"""
        if not self.frame_buffer:
            return None
            
        # 取最新的幀進行分析
        latest_frame = self.frame_buffer[-1]
        
        # 建立分析提示
        prompt = self._build_live_prompt()
        
        try:
            # 準備圖片數據
            image_parts = [{
                "mime_type": "image/jpeg",
                "data": latest_frame if isinstance(latest_frame, str) else base64.b64encode(latest_frame).decode()
            }]
            
            # 呼叫 Gemini
            response = await asyncio.to_thread(
                self.model.generate_content,
                [prompt, {"inline_data": image_parts[0]}],
                generation_config={
                    "max_output_tokens": 1024,
                    "temperature": 0.3,
                }
            )
            
            # 解析回應
            result = self._parse_live_response(response.text)
            
            # 處理分析結果
            if result:
                self._process_analysis_result(result)
                
            return result
            
        except Exception as e:
            print(f"Gemini 分析錯誤: {e}")
            return None
    
    def _build_live_prompt(self) -> str:
        """建立即時分析提示詞"""
        focus_text = f"特別關注 {self.player_focus} 選手。" if self.player_focus else ""
        state_text = f"目前比分：{self.match_state.player1_score}-{self.match_state.player2_score}"
        
        return f"""你是一位專業桌球教練，正在即時觀看比賽。{focus_text}

{state_text}

請快速分析這個畫面，回答以下問題（用 JSON 格式）：

```json
{{
  "scene_type": "playing|serving|between_points|other",
  "action_detected": "正在發生的動作描述",
  "point_result": "win|lose|ongoing|unknown",
  "error_type": "失誤類型（如果有）",
  "immediate_feedback": "給教練的即時反饋（10字以內）",
  "tactical_suggestion": "戰術建議（如果適用）",
  "urgency": "low|medium|high|critical"
}}
```

請只輸出 JSON，快速響應。"""

    def _parse_live_response(self, response_text: str) -> Optional[Dict[str, Any]]:
        """解析即時回應"""
        try:
            # 清理回應
            clean_text = response_text.strip()
            if clean_text.startswith('```json'):
                clean_text = clean_text[7:]
            if clean_text.startswith('```'):
                clean_text = clean_text[3:]
            if clean_text.endswith('```'):
                clean_text = clean_text[:-3]
            clean_text = clean_text.strip()
            
            return json.loads(clean_text)
        except:
            return None
    
    def _process_analysis_result(self, result: Dict[str, Any]):
        """處理分析結果，生成提醒"""
        
        urgency = result.get('urgency', 'low')
        scene_type = result.get('scene_type', 'unknown')
        point_result = result.get('point_result', 'unknown')
        error_type = result.get('error_type')
        feedback = result.get('immediate_feedback', '')
        tactic = result.get('tactical_suggestion')
        
        # 更新比賽狀態
        if point_result == 'lose':
            self.match_state.consecutive_errors += 1
            self.match_state.last_point_type = 'lose'
            
            if error_type and error_type not in self.match_state.weakness_detected:
                self.match_state.weakness_detected.append(error_type)
                
        elif point_result == 'win':
            self.match_state.consecutive_errors = 0
            self.match_state.last_point_type = 'win'
        
        # 根據情況生成提醒
        if urgency == 'critical' or self.match_state.consecutive_errors >= 3:
            self._emit_alert(
                AlertType.CRITICAL,
                "⚠️ 連續失誤警告",
                f"連續 {self.match_state.consecutive_errors} 次失誤！{feedback}",
                tactic or "建議暫停調整心態"
            )
        elif urgency == 'high' and error_type:
            self._emit_alert(
                AlertType.WARNING,
                f"🔴 {error_type}",
                feedback,
                tactic
            )
        elif tactic and scene_type == 'between_points':
            self._emit_alert(
                AlertType.TACTIC,
                "💡 戰術建議",
                tactic,
                None
            )
        elif point_result == 'win' and feedback:
            self._emit_alert(
                AlertType.SUCCESS,
                "✅ 好球！",
                feedback,
                None
            )
    
    def detect_pose_and_draw(self, frame_data: bytes) -> tuple[bytes, Optional[Dict[str, Any]]]:
        """
        偵測人體姿態並繪製骨架
        
        Args:
            frame_data: 原始影像幀（JPEG bytes）
            
        Returns:
            (繪製骨架後的影像, 姿態資訊)
        """
        if not self.pose:
            return frame_data, None
            
        try:
            # 解碼圖片
            nparr = np.frombuffer(frame_data, np.uint8)
            image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if image is None:
                return frame_data, None
            
            # 轉換為 RGB
            image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            
            # 執行姿態偵測
            results = self.pose.process(image_rgb)
            
            pose_data = None
            if results.pose_landmarks:
                # 繪製骨架
                mp_drawing.draw_landmarks(
                    image,
                    results.pose_landmarks,
                    mp_pose.POSE_CONNECTIONS,
                    landmark_drawing_spec=mp_drawing_styles.get_default_pose_landmarks_style()
                )
                
                # 提取關鍵點資訊
                landmarks = results.pose_landmarks.landmark
                pose_data = {
                    'detected': True,
                    'landmarks': [
                        {
                            'x': lm.x,
                            'y': lm.y,
                            'z': lm.z,
                            'visibility': lm.visibility
                        }
                        for lm in landmarks
                    ]
                }
            
            # 編碼回 JPEG
            _, encoded = cv2.imencode('.jpg', image)
            return encoded.tobytes(), pose_data
            
        except Exception as e:
            print(f"❌ 姿態偵測錯誤: {e}")
            return frame_data, None
    
    def _emit_alert(self, alert_type: AlertType, title: str, message: str, suggestion: str = None):
        """發送提醒"""
        alert = LiveAlert(
            id=f"alert_{int(time.time() * 1000)}",
            timestamp=time.time(),
            alert_type=alert_type,
            title=title,
            message=message,
            suggestion=suggestion
        )
        
        self.alerts.append(alert)
        
        # 只保留最近 50 條
        if len(self.alerts) > 50:
            self.alerts = self.alerts[-50:]
        
        # 回調通知
        if self.alert_callback:
            self.alert_callback(alert)
            
    def get_current_state(self) -> Dict[str, Any]:
        """取得當前狀態"""
        return {
            'is_analyzing': self.is_analyzing,
            'match_state': self.match_state.to_dict(),
            'recent_alerts': [a.to_dict() for a in self.alerts[-10:]],
            'total_alerts': len(self.alerts)
        }
    
    def update_score(self, player1_score: int, player2_score: int):
        """手動更新比分"""
        self.match_state.player1_score = player1_score
        self.match_state.player2_score = player2_score
        
    def manual_alert(self, message: str):
        """手動發送提醒"""
        self._emit_alert(
            AlertType.INFO,
            "📢 教練提醒",
            message,
            None
        )
