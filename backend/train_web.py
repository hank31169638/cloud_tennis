"""
網頁版訓練腳本 - 簡化版本，支援進度回報
"""

import numpy as np
import os
import glob
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
import tensorflow as tf
from tensorflow.keras.models import Sequential # type: ignore
from tensorflow.keras.layers import LSTM, Dense, Dropout, Bidirectional # type: ignore
from tensorflow.keras.callbacks import Callback # type: ignore
from tensorflow.keras.optimizers import Adam # type: ignore
import joblib
from datetime import datetime
from skeleton import PoseExtractor


class TrainingProgressCallback(Callback):
    """自定義回調函數，用於更新訓練進度"""
    
    def __init__(self, task_id, training_tasks, total_epochs):
        super().__init__()
        self.task_id = task_id
        self.training_tasks = training_tasks
        self.total_epochs = total_epochs
    
    def on_epoch_end(self, epoch, logs=None):
        """每個 epoch 結束後更新狀態"""
        logs = logs or {}
        
        self.training_tasks[self.task_id].update({
            'current_epoch': epoch + 1,
            'accuracy': float(logs.get('accuracy', 0)),
            'val_accuracy': float(logs.get('val_accuracy', 0)),
            'loss': float(logs.get('loss', 0)),
            'val_loss': float(logs.get('val_loss', 0)),
            'message': f'訓練中... Epoch {epoch + 1}/{self.total_epochs}'
        })
        
        log_msg = f"Epoch {epoch + 1}/{self.total_epochs} - acc: {logs.get('accuracy', 0):.4f} - val_acc: {logs.get('val_accuracy', 0):.4f}"
        self.training_tasks[self.task_id]['logs'].append(log_msg)


def load_training_data():
    """載入訓練資料"""
    X_data = []
    y_data = []
    
    # 定義類別對應
    class_map = {'good': 0, 'normal': 1, 'bad': 2}
    
    # 初始化骨架提取器
    pose_extractor = PoseExtractor()
    
    # 掃描各個類別的影片資料夾
    for class_name, class_id in class_map.items():
        folder = f'{class_name}_input_movid'
        if not os.path.exists(folder):
            continue
        
        video_files = glob.glob(os.path.join(folder, '*.mp4')) + \
                      glob.glob(os.path.join(folder, '*.avi')) + \
                      glob.glob(os.path.join(folder, '*.MOV'))
        
        print(f"處理 {class_name} 類別，找到 {len(video_files)} 個影片")
        
        for video_path in video_files:
            try:
                # 提取骨架特徵（返回字典列表）
                pose_data = pose_extractor.extract_pose_data(video_path)
                
                if pose_data is None or len(pose_data) == 0:
                    print(f"警告：{video_path} 未提取到骨架資料")
                    continue
                
                # 將骨架資料轉換為數值陣列
                landmarks_array = []
                for frame_data in pose_data:
                    if frame_data['landmarks'] is not None:
                        frame_landmarks = []
                        for lm in frame_data['landmarks']:
                            # 只使用 x, y, z 座標（忽略 visibility）
                            frame_landmarks.extend([lm['x'], lm['y'], lm['z']])
                        landmarks_array.append(frame_landmarks)
                
                if len(landmarks_array) == 0:
                    print(f"警告：{video_path} 未偵測到有效幀")
                    continue
                
                # 轉換為 numpy 陣列
                landmarks_array = np.array(landmarks_array)
                
                # 標準化為 150 幀 × 69 特徵（23 個關鍵點 × 3 座標）
                # MediaPipe Pose 有 33 個關鍵點，排除臉部後剩 23 個
                target_frames = 150
                target_features = 69  # 23 關鍵點 × 3 座標 (x, y, z)
                
                # 檢查特徵維度
                if landmarks_array.shape[1] != target_features:
                    print(f"警告：{video_path} 特徵維度不符 ({landmarks_array.shape[1]} != {target_features})，跳過")
                    continue
                
                # 重新採樣到 150 幀
                if landmarks_array.shape[0] != target_frames:
                    # 使用線性插值重新採樣
                    original_frames = landmarks_array.shape[0]
                    resampled = np.zeros((target_frames, target_features))
                    
                    for feature_idx in range(target_features):
                        resampled[:, feature_idx] = np.interp(
                            np.linspace(0, original_frames - 1, target_frames),
                            np.arange(original_frames),
                            landmarks_array[:, feature_idx]
                        )
                    landmarks_array = resampled
                
                X_data.append(landmarks_array)
                y_data.append(class_id)
                
            except Exception as e:
                print(f"處理影片 {video_path} 時出錯: {e}")
                import traceback
                traceback.print_exc()
                continue
    
    if len(X_data) == 0:
        raise ValueError("未找到任何訓練資料，請確認影片資料夾是否存在且包含有效影片")
    
    print(f"成功載入 {len(X_data)} 個訓練樣本")
    return np.array(X_data), np.array(y_data)


def create_model_basic(input_shape=(150, 69), num_classes=3):
    """基礎 LSTM 模型"""
    model = Sequential([
        LSTM(128, input_shape=input_shape, return_sequences=True),
        Dropout(0.4),
        LSTM(64),
        Dropout(0.4),
        Dense(32, activation='relu'),
        Dropout(0.2),
        Dense(num_classes, activation='softmax')
    ])
    return model


def create_model_bidirectional(input_shape=(150, 69), num_classes=3):
    """雙向 LSTM 模型"""
    model = Sequential([
        Bidirectional(LSTM(64, return_sequences=True), input_shape=input_shape),
        Dropout(0.4),
        Bidirectional(LSTM(32)),
        Dropout(0.3),
        Dense(16, activation='relu'),
        Dense(num_classes, activation='softmax')
    ])
    return model


def create_model_deep(input_shape=(150, 69), num_classes=3):
    """深層 LSTM 模型"""
    model = Sequential([
        LSTM(128, input_shape=input_shape, return_sequences=True),
        Dropout(0.4),
        LSTM(64, return_sequences=True),
        Dropout(0.4),
        LSTM(32),
        Dropout(0.3),
        Dense(32, activation='relu'),
        Dropout(0.2),
        Dense(num_classes, activation='softmax')
    ])
    return model


def train_model(config, task_id, training_tasks):
    """
    執行模型訓練
    
    Args:
        config: 訓練配置
        task_id: 任務 ID
        training_tasks: 全局任務字典（用於更新進度）
    
    Returns:
        訓練結果字典
    """
    try:
        start_time = datetime.now()
        
        # 1. 載入資料
        training_tasks[task_id]['message'] = '正在載入訓練資料...'
        training_tasks[task_id]['logs'].append('📂 載入訓練資料...')
        
        X_data, y_data = load_training_data()
        
        training_tasks[task_id]['logs'].append(f'✅ 載入完成：共 {len(X_data)} 個樣本')
        training_tasks[task_id]['logs'].append(f'   - Good: {np.sum(y_data == 0)} 個')
        training_tasks[task_id]['logs'].append(f'   - Normal: {np.sum(y_data == 1)} 個')
        training_tasks[task_id]['logs'].append(f'   - Bad: {np.sum(y_data == 2)} 個')
        
        # 檢查樣本數量是否足夠
        min_samples_per_class = 10
        for class_id in [0, 1, 2]:
            class_count = np.sum(y_data == class_id)
            if class_count < min_samples_per_class:
                class_name = ['Good', 'Normal', 'Bad'][class_id]
                raise ValueError(
                    f'{class_name} 類別只有 {class_count} 個樣本，至少需要 {min_samples_per_class} 個。\n'
                    f'請在對應資料夾中添加更多影片：\n'
                    f'  - Good → backend/good_input_movid/\n'
                    f'  - Normal → backend/normal_input_movid/\n'
                    f'  - Bad → backend/bad_input_movid/'
                )
        
        if len(X_data) < 30:
            raise ValueError(
                f'總樣本數只有 {len(X_data)} 個，至少需要 30 個（每類 10 個）才能進行訓練。\n'
                f'當前狀態：\n'
                f'  - Good: {np.sum(y_data == 0)} 個\n'
                f'  - Normal: {np.sum(y_data == 1)} 個\n'
                f'  - Bad: {np.sum(y_data == 2)} 個\n\n'
                f'建議：每個類別至少準備 30 個影片（總共 90 個）以獲得較好的訓練效果。'
            )
        
        # 2. 資料分割
        training_tasks[task_id]['message'] = '正在分割資料集...'
        
        # 根據樣本數量動態調整測試集比例
        if len(X_data) < 50:
            test_size = 0.25  # 小數據集用 25%
            training_tasks[task_id]['logs'].append('⚠️  樣本數較少，使用 25% 作為測試集')
        else:
            test_size = 0.2   # 正常情況用 20%
        
        X_train, X_test, y_train, y_test = train_test_split(
            X_data, y_data, test_size=test_size, stratify=y_data, random_state=42
        )
        
        training_tasks[task_id]['logs'].append(f'✅ 訓練集: {len(X_train)} 樣本，測試集: {len(X_test)} 樣本')
        
        # 3. 標準化
        training_tasks[task_id]['message'] = '正在標準化特徵...'
        scaler = StandardScaler()
        X_train = scaler.fit_transform(X_train.reshape(-1, 69)).reshape(-1, 150, 69)
        X_test = scaler.transform(X_test.reshape(-1, 69)).reshape(-1, 150, 69)
        
        # 儲存 scaler
        joblib.dump(scaler, 'scaler.pkl')
        training_tasks[task_id]['logs'].append('✅ 特徵標準化完成')
        
        # 4. One-hot encoding
        from tensorflow.keras.utils import to_categorical # type: ignore
        y_train_cat = to_categorical(y_train, num_classes=3)
        y_test_cat = to_categorical(y_test, num_classes=3)
        
        # 5. 建立模型
        training_tasks[task_id]['message'] = f'正在建立 {config["model_type"]} 模型...'
        
        if config['model_type'] == 'basic':
            model = create_model_basic()
        elif config['model_type'] == 'bidirectional':
            model = create_model_bidirectional()
        elif config['model_type'] == 'deep':
            model = create_model_deep()
        else:
            raise ValueError(f"未知的模型類型: {config['model_type']}")
        
        model.compile(
            optimizer=Adam(learning_rate=config['learning_rate']),
            loss='categorical_crossentropy',
            metrics=['accuracy']
        )
        
        training_tasks[task_id]['logs'].append(f'✅ {config["model_type"]} 模型建立完成')
        total_params = model.count_params()
        training_tasks[task_id]['logs'].append(f'   模型參數量: {total_params:,}')
        
        # 6. 訓練模型
        training_tasks[task_id]['message'] = '開始訓練模型...'
        training_tasks[task_id]['logs'].append('🏋️ 開始訓練...')
        
        progress_callback = TrainingProgressCallback(task_id, training_tasks, config['epochs'])
        
        history = model.fit(
            X_train, y_train_cat,
            validation_data=(X_test, y_test_cat),
            epochs=config['epochs'],
            batch_size=config['batch_size'],
            callbacks=[progress_callback],
            verbose=0  # 不在控制台輸出，改用回調函數
        )
        
        # 7. 評估模型
        training_tasks[task_id]['message'] = '正在評估模型...'
        test_loss, test_acc = model.evaluate(X_test, y_test_cat, verbose=0)
        
        training_tasks[task_id]['logs'].append(f'✅ 測試集準確率: {test_acc:.4f}')
        training_tasks[task_id]['logs'].append(f'✅ 測試集損失: {test_loss:.4f}')
        
        # 8. 儲存模型
        model_path = 'pose_classifier_model.h5'
        model.save(model_path)
        training_tasks[task_id]['logs'].append(f'✅ 模型已儲存至: {model_path}')
        
        # 計算訓練時間
        end_time = datetime.now()
        training_time = str(end_time - start_time).split('.')[0]  # 移除微秒
        
        training_tasks[task_id]['logs'].append(f'🎉 訓練完成！總耗時: {training_time}')
        
        # 返回結果
        return {
            'test_accuracy': float(test_acc),
            'test_loss': float(test_loss),
            'training_time': training_time,
            'model_path': model_path,
            'total_samples': len(X_data),
            'train_samples': len(X_train),
            'test_samples': len(X_test),
            'model_params': int(total_params)
        }
        
    except Exception as e:
        raise Exception(f'訓練過程中發生錯誤: {str(e)}')
