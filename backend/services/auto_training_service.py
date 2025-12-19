"""
自動訓練服務
將 YouTube 分析結果轉換為訓練資料
"""
import os
import json
import subprocess
import shutil
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
import uuid


class TechniqueType(Enum):
    """技術類型分類"""
    # 攻擊技術
    FOREHAND_ATTACK = "forehand_attack"
    BACKHAND_ATTACK = "backhand_attack"
    SMASH = "smash"
    LOOP_DRIVE = "loop_drive"
    # 防守技術
    BLOCK = "block"
    CHOP = "chop"
    LOB = "lob"
    # 發球接發
    SERVE_ACE = "serve_ace"
    SERVE_ATTACK = "serve_attack"
    RECEIVE_ATTACK = "receive_attack"
    RECEIVE_CONTROL = "receive_control"
    # 失誤類型
    FOREHAND_ERROR = "forehand_error"
    BACKHAND_ERROR = "backhand_error"
    SERVE_ERROR = "serve_error"
    RECEIVE_ERROR = "receive_error"
    NET_ERROR = "net_error"
    OUT_OF_BOUNDS = "out_of_bounds"
    FOOTWORK_ERROR = "footwork_error"
    JUDGMENT_ERROR = "judgment_error"
    # 其他
    OTHER = "other"

# 保留舊的 ActionLabel 別名以保持向後相容
ActionLabel = TechniqueType


@dataclass
class TrainingClip:
    """訓練片段"""
    clip_id: str
    source_video: str        # YouTube URL 或本地路徑
    source_type: str         # "youtube" 或 "local"
    start_time: float        # 開始時間（秒）
    end_time: float          # 結束時間（秒）
    label: str               # 標籤
    label_confidence: float  # 標籤信心度 (0-1)
    description: str         # 描述（來自 Gemini）
    error_type: Optional[str]  # 失誤類型
    status: str              # pending, approved, rejected, processed
    created_at: str
    processed_at: Optional[str]
    skeleton_path: Optional[str]  # 骨架資料路徑
    clip_path: Optional[str] = None  # 已切割的片段路徑 (來自選手分析)
    
    # 訓練適合度 (由 AI 評核)
    is_suitable_for_training: bool = False
    suitability_score: int = 0
    suitability_reason: str = ""
    camera_angle: str = "unknown"
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class AutoTrainingService:
    """自動訓練服務"""
    
    def __init__(self):
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.data_dir = os.path.join(self.base_dir, 'data', 'training_clips')
        self.clips_file = os.path.join(self.data_dir, 'clips.json')
        self.videos_dir = os.path.join(self.data_dir, 'videos')
        self.skeletons_dir = os.path.join(self.data_dir, 'skeletons')
        
        # 建立目錄
        os.makedirs(self.videos_dir, exist_ok=True)
        os.makedirs(self.skeletons_dir, exist_ok=True)
        
        # 載入現有片段
        self.clips: Dict[str, TrainingClip] = {}
        self._load_clips()
        
    
    def _load_clips(self):
        """載入片段資料"""
        if os.path.exists(self.clips_file):
            with open(self.clips_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for clip_data in data:
                    clip = TrainingClip(**clip_data)
                    self.clips[clip.clip_id] = clip
    
    def _save_clips(self):
        """儲存片段資料"""
        with open(self.clips_file, 'w', encoding='utf-8') as f:
            json.dump([c.to_dict() for c in self.clips.values()], f, ensure_ascii=False, indent=2)
    
    def import_from_youtube_analysis(
        self, 
        analysis_result: Dict[str, Any],
        auto_approve: bool = False,
        confidence_threshold: float = 0.7
    ) -> List[TrainingClip]:
        """
        從 YouTube 分析結果匯入訓練片段
        
        Args:
            analysis_result: YouTube 分析的結果 (包含 point_losses 和 point_wins)
            auto_approve: 是否自動核准高信心度片段
            confidence_threshold: 自動核准的信心度門檻
        
        Returns:
            新建立的訓練片段列表
        """
        new_clips = []
        
        video_url = analysis_result.get('video_url', '')
        
        # 1. 處理失分 (Bad)
        point_losses = analysis_result.get('point_losses', [])
        for point in point_losses:
            # 解析時間 (優先使用精確秒數)
            if 'start_seconds' in point and 'end_seconds' in point:
                start_time = float(point['start_seconds'])
                end_time = float(point['end_seconds'])
            else:
                timestamp = point.get('timestamp_display', point.get('timestamp', '0:00'))
                start_time = self._parse_timestamp(timestamp)
                end_time = start_time + 5  # 預設擷取 5 秒片段
            
            # 決定標籤
            error_type = point.get('loss_type', point.get('error_type', ''))
            description = point.get('description', '')
            
            label, confidence = self._determine_label(error_type, description)
            # 如果判斷為 Normal，但在 point_losses 裡，強制設為 Bad
            if label == ActionLabel.NORMAL:
                label = ActionLabel.BAD
                confidence = 0.9
            
            # 建立片段
            clip = TrainingClip(
                clip_id=str(uuid.uuid4())[:8],
                source_video=video_url,
                source_type="youtube",
                start_time=start_time,
                end_time=end_time,
                label=label.value,
                label_confidence=confidence,
                description=f"[失分] {error_type}: {description}",
                error_type=error_type,
                status="approved" if (auto_approve and confidence >= confidence_threshold) else "pending",
                created_at=datetime.now().isoformat(),
                processed_at=None,
                skeleton_path=None,
                
                # 填入適合度資訊
                is_suitable_for_training=point.get('is_suitable_for_training', False),
                suitability_score=point.get('suitability_score', 0),
                suitability_reason=point.get('suitability_reason', ""),
                camera_angle=point.get('camera_angle', "unknown")
            )
            
            self.clips[clip.clip_id] = clip
            new_clips.append(clip)

        # 2. 處理得分 (Good)
        point_wins = analysis_result.get('point_wins', [])
        for point in point_wins:
            # 解析時間
            if 'start_seconds' in point and 'end_seconds' in point:
                start_time = float(point['start_seconds'])
                end_time = float(point['end_seconds'])
            else:
                timestamp = point.get('timestamp_display', point.get('timestamp', '0:00'))
                start_time = self._parse_timestamp(timestamp)
                end_time = start_time + 5
            
            win_type = point.get('win_type', '')
            description = point.get('description', '')
            
            # 建立片段
            clip = TrainingClip(
                clip_id=str(uuid.uuid4())[:8],
                source_video=video_url,
                source_type="youtube",
                start_time=start_time,
                end_time=end_time,
                label="good",
                label_confidence=0.95,
                description=f"[得分] {win_type}: {description}",
                error_type=None,
                status="approved" if auto_approve else "pending",
                created_at=datetime.now().isoformat(),
                processed_at=None,
                skeleton_path=None,
                
                # 填入適合度資訊
                is_suitable_for_training=point.get('is_suitable_for_training', False),
                suitability_score=point.get('suitability_score', 0),
                suitability_reason=point.get('suitability_reason', ""),
                camera_angle=point.get('camera_angle', "unknown")
            )
            
            self.clips[clip.clip_id] = clip
            new_clips.append(clip)
            
        self._save_clips()
        return new_clips

    def import_from_player_analysis(
        self,
        analysis_result: Dict[str, Any],
        player_name: str,
        auto_approve: bool = True,
        auto_process: bool = False,
        confidence_threshold: float = 0.7
    ) -> List[TrainingClip]:
        """
        從選手分析結果匯入訓練片段
        
        Args:
            analysis_result: 選手分析的結果 (包含 scoring_clips 和 losing_clips)
            player_name: 選手名稱
            auto_approve: 是否自動核准高信心度片段 (預設 True)
            auto_process: 是否自動處理並匯出到訓練資料夾 (預設 True)
            confidence_threshold: 自動核准的信心度門檻
        
        Returns:
            新建立的訓練片段列表
        """
        new_clips = []
        
        video_url = analysis_result.get('video_url', '')
        scoring_clips = analysis_result.get('scoring_clips', [])
        losing_clips = analysis_result.get('losing_clips', [])
        
        # 處理得分片段
        for clip in scoring_clips:
            training_clip = self._create_clip_from_performance(
                clip, video_url, player_name, is_scoring=True,
                auto_approve=auto_approve, confidence_threshold=confidence_threshold
            )
            self.clips[training_clip.clip_id] = training_clip
            new_clips.append(training_clip)
        
        # 處理失分片段
        for clip in losing_clips:
            training_clip = self._create_clip_from_performance(
                clip, video_url, player_name, is_scoring=False,
                auto_approve=auto_approve, confidence_threshold=confidence_threshold
            )
            self.clips[training_clip.clip_id] = training_clip
            new_clips.append(training_clip)
        
        self._save_clips()
        
        # 自動處理：匯出到訓練資料夾
        if auto_process and auto_approve:
            print(f"🔄 自動處理：匯出 {len(new_clips)} 個片段到訓練資料夾...")
            export_result = self.export_approved_clips()
            print(f"✅ 匯出完成: good={export_result.get('good', 0)}, bad={export_result.get('bad', 0)}, normal={export_result.get('normal', 0)}")
        
        return new_clips
    
    def _create_clip_from_performance(
        self,
        clip_data: Dict[str, Any],
        video_url: str,
        player_name: str,
        is_scoring: bool,
        auto_approve: bool,
        confidence_threshold: float
    ) -> TrainingClip:
        """
        從表現片段建立訓練片段
        
        Args:
            clip_data: 片段資料
            video_url: 影片 URL
            player_name: 選手名稱
            is_scoring: 是否為得分片段
            auto_approve: 是否自動核准
            confidence_threshold: 核准門檻
        
        Returns:
            訓練片段
        """
        # 優先使用精確秒數（來自 AI 分析）
        if 'start_seconds' in clip_data and clip_data['start_seconds'] is not None:
            start_time = float(clip_data['start_seconds'])
        else:
            timestamp = clip_data.get('timestamp', '0:00')
            start_time = self._parse_timestamp(timestamp)
        
        if 'end_seconds' in clip_data and clip_data['end_seconds'] is not None:
            end_time = float(clip_data['end_seconds'])
        else:
            end_time = start_time + 8  # 預設 8 秒（一個完整回合）
        
        # 使用 AI 標註的技術類型 (technique_type)
        technique_type = clip_data.get('technique_type', 'other')
        
        # 驗證技術類型
        valid_techniques = [t.value for t in TechniqueType]
        if technique_type not in valid_techniques:
            # 根據是否得分給予預設類別
            if is_scoring:
                technique_type = 'forehand_attack'  # 得分預設正手進攻
            else:
                technique_type = 'forehand_error'   # 失分預設正手失誤
        
        # 設定信心度（AI 標籤有一定的信心度）
        quality_score = clip_data.get('quality_score', 7)
        confidence = quality_score / 10.0  # 轉換為 0-1
        
        # 建立描述
        point_type = clip_data.get('point_type', '')
        quality_reason = clip_data.get('quality_reason', '')
        description = clip_data.get('description', '')
        
        full_description = f"[{player_name}] "
        if is_scoring:
            full_description += f"得分 - {point_type}"
        else:
            full_description += f"失分 - {point_type}"
        
        if quality_reason:
            full_description += f" ({quality_reason})"
        if description:
            full_description += f" | {description}"
        
        # 建立片段
        return TrainingClip(
            clip_id=str(uuid.uuid4())[:8],
            source_video=video_url,
            source_type="youtube",
            start_time=start_time,
            end_time=end_time,
            label=technique_type,  # 使用技術類型作為標籤
            label_confidence=confidence,
            description=full_description,
            error_type=technique_type if not is_scoring else None,
            status="approved" if (auto_approve and confidence >= confidence_threshold) else "pending",
            created_at=datetime.now().isoformat(),
            processed_at=None,
            skeleton_path=None,
            clip_path=clip_data.get('clip_path'),  # 使用已切割的片段路徑
            
            # 填入適合度資訊
            is_suitable_for_training=clip_data.get('is_suitable_for_training', False),
            suitability_score=clip_data.get('suitability_score', 0),
            suitability_reason=clip_data.get('suitability_reason', ""),
            camera_angle=clip_data.get('camera_angle', "unknown")
        )
    
    def _parse_timestamp(self, timestamp: str) -> float:
        """解析時間戳為秒數"""
        try:
            parts = timestamp.replace('：', ':').split(':')
            if len(parts) == 2:
                minutes, seconds = parts
                return int(minutes) * 60 + float(seconds)
            elif len(parts) == 3:
                hours, minutes, seconds = parts
                return int(hours) * 3600 + int(minutes) * 60 + float(seconds)
            else:
                return float(timestamp)
        except:
            return 0.0
    
    def _determine_label(self, error_type: str, description: str) -> Tuple[ActionLabel, float]:
        """根據失誤類型決定標籤和信心度"""
        
        # 精確匹配
        if error_type in self.error_to_label:
            return self.error_to_label[error_type], 0.9
        
        # 關鍵字匹配
        description_lower = description.lower()
        error_lower = error_type.lower() if error_type else ""
        combined = f"{error_lower} {description_lower}"
        
        # 失誤關鍵字
        bad_keywords = ['失誤', '出界', '掛網', '失敗', '錯誤', '不到位', 'error', 'miss', 'fault']
        for kw in bad_keywords:
            if kw in combined:
                return ActionLabel.BAD, 0.8
        
        # 得分關鍵字
        good_keywords = ['得分', '制勝', 'ace', '扣殺', '漂亮', 'winner', 'point']
        for kw in good_keywords:
            if kw in combined:
                return ActionLabel.GOOD, 0.7
        
        # 預設為 bad（因為是從失分分析來的）
        return ActionLabel.BAD, 0.6
    
    def get_pending_clips(self) -> List[TrainingClip]:
        """取得待審核的片段"""
        return [c for c in self.clips.values() if c.status == "pending"]
    
    def get_approved_clips(self) -> List[TrainingClip]:
        """取得已核准的片段"""
        return [c for c in self.clips.values() if c.status == "approved"]
    
    def approve_clip(self, clip_id: str, label: Optional[str] = None) -> bool:
        """核准片段，可選擇性修改標籤"""
        if clip_id not in self.clips:
            return False
        
        clip = self.clips[clip_id]
        clip.status = "approved"
        
        if label:
            clip.label = label
            clip.label_confidence = 1.0  # 人工審核信心度為 100%
        
        self._save_clips()
        return True
    
    def reject_clip(self, clip_id: str) -> bool:
        """拒絕片段"""
        if clip_id not in self.clips:
            return False
        
        self.clips[clip_id].status = "rejected"
        self._save_clips()
        return True
    
    def update_clip_label(self, clip_id: str, label: str) -> bool:
        """更新片段標籤"""
        if clip_id not in self.clips:
            return False
        
        if label not in [l.value for l in ActionLabel]:
            return False
        
        self.clips[clip_id].label = label
        self.clips[clip_id].label_confidence = 1.0
        self._save_clips()
        return True
    
    def download_and_extract_clip(self, clip_id: str) -> Optional[str]:
        """
        下載並擷取影片片段
        
        Returns:
            片段影片的路徑，失敗則為 None
        """
        if clip_id not in self.clips:
            return None
        
        clip = self.clips[clip_id]
        
        if clip.source_type != "youtube":
            return None
        
        output_path = os.path.join(self.videos_dir, f"{clip_id}.mp4")
        
        try:
            # 使用 yt-dlp 下載特定片段
            # 注意：yt-dlp 的 --download-sections 需要特定格式
            import yt_dlp
            
            ydl_opts = {
                'format': '(bestvideo[height<=720]+bestaudio/best[height<=720])[ext=mp4]/best[ext=mp4]/best',
                'outtmpl': output_path.replace('.mp4', '.%(ext)s'),
                'quiet': False,
                'no_warnings': False,
                'merge_output_format': 'mp4',
                'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'postprocessors': [{
                    'key': 'FFmpegVideoConvertor',
                    'preferedformat': 'mp4',
                }],
                'ignoreerrors': False,
                'skip_unavailable_fragments': True,
                # 下載完整影片後再用 ffmpeg 切割
            }
            
            # 先下載完整影片到暫存
            temp_path = os.path.join(self.videos_dir, f"temp_{clip_id}.mp4")
            ydl_opts['outtmpl'] = temp_path.replace('.mp4', '.%(ext)s')
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([clip.source_video])
            
            # 找到下載的檔案
            for ext in ['mp4', 'webm', 'mkv']:
                temp_file = temp_path.replace('.mp4', f'.{ext}')
                if os.path.exists(temp_file):
                    # 用 ffmpeg 切割片段
                    duration = clip.end_time - clip.start_time
                    cmd = [
                        'ffmpeg', '-y',
                        '-ss', str(clip.start_time),
                        '-i', temp_file,
                        '-t', str(duration),
                        '-c:v', 'libx264',
                        '-c:a', 'aac',
                        output_path
                    ]
                    subprocess.run(cmd, capture_output=True)
                    
                    # 清理暫存
                    os.remove(temp_file)
                    break
            
            if os.path.exists(output_path):
                return output_path
            
        except Exception as e:
            print(f"下載片段失敗: {e}")
        
        return None
    
    def extract_skeleton(self, clip_id: str) -> Optional[str]:
        """
        從影片片段提取骨架資料
        
        Returns:
            骨架資料的路徑
        """
        if clip_id not in self.clips:
            return None
        
        clip = self.clips[clip_id]
        video_path = os.path.join(self.videos_dir, f"{clip_id}.mp4")
        
        if not os.path.exists(video_path):
            # 嘗試下載
            video_path = self.download_and_extract_clip(clip_id)
            if not video_path:
                return None
        
        # 使用現有的骨架提取模組
        try:
            from skeleton import extract_skeleton_from_video
            
            output_dir = os.path.join(self.skeletons_dir, clip_id)
            os.makedirs(output_dir, exist_ok=True)
            
            # 提取骨架
            skeleton_data = extract_skeleton_from_video(video_path, output_dir)
            
            if skeleton_data:
                skeleton_path = os.path.join(output_dir, 'skeleton.json')
                with open(skeleton_path, 'w') as f:
                    json.dump(skeleton_data, f)
                
                clip.skeleton_path = skeleton_path
                clip.processed_at = datetime.now().isoformat()
                clip.status = "processed"
                self._save_clips()
                
                return skeleton_path
        except ImportError:
            print("骨架提取模組未找到")
        except Exception as e:
            print(f"骨架提取失敗: {e}")
        
        return None
    
    def prepare_training_batch(self, label: Optional[str] = None) -> Dict[str, Any]:
        """
        準備訓練批次
        
        Args:
            label: 篩選特定標籤，None 表示全部
        
        Returns:
            訓練批次資訊
        """
        processed_clips = [c for c in self.clips.values() if c.status == "processed"]
        
        if label:
            processed_clips = [c for c in processed_clips if c.label == label]
        
        # 按標籤分組
        by_label = {}
        for clip in processed_clips:
            if clip.label not in by_label:
                by_label[clip.label] = []
            by_label[clip.label].append(clip)
        
        return {
            "total_clips": len(processed_clips),
            "by_label": {k: len(v) for k, v in by_label.items()},
            "clips": [c.to_dict() for c in processed_clips],
            "skeleton_paths": [c.skeleton_path for c in processed_clips if c.skeleton_path]
        }
    
    def export_approved_clips(self) -> Dict[str, int]:
        """
        將已核准的片段匯出到訓練資料夾 (優先使用已切割的片段)
        
        Returns:
            匯出統計
        """
        counts = {}
        
        # 訓練資料夾根目錄
        training_data_dir = os.path.join(self.base_dir, "training_data")
        os.makedirs(training_data_dir, exist_ok=True)
        
        # 所有可用的技術類別
        all_techniques = [t.value for t in TechniqueType]
        
        # 為每個技術類別建立資料夾
        for technique in all_techniques:
            folder_path = os.path.join(training_data_dir, technique)
            os.makedirs(folder_path, exist_ok=True)
            counts[technique] = 0
        counts["errors"] = 0
            
        approved_clips = [c for c in self.clips.values() if c.status == "approved"]
        print(f"準備匯出 {len(approved_clips)} 個已核准片段到技術資料夾...")
        
        for clip in approved_clips:
            try:
                # 使用 label 作為技術類別 (現在是 technique_type)
                technique = clip.label
                if technique not in all_techniques:
                    technique = "other"  # 預設
                
                target_folder = os.path.join(training_data_dir, technique)
                target_filename = f"{clip.clip_id}.mp4"
                target_path = os.path.join(target_folder, target_filename)
                
                # 如果目標檔案已存在，跳過
                if os.path.exists(target_path):
                    counts[technique] += 1
                    continue
                
                # 取得來源影片路徑
                source_path = None
                
                # 0. 優先使用已切割的片段 (來自選手分析)
                if hasattr(clip, 'clip_path') and clip.clip_path:
                    # clip_path 格式: /uploads/clips/VIDEO_ID/loss_1.mp4
                    # 需要轉換為完整的本地路徑
                    if clip.clip_path.startswith('/uploads/'):
                        local_clip_path = os.path.join(self.base_dir, clip.clip_path.lstrip('/'))
                    else:
                        local_clip_path = clip.clip_path
                    
                    if os.path.exists(local_clip_path):
                        source_path = local_clip_path
                        print(f"  📁 使用已切割片段: {clip.clip_path}")
                
                # 1. 如果是本地檔案
                if not source_path and clip.source_type == "local" and os.path.exists(clip.source_video):
                    source_path = clip.source_video
                
                # 2. 如果是 YouTube，檢查快取或下載
                if not source_path and clip.source_type == "youtube":
                    # 檢查是否已經下載在 videos_dir
                    cached_path = os.path.join(self.videos_dir, f"{clip.clip_id}.mp4")
                    if os.path.exists(cached_path):
                        source_path = cached_path
                    else:
                        # 下載
                        print(f"  ⬇️ 正在下載片段: {clip.clip_id}")
                        source_path = self.download_and_extract_clip(clip.clip_id)
                
                # 複製檔案
                if source_path and os.path.exists(source_path):
                    shutil.copy2(source_path, target_path)
                    counts[label] += 1
                    print(f"✅ 已匯出: {target_filename} -> {label}")
                else:
                    print(f"❌ 找不到來源檔案: {clip.clip_id}")
                    counts["errors"] += 1
                    
            except Exception as e:
                print(f"❌ 匯出失敗 {clip.clip_id}: {e}")
                counts["errors"] += 1
                
        return counts

    def copy_to_training_folder(self) -> Dict[str, int]:
        """
        將處理完成的資料複製到訓練資料夾
        
        Returns:
            各標籤複製的數量
        """
        counts = {"bad": 0, "good": 0, "normal": 0}
        
        # 訓練資料夾路徑
        folders = {
            "bad": os.path.join(self.base_dir, "bad_input_movid"),
            "good": os.path.join(self.base_dir, "good_input_movid"),
            "normal": os.path.join(self.base_dir, "normal_input_movid"),
        }
        
        for clip in self.clips.values():
            if clip.status != "processed" or not clip.skeleton_path:
                continue
            
            label = clip.label
            if label not in folders:
                continue
            
            # 複製骨架資料
            src_dir = os.path.dirname(clip.skeleton_path)
            dst_dir = os.path.join(folders[label], clip.clip_id)
            
            if os.path.exists(src_dir):
                shutil.copytree(src_dir, dst_dir, dirs_exist_ok=True)
                counts[label] += 1
        
        return counts
    
    def get_statistics(self) -> Dict[str, Any]:
        """取得統計資訊"""
        stats = {
            "total": len(self.clips),
            "by_status": {},
            "by_label": {},
            "by_source": {"youtube": 0, "local": 0},
        }
        
        for clip in self.clips.values():
            # 狀態統計
            if clip.status not in stats["by_status"]:
                stats["by_status"][clip.status] = 0
            stats["by_status"][clip.status] += 1
            
            # 標籤統計
            if clip.label not in stats["by_label"]:
                stats["by_label"][clip.label] = 0
            stats["by_label"][clip.label] += 1
            
            # 來源統計
            stats["by_source"][clip.source_type] += 1
        
        return stats

    def delete_clip(self, clip_id: str) -> bool:
        """刪除單一片段"""
        if clip_id in self.clips:
            del self.clips[clip_id]
            self._save_clips()
            return True
        return False

    def clear_all_clips(self) -> int:
        """清空所有片段"""
        count = len(self.clips)
        self.clips = {}
        self._save_clips()
        return count


# 單例實例
_service_instance = None

def get_auto_training_service() -> AutoTrainingService:
    global _service_instance
    if _service_instance is None:
        _service_instance = AutoTrainingService()
    return _service_instance


if __name__ == "__main__":
    # 測試
    service = AutoTrainingService()
    
    # 模擬 YouTube 分析結果
    mock_analysis = {
        "video_url": "https://www.youtube.com/watch?v=test123",
        "point_losses": [
            {
                "timestamp": "1:23",
                "error_type": "正手失誤",
                "description": "正手拉球出界，動作幅度過大"
            },
            {
                "timestamp": "2:45",
                "error_type": "發球失誤",
                "description": "發球下網，拋球位置不穩定"
            }
        ]
    }
    
    clips = service.import_from_youtube_analysis(mock_analysis)
    print(f"匯入了 {len(clips)} 個片段")
    
    stats = service.get_statistics()
    print(f"統計: {stats}")
