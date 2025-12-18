"""
增強版預測服務
支援多種模型（R3D 和 LSTM）和多種分類模式（簡單/技術）
"""
import os
import json
import numpy as np
from typing import Dict, Any, Optional, Tuple, List
import joblib

# 延遲載入深度學習框架
_tf_loaded = False
_torch_loaded = False


def _load_tensorflow():
    """延遲載入 TensorFlow"""
    global _tf_loaded
    if not _tf_loaded:
        import tensorflow as tf
        _tf_loaded = True
    import tensorflow as tf
    return tf


def _load_torch():
    """延遲載入 PyTorch"""
    global _torch_loaded
    if not _torch_loaded:
        import torch
        _torch_loaded = True
    import torch
    return torch


class EnhancedPredictionService:
    """增強版預測服務"""
    
    # 簡單分類標籤
    SIMPLE_CLASS_NAMES = {
        0: {'en': 'good', 'zh': '得分/標準'},
        1: {'en': 'normal', 'zh': '一般'},
        2: {'en': 'bad', 'zh': '失誤/不標準'}
    }
    
    # 技術分類標籤
    TECHNIQUE_CLASS_NAMES = {
        'forehand_attack': '正手進攻', 'backhand_attack': '反手進攻',
        'smash': '扣殺', 'loop_drive': '弧圈球',
        'block': '擋球', 'chop': '削球', 'lob': '挑球',
        'serve_ace': '發球直接得分', 'serve_attack': '發球搶攻',
        'receive_attack': '接發搶攻', 'receive_control': '接發控制',
        'forehand_error': '正手失誤', 'backhand_error': '反手失誤',
        'serve_error': '發球失誤', 'receive_error': '接發失誤',
        'net_error': '下網', 'out_of_bounds': '出界',
        'footwork_error': '步法失誤', 'judgment_error': '判斷失誤',
        'other': '其他'
    }
    
    def __init__(self):
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.models_dir = os.path.join(self.base_dir, 'models')
        
        # 模型緩存
        self._lstm_models = {}
        self._r3d_model = None
        self._pose_extractor = None
    
    @property
    def pose_extractor(self):
        """延遲載入骨架提取器"""
        if self._pose_extractor is None:
            try:
                from skeleton import PoseExtractor
                self._pose_extractor = PoseExtractor()
            except ImportError:
                print("警告：無法載入 PoseExtractor")
        return self._pose_extractor
    
    def get_available_models(self) -> Dict[str, Any]:
        """取得可用模型列表"""
        models = {
            'simple': None,
            'technique': None,
            'r3d': os.path.exists(os.path.join(self.base_dir, 'table_tennis_model.pth'))
        }
        
        # 檢查 LSTM 模型
        for mode in ['simple', 'technique']:
            config_path = os.path.join(self.models_dir, f'latest_{mode}_config.json')
            model_path = os.path.join(self.models_dir, f'latest_{mode}.h5')
            
            if os.path.exists(model_path) and os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                models[mode] = {
                    'path': model_path,
                    'config': config,
                    'accuracy': config.get('accuracy', 0)
                }
        
        return models
    
    def _load_lstm_model(self, mode: str) -> Tuple[Any, Any, Dict]:
        """載入 LSTM 模型"""
        if mode in self._lstm_models:
            return self._lstm_models[mode]
        
        model_path = os.path.join(self.models_dir, f'latest_{mode}.h5')
        scaler_path = os.path.join(self.models_dir, f'latest_{mode}_scaler.pkl')
        config_path = os.path.join(self.models_dir, f'latest_{mode}_config.json')
        
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"找不到 {mode} 模型")
        
        tf = _load_tensorflow()
        model = tf.keras.models.load_model(model_path)
        scaler = joblib.load(scaler_path) if os.path.exists(scaler_path) else None
        
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        self._lstm_models[mode] = (model, scaler, config)
        return self._lstm_models[mode]
    
    def _load_r3d_model(self):
        """載入 R3D 模型"""
        if self._r3d_model is not None:
            return self._r3d_model
        
        torch = _load_torch()
        import torch.nn as nn
        from torchvision.models.video import r3d_18, R3D_18_Weights
        
        device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        model_path = os.path.join(self.base_dir, 'table_tennis_model.pth')
        
        if not os.path.exists(model_path):
            raise FileNotFoundError("找不到 R3D 模型")
        
        model = r3d_18(weights=R3D_18_Weights.KINETICS400_V1)
        num_features = model.fc.in_features
        model.fc = nn.Linear(num_features, 2)
        
        try:
            state_dict = torch.load(model_path, map_location=device, weights_only=False)
        except TypeError:
            state_dict = torch.load(model_path, map_location=device)
        
        model.load_state_dict(state_dict)
        model = model.to(device)
        model.eval()
        
        self._r3d_model = (model, device)
        return self._r3d_model
    
    def _extract_skeleton_features(self, video_path: str) -> Optional[np.ndarray]:
        """從影片提取骨架特徵"""
        if self.pose_extractor is None:
            return None
        
        try:
            pose_data = self.pose_extractor.extract_pose_data(video_path)
            
            if pose_data is None or len(pose_data) == 0:
                return None
            
            # 轉換為數值陣列
            landmarks_array = []
            for frame_data in pose_data:
                if frame_data['landmarks'] is not None:
                    frame_landmarks = []
                    for lm in frame_data['landmarks']:
                        frame_landmarks.extend([lm['x'], lm['y'], lm['z']])
                    landmarks_array.append(frame_landmarks)
            
            if len(landmarks_array) == 0:
                return None
            
            landmarks_array = np.array(landmarks_array)
            
            # 標準化為 150 幀
            target_frames = 150
            target_features = landmarks_array.shape[1]
            
            if landmarks_array.shape[0] != target_frames:
                resampled = np.zeros((target_frames, target_features))
                original_frames = landmarks_array.shape[0]
                
                for feature_idx in range(target_features):
                    resampled[:, feature_idx] = np.interp(
                        np.linspace(0, original_frames - 1, target_frames),
                        np.arange(original_frames),
                        landmarks_array[:, feature_idx]
                    )
                landmarks_array = resampled
            
            return landmarks_array
            
        except Exception as e:
            print(f"骨架提取失敗: {e}")
            return None
    
    def predict_with_lstm(
        self,
        video_path: str,
        mode: str = 'simple'
    ) -> Dict[str, Any]:
        """
        使用 LSTM 模型預測
        
        Args:
            video_path: 影片路徑
            mode: 'simple' 或 'technique'
        
        Returns:
            預測結果
        """
        # 載入模型
        model, scaler, config = self._load_lstm_model(mode)
        class_names = config.get('class_names', [])
        
        # 提取特徵
        features = self._extract_skeleton_features(video_path)
        if features is None:
            return {
                'success': False,
                'error': '無法從影片提取骨架特徵'
            }
        
        # 標準化
        if scaler is not None:
            input_shape = features.shape
            features = scaler.transform(features.reshape(-1, input_shape[1])).reshape(1, input_shape[0], input_shape[1])
        else:
            features = features.reshape(1, features.shape[0], features.shape[1])
        
        # 預測
        predictions = model.predict(features, verbose=0)
        predicted_class = np.argmax(predictions[0])
        confidence = float(predictions[0][predicted_class])
        
        # 構建結果
        class_name = class_names[predicted_class] if predicted_class < len(class_names) else 'unknown'
        
        if mode == 'simple':
            display_name = self.SIMPLE_CLASS_NAMES.get(predicted_class, {}).get('zh', class_name)
        else:
            display_name = self.TECHNIQUE_CLASS_NAMES.get(class_name, class_name)
        
        # 所有類別的機率
        all_probabilities = {}
        for i, prob in enumerate(predictions[0]):
            cn = class_names[i] if i < len(class_names) else f'class_{i}'
            if mode == 'simple':
                dn = self.SIMPLE_CLASS_NAMES.get(i, {}).get('zh', cn)
            else:
                dn = self.TECHNIQUE_CLASS_NAMES.get(cn, cn)
            all_probabilities[dn] = float(prob)
        
        return {
            'success': True,
            'model_type': 'lstm',
            'mode': mode,
            'predicted_class': class_name,
            'display_name': display_name,
            'confidence': confidence,
            'probabilities': all_probabilities
        }
    
    def predict_with_r3d(self, video_path: str) -> Dict[str, Any]:
        """
        使用 R3D 模型預測 (二分類: 標準/不標準)
        
        Args:
            video_path: 影片路徑
        
        Returns:
            預測結果
        """
        import cv2
        torch = _load_torch()
        
        model, device = self._load_r3d_model()
        
        # 載入影片
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return {
                'success': False,
                'error': f'無法開啟影片: {video_path}'
            }
        
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        num_frames = 16
        
        # 計算採樣索引
        if total_frames <= num_frames:
            frame_indices = list(range(total_frames))
            while len(frame_indices) < num_frames:
                frame_indices.append(frame_indices[-1] if frame_indices else 0)
        else:
            frame_indices = np.linspace(0, total_frames - 1, num_frames, dtype=int)
        
        frames = []
        frame_idx = 0
        
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            
            if frame_idx in frame_indices:
                frame = cv2.resize(frame, (112, 112))
                frames.append(frame)
            
            frame_idx += 1
            
            if len(frames) >= num_frames:
                break
        
        cap.release()
        
        # 填充
        while len(frames) < num_frames:
            frames.append(frames[-1] if frames else np.zeros((112, 112, 3), dtype=np.uint8))
        
        frames = np.array(frames[:num_frames])
        
        # 轉換為 tensor
        frames_tensor = torch.FloatTensor(frames)
        frames_tensor = frames_tensor.permute(3, 0, 1, 2)  # (T, H, W, C) -> (C, T, H, W)
        frames_tensor = frames_tensor / 255.0
        frames_tensor = frames_tensor.unsqueeze(0).to(device)
        
        # 預測
        with torch.no_grad():
            outputs = model(frames_tensor)
            probabilities = torch.nn.functional.softmax(outputs, dim=1)
            predicted_class = torch.argmax(outputs, dim=1).item()
            confidence = probabilities[0][predicted_class].item()
        
        class_names = ['不標準', '標準']
        
        return {
            'success': True,
            'model_type': 'r3d',
            'mode': 'binary',
            'predicted_class': 'good' if predicted_class == 1 else 'bad',
            'display_name': class_names[predicted_class],
            'confidence': confidence,
            'probabilities': {
                '不標準': float(probabilities[0][0].item()),
                '標準': float(probabilities[0][1].item())
            }
        }
    
    def predict(
        self,
        video_path: str,
        model_type: str = 'auto',
        mode: str = 'simple'
    ) -> Dict[str, Any]:
        """
        統一預測介面
        
        Args:
            video_path: 影片路徑
            model_type: 'lstm', 'r3d', 或 'auto' (自動選擇最佳模型)
            mode: 'simple' 或 'technique' (僅用於 LSTM)
        
        Returns:
            預測結果
        """
        if not os.path.exists(video_path):
            return {
                'success': False,
                'error': f'影片不存在: {video_path}'
            }
        
        available = self.get_available_models()
        
        # 自動選擇模型
        if model_type == 'auto':
            if mode == 'technique' and available.get('technique'):
                model_type = 'lstm'
            elif available.get('simple'):
                model_type = 'lstm'
            elif available.get('r3d'):
                model_type = 'r3d'
            else:
                return {
                    'success': False,
                    'error': '沒有可用的模型，請先訓練模型'
                }
        
        try:
            if model_type == 'lstm':
                return self.predict_with_lstm(video_path, mode)
            elif model_type == 'r3d':
                return self.predict_with_r3d(video_path)
            else:
                return {
                    'success': False,
                    'error': f'未知的模型類型: {model_type}'
                }
        except Exception as e:
            import traceback
            return {
                'success': False,
                'error': str(e),
                'traceback': traceback.format_exc()
            }
    
    def batch_predict(
        self,
        video_paths: List[str],
        model_type: str = 'auto',
        mode: str = 'simple'
    ) -> List[Dict[str, Any]]:
        """批量預測"""
        results = []
        for path in video_paths:
            result = self.predict(path, model_type, mode)
            result['video_path'] = path
            results.append(result)
        return results


# 單例
_enhanced_service = None


def get_enhanced_prediction_service() -> EnhancedPredictionService:
    global _enhanced_service
    if _enhanced_service is None:
        _enhanced_service = EnhancedPredictionService()
    return _enhanced_service
