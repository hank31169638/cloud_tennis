"""
分析紀錄服務
管理 YouTube 比賽分析的歷史紀錄
"""
import os
import json
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional
from config import get_config

config = get_config()


class AnalysisRecord:
    """分析紀錄資料類別"""
    
    def __init__(
        self,
        record_id: str,
        video_id: str,
        video_title: str,
        video_url: str,
        video_duration: int,
        thumbnail_url: str,
        player_focus: Optional[str],
        analysis_result: Dict[str, Any],
        created_at: str,
        player2_focus: Optional[str] = None
    ):
        self.record_id = record_id
        self.video_id = video_id
        self.video_title = video_title
        self.video_url = video_url
        self.video_duration = video_duration
        self.thumbnail_url = thumbnail_url
        self.player_focus = player_focus
        self.player2_focus = player2_focus
        self.analysis_result = analysis_result
        self.created_at = created_at
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'record_id': self.record_id,
            'video_id': self.video_id,
            'video_title': self.video_title,
            'video_url': self.video_url,
            'video_duration': self.video_duration,
            'thumbnail_url': self.thumbnail_url,
            'player_focus': self.player_focus,
            'player2_focus': self.player2_focus,
            'analysis_result': self.analysis_result,
            'created_at': self.created_at
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AnalysisRecord':
        return cls(**data)


class AnalysisHistoryService:
    """分析歷史紀錄服務"""
    
    def __init__(self):
        self.records_dir = os.path.join(config.paths.DATA_DIR, 'analysis_records')
        self.index_file = os.path.join(self.records_dir, 'index.json')
        os.makedirs(self.records_dir, exist_ok=True)
        self._ensure_index()
    
    def _ensure_index(self):
        """確保索引檔案存在"""
        if not os.path.exists(self.index_file):
            self._save_index([])
    
    def _load_index(self) -> List[Dict[str, Any]]:
        """載入索引"""
        try:
            with open(self.index_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return []
    
    def _save_index(self, index: List[Dict[str, Any]]):
        """儲存索引"""
        with open(self.index_file, 'w', encoding='utf-8') as f:
            json.dump(index, f, ensure_ascii=False, indent=2)
    
    def save_record(
        self,
        video_info: Dict[str, Any],
        analysis_result: Dict[str, Any],
        player_focus: Optional[str] = None,
        player2_focus: Optional[str] = None
    ) -> str:
        """
        儲存分析紀錄
        
        Args:
            video_info: 影片資訊
            analysis_result: 分析結果
            player_focus: 關注的選手
            player2_focus: 選手2 (可選)
            
        Returns:
            紀錄 ID (若已存在則返回現有 ID)
        """
        video_id = video_info.get('video_id', '')
        
        record_id = str(uuid.uuid4())[:8]
        
        # 重複偵測：檢查是否已有相同 video_id 的紀錄
        existing_record = self.find_by_video_id(video_id)
        if existing_record:
            # 如果已存在，更新現有紀錄
            record_id = existing_record['record_id']
            print(f"⚠️ 影片已分析過: {video_id}, 更新現有紀錄: {record_id}")
            # 為確保更新，我們先刪除舊的（或直接覆蓋檔案）
            # self.delete_record(record_id) # Optional, but overwriting file is enough
        else:
            record_id = str(uuid.uuid4())[:8]
        
        # 建立縮圖 URL
        thumbnail_url = f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"
        
        record = AnalysisRecord(
            record_id=record_id,
            video_id=video_id,
            video_title=video_info.get('title', '未知影片'),
            video_url=video_info.get('url', ''),
            video_duration=video_info.get('duration', 0),
            thumbnail_url=thumbnail_url,
            player_focus=player_focus,
            player2_focus=player2_focus,
            analysis_result=analysis_result,
            created_at=datetime.now().isoformat()
        )
        
        # 儲存完整紀錄
        record_file = os.path.join(self.records_dir, f'{record_id}.json')
        with open(record_file, 'w', encoding='utf-8') as f:
            json.dump(record.to_dict(), f, ensure_ascii=False, indent=2)
        
        # 更新索引（只保存摘要資訊）
        index = self._load_index()
        index_entry = {
            'record_id': record_id,
            'video_id': video_id,
            'video_title': record.video_title,
            'video_url': record.video_url,
            'thumbnail_url': thumbnail_url,
            'player_focus': player_focus,
            'player2_focus': player2_focus,
            'created_at': record.created_at,
            'video_duration': record.video_duration
        }
        index.insert(0, index_entry)  # 最新的放前面
        
        # 只保留最近 100 筆
        index = index[:100]
        self._save_index(index)
        
        return record_id
    
    def get_record(self, record_id: str) -> Optional[Dict[str, Any]]:
        """
        取得單一分析紀錄
        
        Args:
            record_id: 紀錄 ID
            
        Returns:
            完整的分析紀錄
        """
        record_file = os.path.join(self.records_dir, f'{record_id}.json')
        
        if not os.path.exists(record_file):
            return None
        
        try:
            with open(record_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return None
    
    def get_all_records(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        取得所有分析紀錄（摘要）
        
        Args:
            limit: 最大筆數
            
        Returns:
            紀錄摘要列表
        """
        index = self._load_index()
        return index[:limit]
    
    def delete_record(self, record_id: str) -> bool:
        """
        刪除分析紀錄
        
        Args:
            record_id: 紀錄 ID
            
        Returns:
            是否成功刪除
        """
        record_file = os.path.join(self.records_dir, f'{record_id}.json')
        
        # 刪除檔案
        if os.path.exists(record_file):
            os.remove(record_file)
        
        # 更新索引
        index = self._load_index()
        index = [r for r in index if r['record_id'] != record_id]
        self._save_index(index)
        
        return True
    
    def search_records(self, query: str) -> List[Dict[str, Any]]:
        """
        搜尋分析紀錄
        
        Args:
            query: 搜尋關鍵字
            
        Returns:
            符合的紀錄列表
        """
        index = self._load_index()
        query_lower = query.lower()
        
        results = []
        for record in index:
            if (query_lower in record.get('video_title', '').lower() or
                query_lower in (record.get('player_focus') or '').lower()):
                results.append(record)
        
        return results

    def find_by_video_id(self, video_id: str) -> Optional[Dict[str, Any]]:
        """
        根據 video_id 查找紀錄
        
        Args:
            video_id: YouTube 影片 ID
            
        Returns:
            找到的紀錄摘要，或 None
        """
        if not video_id:
            return None
            
        index = self._load_index()
        for record in index:
            if record.get('video_id') == video_id:
                return record
        return None
