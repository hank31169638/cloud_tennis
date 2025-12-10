"""
動作標準預測服務
使用 user_movid_predict.py 中的模型來預測動作是否標準
"""
import os
import sys
from typing import Dict, Optional, Any

# 確保可以導入 user_movid_predict
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class ActionPredictionService:
    """動作標準預測服務類別"""
    
    def __init__(self, model_path: str = 'table_tennis_model.pth'):
        """
        初始化服務
        
        Args:
            model_path: 模型檔案路徑（相對於 backend 目錄）
        """
        self.model_path = model_path
        self._model = None
        # 獲取 backend 目錄路徑
        self._base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        # 構建完整的模型路徑
        if os.path.isabs(model_path):
            self._model_full_path = model_path
        else:
            self._model_full_path = os.path.join(self._base_dir, model_path)
    
    def _get_model(self):
        """延遲載入模型（單例模式）"""
        if self._model is None:
            # 確保可以導入 user_movid_predict（從 backend 目錄）
            import sys
            backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            if backend_dir not in sys.path:
                sys.path.insert(0, backend_dir)
            
            from user_movid_predict import load_model
            
            # 檢查模型文件是否存在
            if not os.path.exists(self._model_full_path):
                raise FileNotFoundError(
                    f'找不到模型檔案: {self._model_full_path}\n'
                    f'請確認模型檔案位於 backend 目錄下'
                )
            
            self._model = load_model(self._model_full_path)
        return self._model
    
    def predict(self, video_path: str) -> Optional[Dict[str, Any]]:
        """
        預測影片中的動作是否標準
        
        Args:
            video_path: 影片路徑
            
        Returns:
            預測結果字典，包含：
            - prediction: 預測結果 ('標準' 或 '不標準')
            - confidence: 信心度 (0-1)
            - probabilities: 各類別機率字典
        """
        try:
            model = self._get_model()
            from user_movid_predict import predict_video
            
            result, confidence, probabilities = predict_video(model, video_path)
            
            return {
                'prediction': result,
                'confidence': float(confidence),
                'probabilities': {
                    '不標準': float(probabilities[0]),
                    '標準': float(probabilities[1])
                }
            }
        except Exception as e:
            print(f"預測時發生錯誤: {str(e)}")
            import traceback
            traceback.print_exc()
            return None

