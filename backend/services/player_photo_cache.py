"""
選手頭像快取服務
儲存已驗證的選手頭像 URL
"""
import os
import json
from typing import Dict, Any, Optional
from config import get_config

config = get_config()


class PlayerPhotoCache:
    """選手頭像快取"""
    
    def __init__(self):
        self.cache_file = os.path.join(config.paths.DATA_DIR, 'player_photos_cache.json')
        self._ensure_cache()
    
    def _ensure_cache(self):
        """確保快取檔案存在"""
        if not os.path.exists(self.cache_file):
            self._save_cache({})
    
    def _load_cache(self) -> Dict[str, Any]:
        """載入快取"""
        try:
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    
    def _save_cache(self, cache: Dict[str, Any]):
        """儲存快取"""
        with open(self.cache_file, 'w', encoding='utf-8') as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
    
    def save_validated_photo(self, ittf_id: str, photo_url: str, player_name: str = None) -> bool:
        """
        儲存已驗證的選手頭像 URL
        
        Args:
            ittf_id: ITTF 選手 ID
            photo_url: 已驗證可用的頭像 URL
            player_name: 選手名稱（可選）
            
        Returns:
            是否儲存成功
        """
        if not ittf_id or not photo_url:
            return False
        
        cache = self._load_cache()
        cache[ittf_id] = {
            'photo_url': photo_url,
            'player_name': player_name,
            'validated': True
        }
        self._save_cache(cache)
        print(f"✅ 已儲存選手頭像: {ittf_id} -> {photo_url}")
        return True
    
    def get_validated_photo(self, ittf_id: str) -> Optional[str]:
        """
        取得已驗證的選手頭像 URL
        
        Args:
            ittf_id: ITTF 選手 ID
            
        Returns:
            頭像 URL 或 None
        """
        if not ittf_id:
            return None
        
        cache = self._load_cache()
        entry = cache.get(ittf_id)
        return entry.get('photo_url') if entry else None
    
    def get_all_cached_photos(self) -> Dict[str, Any]:
        """取得所有快取的頭像"""
        return self._load_cache()


# 單例模式
_photo_cache = None

def get_photo_cache() -> PlayerPhotoCache:
    global _photo_cache
    if _photo_cache is None:
        _photo_cache = PlayerPhotoCache()
    return _photo_cache
