"""
統一訓練服務
整合多種訓練模式：簡單分類 (Good/Bad/Normal) 和技術分類 (20種技術類型)
支援增量訓練、模型版本控制、訓練數據統計等功能
"""
import os
import glob
import json
import shutil
import numpy as np
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple, TYPE_CHECKING
from dataclasses import dataclass, asdict
from enum import Enum

# 延遲導入的模組
_tf = None
_joblib = None


def _get_tensorflow():
    """延遲載入 TensorFlow"""
    global _tf
    if _tf is None:
        import tensorflow as tf
        _tf = tf
    return _tf


def _get_joblib():
    """延遲載入 joblib"""
    global _joblib
    if _joblib is None:
        import joblib
        _joblib = joblib
    return _joblib


def _get_sklearn():
    """延遲載入 sklearn 模組"""
    from sklearn.model_selection import train_test_split
    from sklearn.preprocessing import StandardScaler
    from sklearn.utils.class_weight import compute_class_weight
    return train_test_split, StandardScaler, compute_class_weight


class TrainingMode(Enum):
    """訓練模式"""
    SIMPLE = "simple"           # Good / Bad / Normal 三分類
    TECHNIQUE = "technique"      # 20 種技術類型分類


class ModelArchitecture(Enum):
    """模型架構"""
    BASIC = "basic"
    BIDIRECTIONAL = "bidirectional"
    DEEP = "deep"
    ADVANCED = "advanced"


@dataclass
class TrainingConfig:
    """訓練配置"""
    mode: str = "simple"
    architecture: str = "basic"
    epochs: int = 100
    batch_size: int = 32
    learning_rate: float = 0.001
    use_augmentation: bool = True
    augment_factor: int = 3
    early_stop_patience: int = 15
    use_class_weights: bool = True
    min_samples_per_class: int = 5
    test_size: float = 0.2
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class TrainingResult:
    """訓練結果"""
    success: bool
    model_path: str
    accuracy: float
    val_accuracy: float
    loss: float
    val_loss: float
    training_time: str
    total_samples: int
    num_classes: int
    class_names: List[str]
    confusion_matrix: Optional[List[List[int]]] = None
    per_class_accuracy: Optional[Dict[str, float]] = None
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _create_progress_callback_class():
    """動態創建進度回調類（延遲載入 Keras）"""
    tf = _get_tensorflow()
    
    class TrainingProgressCallback(tf.keras.callbacks.Callback):
        """訓練進度回調"""
        
        def __init__(self, task_id: str, task_storage: Dict, total_epochs: int):
            super().__init__()
            self.task_id = task_id
            self.task_storage = task_storage
            self.total_epochs = total_epochs
        
        def on_epoch_end(self, epoch, logs=None):
            logs = logs or {}
            
            self.task_storage[self.task_id].update({
                'current_epoch': epoch + 1,
                'accuracy': float(logs.get('accuracy', 0)),
                'val_accuracy': float(logs.get('val_accuracy', 0)),
                'loss': float(logs.get('loss', 0)),
                'val_loss': float(logs.get('val_loss', 0)),
                'message': f'訓練中... Epoch {epoch + 1}/{self.total_epochs}'
            })
            
            log_msg = f"Epoch {epoch + 1}/{self.total_epochs} - acc: {logs.get('accuracy', 0):.4f} - val_acc: {logs.get('val_accuracy', 0):.4f}"
            if 'logs' not in self.task_storage[self.task_id]:
                self.task_storage[self.task_id]['logs'] = []
            self.task_storage[self.task_id]['logs'].append(log_msg)
    
    return TrainingProgressCallback


class UnifiedTrainingService:
    """統一訓練服務"""
    
    # 簡單分類標籤
    SIMPLE_CLASSES = ['good', 'normal', 'bad']
    SIMPLE_CLASS_NAMES = {'good': '得分', 'normal': '一般', 'bad': '失誤'}
    
    # 技術分類標籤 (按類別分組)
    TECHNIQUE_CLASSES = [
        # 攻擊技術
        'forehand_attack', 'backhand_attack', 'smash', 'loop_drive',
        # 防守技術  
        'block', 'chop', 'lob',
        # 發球接發
        'serve_ace', 'serve_attack', 'receive_attack', 'receive_control',
        # 失誤類型
        'forehand_error', 'backhand_error', 'serve_error', 'receive_error',
        'net_error', 'out_of_bounds', 'footwork_error', 'judgment_error',
        # 其他
        'other'
    ]
    
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
        self.training_data_dir = os.path.join(self.base_dir, 'training_data')
        self.simple_data_dirs = {
            'good': os.path.join(self.base_dir, 'good_input_movid'),
            'normal': os.path.join(self.base_dir, 'normal_input_movid'),
            'bad': os.path.join(self.base_dir, 'bad_input_movid'),
        }
        
        # 確保目錄存在
        os.makedirs(self.models_dir, exist_ok=True)
        os.makedirs(self.training_data_dir, exist_ok=True)
        
        # 初始化骨架提取器 (延遲載入)
        self._pose_extractor = None
    
    @property
    def pose_extractor(self):
        """延遲載入骨架提取器"""
        if self._pose_extractor is None:
            try:
                from skeleton import PoseExtractor
                self._pose_extractor = PoseExtractor()
            except ImportError:
                print("警告：無法載入 PoseExtractor，將無法處理新影片")
        return self._pose_extractor
    
    # ==================== 數據統計 ====================
    
    def get_training_data_stats(self) -> Dict[str, Any]:
        """取得訓練數據統計"""
        stats = {
            'simple': {
                'total': 0,
                'by_class': {},
                'ready_for_training': False
            },
            'technique': {
                'total': 0,
                'by_class': {},
                'ready_for_training': False
            }
        }
        
        # 統計簡單分類
        for class_name, folder in self.simple_data_dirs.items():
            if os.path.exists(folder):
                videos = self._get_video_files(folder)
                count = len(videos)
                stats['simple']['by_class'][class_name] = count
                stats['simple']['total'] += count
        
        stats['simple']['ready_for_training'] = all(
            stats['simple']['by_class'].get(c, 0) >= 5 for c in self.SIMPLE_CLASSES
        )
        
        # 統計技術分類
        for class_name in self.TECHNIQUE_CLASSES:
            folder = os.path.join(self.training_data_dir, class_name)
            if os.path.exists(folder):
                videos = self._get_video_files(folder)
                count = len(videos)
                if count > 0:
                    stats['technique']['by_class'][class_name] = count
                    stats['technique']['total'] += count
        
        # 至少需要 3 個類別，每個類別至少 5 個樣本
        valid_classes = sum(1 for c in stats['technique']['by_class'].values() if c >= 5)
        stats['technique']['ready_for_training'] = valid_classes >= 3
        
        return stats
    
    def _get_video_files(self, folder: str) -> List[str]:
        """取得資料夾中的影片檔案"""
        if not os.path.exists(folder):
            return []
        
        extensions = ['*.mp4', '*.avi', '*.MOV', '*.mov', '*.mkv']
        videos = []
        for ext in extensions:
            videos.extend(glob.glob(os.path.join(folder, ext)))
        return videos
    
    # ==================== 數據載入 ====================
    
    def load_simple_training_data(self) -> Tuple[np.ndarray, np.ndarray, List[str]]:
        """載入簡單分類訓練數據"""
        X_data = []
        y_data = []
        class_names = self.SIMPLE_CLASSES
        
        for class_idx, class_name in enumerate(class_names):
            folder = self.simple_data_dirs.get(class_name)
            if not folder or not os.path.exists(folder):
                continue
            
            videos = self._get_video_files(folder)
            print(f"載入 {class_name} 類別：{len(videos)} 個影片")
            
            for video_path in videos:
                features = self._extract_features(video_path)
                if features is not None:
                    X_data.append(features)
                    y_data.append(class_idx)
        
        if len(X_data) == 0:
            raise ValueError("未找到任何訓練數據")
        
        return np.array(X_data), np.array(y_data), class_names
    
    def load_technique_training_data(self) -> Tuple[np.ndarray, np.ndarray, List[str]]:
        """載入技術分類訓練數據"""
        X_data = []
        y_data = []
        
        # 只載入有足夠樣本的類別
        available_classes = []
        class_counts = {}
        
        for class_name in self.TECHNIQUE_CLASSES:
            folder = os.path.join(self.training_data_dir, class_name)
            videos = self._get_video_files(folder)
            if len(videos) >= 3:  # 至少 3 個樣本
                available_classes.append(class_name)
                class_counts[class_name] = len(videos)
        
        if len(available_classes) < 2:
            raise ValueError(f"可用類別不足，需要至少 2 個類別，目前只有 {len(available_classes)} 個")
        
        print(f"可用技術類別：{len(available_classes)} 個")
        
        for class_idx, class_name in enumerate(available_classes):
            folder = os.path.join(self.training_data_dir, class_name)
            videos = self._get_video_files(folder)
            print(f"載入 {class_name}：{len(videos)} 個影片")
            
            for video_path in videos:
                features = self._extract_features(video_path)
                if features is not None:
                    X_data.append(features)
                    y_data.append(class_idx)
        
        return np.array(X_data), np.array(y_data), available_classes
    
    def _extract_features(self, video_path: str) -> Optional[np.ndarray]:
        """從影片提取骨架特徵"""
        try:
            if self.pose_extractor is None:
                return None
            
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
            print(f"特徵提取失敗 {video_path}: {e}")
            return None
    
    # ==================== 數據增強 ====================
    
    def augment_data(self, X: np.ndarray, y: np.ndarray, factor: int = 3) -> Tuple[np.ndarray, np.ndarray]:
        """數據增強"""
        aug_X = [X]
        aug_y = [y]
        
        for _ in range(factor):
            augmented = []
            for seq in X:
                aug_seq = seq.copy()
                
                # 時間軸縮放
                if np.random.rand() > 0.5:
                    aug_seq = self._temporal_scaling(aug_seq)
                
                # 添加噪聲
                if np.random.rand() > 0.5:
                    aug_seq = self._add_noise(aug_seq)
                
                # 隨機裁剪
                if np.random.rand() > 0.3:
                    aug_seq = self._random_crop(aug_seq)
                
                augmented.append(aug_seq)
            
            aug_X.append(np.array(augmented))
            aug_y.append(y.copy())
        
        return np.concatenate(aug_X), np.concatenate(aug_y)
    
    def _temporal_scaling(self, sequence: np.ndarray, scale_factor: float = 0.2) -> np.ndarray:
        """時間軸縮放"""
        scale = np.random.uniform(1 - scale_factor, 1 + scale_factor)
        original_length = len(sequence)
        indices = np.linspace(0, original_length - 1, int(original_length * scale))
        
        scaled = np.zeros((len(indices), sequence.shape[1]))
        for col in range(sequence.shape[1]):
            scaled[:, col] = np.interp(indices, np.arange(original_length), sequence[:, col])
        
        # 重新採樣回原長度
        final = np.zeros_like(sequence)
        for col in range(sequence.shape[1]):
            final[:, col] = np.interp(
                np.linspace(0, len(scaled) - 1, original_length),
                np.arange(len(scaled)),
                scaled[:, col]
            )
        
        return final
    
    def _add_noise(self, sequence: np.ndarray, noise_level: float = 0.01) -> np.ndarray:
        """添加噪聲"""
        noise = np.random.normal(0, noise_level, sequence.shape)
        return sequence + noise
    
    def _random_crop(self, sequence: np.ndarray, crop_ratio: float = 0.1) -> np.ndarray:
        """隨機裁剪"""
        crop_length = int(len(sequence) * (1 - crop_ratio))
        start_idx = np.random.randint(0, max(1, len(sequence) - crop_length))
        cropped = sequence[start_idx:start_idx + crop_length]
        
        # 重新採樣回原長度
        result = np.zeros_like(sequence)
        for col in range(sequence.shape[1]):
            result[:, col] = np.interp(
                np.linspace(0, len(cropped) - 1, len(sequence)),
                np.arange(len(cropped)),
                cropped[:, col]
            )
        
        return result
    
    # ==================== 模型構建 ====================
    
    def create_model(self, architecture: str, input_shape: Tuple[int, int], num_classes: int):
        """創建模型"""
        if architecture == 'basic':
            return self._create_basic_model(input_shape, num_classes)
        elif architecture == 'bidirectional':
            return self._create_bidirectional_model(input_shape, num_classes)
        elif architecture == 'deep':
            return self._create_deep_model(input_shape, num_classes)
        elif architecture == 'advanced':
            return self._create_advanced_model(input_shape, num_classes)
        else:
            raise ValueError(f"未知的模型架構: {architecture}")
    
    def _create_basic_model(self, input_shape: Tuple[int, int], num_classes: int):
        """基礎 LSTM 模型"""
        tf = _get_tensorflow()
        Sequential = tf.keras.models.Sequential
        LSTM = tf.keras.layers.LSTM
        Dense = tf.keras.layers.Dense
        Dropout = tf.keras.layers.Dropout
        
        return Sequential([
            LSTM(128, input_shape=input_shape, return_sequences=True),
            Dropout(0.4),
            LSTM(64),
            Dropout(0.4),
            Dense(32, activation='relu'),
            Dropout(0.2),
            Dense(num_classes, activation='softmax')
        ])
    
    def _create_bidirectional_model(self, input_shape: Tuple[int, int], num_classes: int):
        """雙向 LSTM 模型"""
        tf = _get_tensorflow()
        Sequential = tf.keras.models.Sequential
        LSTM = tf.keras.layers.LSTM
        Dense = tf.keras.layers.Dense
        Dropout = tf.keras.layers.Dropout
        Bidirectional = tf.keras.layers.Bidirectional
        
        return Sequential([
            Bidirectional(LSTM(64, return_sequences=True), input_shape=input_shape),
            Dropout(0.4),
            Bidirectional(LSTM(32)),
            Dropout(0.3),
            Dense(32, activation='relu'),
            Dense(num_classes, activation='softmax')
        ])
    
    def _create_deep_model(self, input_shape: Tuple[int, int], num_classes: int):
        """深層 LSTM 模型"""
        tf = _get_tensorflow()
        Sequential = tf.keras.models.Sequential
        LSTM = tf.keras.layers.LSTM
        Dense = tf.keras.layers.Dense
        Dropout = tf.keras.layers.Dropout
        BatchNormalization = tf.keras.layers.BatchNormalization
        
        return Sequential([
            LSTM(128, input_shape=input_shape, return_sequences=True),
            BatchNormalization(),
            Dropout(0.4),
            LSTM(64, return_sequences=True),
            BatchNormalization(),
            Dropout(0.4),
            LSTM(32),
            Dropout(0.3),
            Dense(32, activation='relu'),
            Dropout(0.2),
            Dense(num_classes, activation='softmax')
        ])
    
    def _create_advanced_model(self, input_shape: Tuple[int, int], num_classes: int):
        """進階模型 - 適用於更多類別"""
        tf = _get_tensorflow()
        Sequential = tf.keras.models.Sequential
        LSTM = tf.keras.layers.LSTM
        Dense = tf.keras.layers.Dense
        Dropout = tf.keras.layers.Dropout
        BatchNormalization = tf.keras.layers.BatchNormalization
        Bidirectional = tf.keras.layers.Bidirectional
        
        return Sequential([
            Bidirectional(LSTM(128, return_sequences=True), input_shape=input_shape),
            BatchNormalization(),
            Dropout(0.4),
            Bidirectional(LSTM(64, return_sequences=True)),
            BatchNormalization(),
            Dropout(0.4),
            Bidirectional(LSTM(32)),
            Dropout(0.3),
            Dense(64, activation='relu'),
            BatchNormalization(),
            Dropout(0.3),
            Dense(32, activation='relu'),
            Dense(num_classes, activation='softmax')
        ])
    
    # ==================== 訓練流程 ====================
    
    def train(
        self,
        config: TrainingConfig,
        task_id: Optional[str] = None,
        task_storage: Optional[Dict] = None
    ) -> TrainingResult:
        """
        執行訓練
        
        Args:
            config: 訓練配置
            task_id: 任務 ID (用於進度追蹤)
            task_storage: 任務存儲字典
        
        Returns:
            訓練結果
        """
        start_time = datetime.now()
        
        def log(message: str):
            print(message)
            if task_storage and task_id and task_id in task_storage:
                if 'logs' not in task_storage[task_id]:
                    task_storage[task_id]['logs'] = []
                task_storage[task_id]['logs'].append(message)
        
        def update_status(message: str):
            if task_storage and task_id and task_id in task_storage:
                task_storage[task_id]['message'] = message
        
        try:
            # 懶載入依賴
            tf = _get_tensorflow()
            train_test_split, StandardScaler, compute_class_weight = _get_sklearn()
            joblib = _get_joblib()
            to_categorical = tf.keras.utils.to_categorical
            Adam = tf.keras.optimizers.Adam
            EarlyStopping = tf.keras.callbacks.EarlyStopping
            ReduceLROnPlateau = tf.keras.callbacks.ReduceLROnPlateau
            
            # 1. 載入數據
            update_status('正在載入訓練數據...')
            log('📂 載入訓練數據...')
            
            if config.mode == 'simple':
                X_data, y_data, class_names = self.load_simple_training_data()
            else:
                X_data, y_data, class_names = self.load_technique_training_data()
            
            num_classes = len(class_names)
            log(f'✅ 載入完成：{len(X_data)} 個樣本，{num_classes} 個類別')
            
            for i, class_name in enumerate(class_names):
                count = np.sum(y_data == i)
                display_name = self.SIMPLE_CLASS_NAMES.get(class_name) or self.TECHNIQUE_CLASS_NAMES.get(class_name, class_name)
                log(f'   - {display_name}: {count} 個')
            
            # 2. 數據分割
            update_status('正在分割數據集...')
            
            X_train, X_test, y_train, y_test = train_test_split(
                X_data, y_data,
                test_size=config.test_size,
                stratify=y_data,
                random_state=42
            )
            log(f'✅ 訓練集: {len(X_train)}，測試集: {len(X_test)}')
            
            # 3. 數據增強
            if config.use_augmentation:
                update_status('正在進行數據增強...')
                X_train, y_train = self.augment_data(X_train, y_train, config.augment_factor)
                log(f'✅ 增強後訓練集: {len(X_train)} 樣本')
            
            # 4. 標準化
            update_status('正在標準化特徵...')
            input_shape = (X_train.shape[1], X_train.shape[2])
            
            scaler = StandardScaler()
            X_train_flat = X_train.reshape(-1, input_shape[1])
            X_test_flat = X_test.reshape(-1, input_shape[1])
            
            X_train_scaled = scaler.fit_transform(X_train_flat).reshape(-1, input_shape[0], input_shape[1])
            X_test_scaled = scaler.transform(X_test_flat).reshape(-1, input_shape[0], input_shape[1])
            
            # 5. One-hot encoding
            y_train_cat = to_categorical(y_train, num_classes=num_classes)
            y_test_cat = to_categorical(y_test, num_classes=num_classes)
            
            # 6. 計算類別權重
            class_weights = None
            if config.use_class_weights:
                weights = compute_class_weight(
                    'balanced',
                    classes=np.unique(y_train),
                    y=y_train
                )
                class_weights = dict(enumerate(weights))
                log(f'✅ 類別權重計算完成')
            
            # 7. 創建模型
            update_status(f'正在建立 {config.architecture} 模型...')
            
            model = self.create_model(config.architecture, input_shape, num_classes)
            model.compile(
                optimizer=Adam(learning_rate=config.learning_rate),
                loss='categorical_crossentropy',
                metrics=['accuracy']
            )
            
            total_params = model.count_params()
            log(f'✅ 模型建立完成，參數量: {total_params:,}')
            
            # 8. 設置回調
            callbacks = [
                EarlyStopping(
                    monitor='val_loss',
                    patience=config.early_stop_patience,
                    restore_best_weights=True,
                    verbose=0
                ),
                ReduceLROnPlateau(
                    monitor='val_loss',
                    factor=0.5,
                    patience=10,
                    min_lr=1e-6,
                    verbose=0
                )
            ]
            
            if task_storage and task_id:
                TrainingProgressCallback = _create_progress_callback_class()
                callbacks.append(TrainingProgressCallback(task_id, task_storage, config.epochs))
            
            # 9. 訓練
            update_status('開始訓練...')
            log('🏋️ 開始訓練...')
            
            history = model.fit(
                X_train_scaled, y_train_cat,
                validation_data=(X_test_scaled, y_test_cat),
                epochs=config.epochs,
                batch_size=config.batch_size,
                class_weight=class_weights,
                callbacks=callbacks,
                verbose=0
            )
            
            # 10. 評估
            update_status('正在評估模型...')
            test_loss, test_acc = model.evaluate(X_test_scaled, y_test_cat, verbose=0)
            log(f'✅ 測試準確率: {test_acc:.4f}')
            log(f'✅ 測試損失: {test_loss:.4f}')
            
            # 11. 計算混淆矩陣
            y_pred = model.predict(X_test_scaled, verbose=0)
            y_pred_classes = np.argmax(y_pred, axis=1)
            
            # 使用懶載入的 sklearn
            from sklearn.metrics import confusion_matrix as sklearn_cm
            cm = sklearn_cm(y_test, y_pred_classes)
            
            # 計算每類準確率
            per_class_acc = {}
            for i, class_name in enumerate(class_names):
                class_mask = y_test == i
                if np.sum(class_mask) > 0:
                    class_acc = np.mean(y_pred_classes[class_mask] == i)
                    display_name = self.SIMPLE_CLASS_NAMES.get(class_name) or self.TECHNIQUE_CLASS_NAMES.get(class_name, class_name)
                    per_class_acc[display_name] = float(class_acc)
            
            # 12. 儲存模型
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            model_name = f"{config.mode}_{config.architecture}_{timestamp}"
            model_path = os.path.join(self.models_dir, f"{model_name}.h5")
            scaler_path = os.path.join(self.models_dir, f"{model_name}_scaler.pkl")
            config_path = os.path.join(self.models_dir, f"{model_name}_config.json")
            
            model.save(model_path)
            joblib.dump(scaler, scaler_path)
            
            # 儲存配置和類別名稱
            model_config = {
                'mode': config.mode,
                'architecture': config.architecture,
                'class_names': class_names,
                'input_shape': list(input_shape),
                'num_classes': num_classes,
                'created_at': timestamp,
                'accuracy': float(test_acc)
            }
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(model_config, f, ensure_ascii=False, indent=2)
            
            # 更新最新模型連結
            latest_model_path = os.path.join(self.models_dir, f"latest_{config.mode}.h5")
            latest_scaler_path = os.path.join(self.models_dir, f"latest_{config.mode}_scaler.pkl")
            latest_config_path = os.path.join(self.models_dir, f"latest_{config.mode}_config.json")
            
            # 複製為 latest
            shutil.copy2(model_path, latest_model_path)
            shutil.copy2(scaler_path, latest_scaler_path)
            shutil.copy2(config_path, latest_config_path)
            
            log(f'✅ 模型已儲存: {model_name}')
            
            # 計算訓練時間
            end_time = datetime.now()
            training_time = str(end_time - start_time).split('.')[0]
            log(f'🎉 訓練完成！總耗時: {training_time}')
            
            return TrainingResult(
                success=True,
                model_path=model_path,
                accuracy=float(test_acc),
                val_accuracy=float(history.history['val_accuracy'][-1]),
                loss=float(test_loss),
                val_loss=float(history.history['val_loss'][-1]),
                training_time=training_time,
                total_samples=len(X_data),
                num_classes=num_classes,
                class_names=class_names,
                confusion_matrix=cm.tolist(),
                per_class_accuracy=per_class_acc
            )
            
        except Exception as e:
            import traceback
            error_msg = f"訓練失敗: {str(e)}\n{traceback.format_exc()}"
            log(f'❌ {error_msg}')
            
            return TrainingResult(
                success=False,
                model_path='',
                accuracy=0.0,
                val_accuracy=0.0,
                loss=0.0,
                val_loss=0.0,
                training_time='',
                total_samples=0,
                num_classes=0,
                class_names=[],
                error_message=str(e)
            )
    
    # ==================== 模型管理 ====================
    
    def get_available_models(self) -> List[Dict[str, Any]]:
        """取得可用模型列表"""
        models = []
        
        if not os.path.exists(self.models_dir):
            return models
        
        for filename in os.listdir(self.models_dir):
            if filename.endswith('.h5') and not filename.startswith('latest_'):
                config_path = os.path.join(self.models_dir, filename.replace('.h5', '_config.json'))
                
                model_info = {
                    'filename': filename,
                    'path': os.path.join(self.models_dir, filename),
                    'created_at': None,
                    'mode': None,
                    'architecture': None,
                    'accuracy': None
                }
                
                if os.path.exists(config_path):
                    with open(config_path, 'r', encoding='utf-8') as f:
                        config = json.load(f)
                        model_info.update(config)
                
                models.append(model_info)
        
        # 按創建時間排序
        models.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        
        return models
    
    def get_latest_model(self, mode: str = 'simple') -> Optional[Dict[str, Any]]:
        """取得最新模型"""
        model_path = os.path.join(self.models_dir, f"latest_{mode}.h5")
        config_path = os.path.join(self.models_dir, f"latest_{mode}_config.json")
        
        if not os.path.exists(model_path):
            return None
        
        result = {'model_path': model_path}
        
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                result['config'] = json.load(f)
        
        return result
    
    def delete_model(self, filename: str) -> bool:
        """刪除模型"""
        model_path = os.path.join(self.models_dir, filename)
        
        if not os.path.exists(model_path):
            return False
        
        # 刪除相關檔案
        base_name = filename.replace('.h5', '')
        for suffix in ['.h5', '_scaler.pkl', '_config.json']:
            file_path = os.path.join(self.models_dir, base_name + suffix)
            if os.path.exists(file_path):
                os.remove(file_path)
        
        return True


# 單例
_unified_service = None

def get_unified_training_service() -> UnifiedTrainingService:
    global _unified_service
    if _unified_service is None:
        _unified_service = UnifiedTrainingService()
    return _unified_service
