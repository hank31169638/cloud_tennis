"""
選手檔案服務
儲存並管理選手分析數據，支援多場比賽評分累積
"""
import os
import json
from datetime import datetime
from typing import Dict, Any, List, Optional
from config import get_config

config = get_config()


class PlayerProfileService:
    """選手檔案服務"""
    
    def __init__(self):
        self.profiles_dir = os.path.join(config.paths.DATA_DIR, 'player_profiles')
        self.index_file = os.path.join(self.profiles_dir, 'index.json')
        os.makedirs(self.profiles_dir, exist_ok=True)
        self._ensure_index()
    
    def _ensure_index(self):
        """確保索引檔案存在"""
        if not os.path.exists(self.index_file):
            self._save_index({})
    
    def _load_index(self) -> Dict[str, Any]:
        """載入索引"""
        try:
            with open(self.index_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    
    def _save_index(self, index: Dict[str, Any]):
        """儲存索引"""
        with open(self.index_file, 'w', encoding='utf-8') as f:
            json.dump(index, f, ensure_ascii=False, indent=2)
    
    def _normalize_name(self, name: str) -> str:
        """正規化選手名稱作為 ID"""
        # 去除空格、轉小寫，作為 key
        return name.strip().lower().replace(' ', '_')
    
    def _get_profile_path(self, player_id: str) -> str:
        """取得選手檔案路徑"""
        return os.path.join(self.profiles_dir, f'{player_id}.json')
    
    def save_player_analysis(
        self,
        player_name: str,
        match_id: str,
        video_id: str,
        opponent_name: str,
        ratings: Dict[str, float],
        strengths: List[Any] = None,
        weaknesses: List[Any] = None,
        result: str = "未知"
    ) -> str:
        """
        儲存選手分析結果
        
        Args:
            player_name: 選手名稱
            match_id: 比賽紀錄 ID
            video_id: YouTube 影片 ID
            opponent_name: 對手名稱
            ratings: 五維評分
            strengths: 優勢列表
            weaknesses: 待改善列表
            result: 比賽結果 (勝/負/未知)
            
        Returns:
            選手 ID
        """
        player_id = self._normalize_name(player_name)
        profile_path = self._get_profile_path(player_id)
        
        # 載入或建立 profile
        if os.path.exists(profile_path):
            with open(profile_path, 'r', encoding='utf-8') as f:
                profile = json.load(f)
        else:
            # 嘗試從世界排名資料庫取得選手頭像
            avatar_url = None
            ittf_player = None
            try:
                from services.player_service import get_player_service
                player_service = get_player_service()
                ittf_player = player_service.find_player_by_name(player_name)
                if ittf_player:
                    # 優先使用快取的已驗證頭像
                    try:
                        from services.player_photo_cache import get_photo_cache
                        photo_cache = get_photo_cache()
                        cached_url = photo_cache.get_validated_photo(ittf_player.get('id'))
                        if cached_url:
                            avatar_url = cached_url
                            print(f"📸 使用快取頭像: {ittf_player.get('name')}")
                        else:
                            avatar_url = ittf_player.get('photo_url')
                    except:
                        avatar_url = ittf_player.get('photo_url')
                    
                    print(f"🎯 找到世界排名選手: {ittf_player.get('name')} (ITTF ID: {ittf_player.get('id')})")
            except Exception as e:
                print(f"⚠️ 無法從排名資料庫取得選手資料: {e}")
            
            profile = {
                'player_id': player_id,
                'display_name': player_name,
                'aliases': [],
                'avatar_url': avatar_url,
                'ittf_id': ittf_player.get('id') if ittf_player else None,
                'ittf_name': ittf_player.get('name') if ittf_player else None,
                'country': ittf_player.get('country') if ittf_player else None,
                'country_code': ittf_player.get('country_code') if ittf_player else None,
                'world_ranking': ittf_player.get('rankings') if ittf_player else None,
                'aggregate_ratings': {},
                'match_history': [],
                'total_matches': 0,
                'created_at': datetime.now().isoformat(),
                'last_updated': datetime.now().isoformat()
            }
        
        # 檢查是否已有相同 video_id 的紀錄（避免重複）
        existing_match = next(
            (m for m in profile['match_history'] if m.get('video_id') == video_id),
            None
        )
        
        if existing_match:
            # 更新現有紀錄
            existing_match['ratings'] = ratings
            existing_match['strengths'] = strengths or []
            existing_match['weaknesses'] = weaknesses or []
            existing_match['result'] = result
            existing_match['updated_at'] = datetime.now().isoformat()
        else:
            # 新增比賽紀錄
            match_record = {
                'match_id': match_id,
                'video_id': video_id,
                'opponent': opponent_name,
                'date': datetime.now().strftime('%Y-%m-%d'),
                'result': result,
                'ratings': ratings,
                'strengths': strengths or [],
                'weaknesses': weaknesses or [],
                'created_at': datetime.now().isoformat()
            }
            profile['match_history'].insert(0, match_record)
            profile['total_matches'] = len(profile['match_history'])
        
        # 重新計算累積評分
        profile['aggregate_ratings'] = self._calculate_aggregate_ratings(profile['match_history'])
        profile['last_updated'] = datetime.now().isoformat()
        
        # 儲存 profile
        with open(profile_path, 'w', encoding='utf-8') as f:
            json.dump(profile, f, ensure_ascii=False, indent=2)
        
        # 更新索引
        index = self._load_index()
        index[player_id] = {
            'player_id': player_id,
            'display_name': player_name,
            'total_matches': profile['total_matches'],
            'last_updated': profile['last_updated'],
            'aggregate_ratings': profile['aggregate_ratings']
        }
        self._save_index(index)
        
        return player_id
    
    def _calculate_aggregate_ratings(self, match_history: List[Dict]) -> Dict[str, float]:
        """計算多場比賽的平均評分"""
        if not match_history:
            return {}
        
        rating_keys = ['serve', 'receive', 'attack', 'defense', 'tactics']
        totals = {key: 0.0 for key in rating_keys}
        counts = {key: 0 for key in rating_keys}
        
        for match in match_history:
            ratings = match.get('ratings', {})
            for key in rating_keys:
                if key in ratings and ratings[key] is not None:
                    try:
                        totals[key] += float(ratings[key])
                        counts[key] += 1
                    except (ValueError, TypeError):
                        pass
        
        aggregate = {}
        for key in rating_keys:
            if counts[key] > 0:
                aggregate[key] = round(totals[key] / counts[key], 1)
        
        return aggregate
    
    def get_player_profile(self, player_name: str) -> Optional[Dict[str, Any]]:
        """
        取得選手檔案
        
        Args:
            player_name: 選手名稱
            
        Returns:
            選手檔案資料
        """
        player_id = self._normalize_name(player_name)
        profile_path = self._get_profile_path(player_id)
        
        if not os.path.exists(profile_path):
            return None
        
        try:
            with open(profile_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return None
    
    def get_all_player_profiles(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        取得所有選手檔案摘要
        
        Args:
            limit: 最大筆數
            
        Returns:
            選手檔案摘要列表
        """
        index = self._load_index()
        
        # 按最近更新排序
        profiles = sorted(
            index.values(),
            key=lambda x: x.get('last_updated', ''),
            reverse=True
        )
        
        return profiles[:limit]
    
    def search_players(self, query: str) -> List[Dict[str, Any]]:
        """
        搜尋選手
        
        Args:
            query: 搜尋關鍵字
            
        Returns:
            符合的選手列表
        """
        index = self._load_index()
        query_lower = query.lower()
        
        results = []
        for player_id, profile in index.items():
            if (query_lower in player_id or 
                query_lower in profile.get('display_name', '').lower()):
                results.append(profile)
        
        return results


# 單例模式
_player_profile_service = None

def get_player_profile_service() -> PlayerProfileService:
    global _player_profile_service
    if _player_profile_service is None:
        _player_profile_service = PlayerProfileService()
    return _player_profile_service
