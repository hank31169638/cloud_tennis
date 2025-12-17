"""
優化版訓練腳本 - 整合進階技術
基於 MODEL_TRAINING_GUIDE.md 的建議實作

使用方式:
    python train_optimized.py --data_path ./training_data --epochs 150
"""

import numpy as np
from sklearn.model_selection import train_test_split, KFold
from sklearn.preprocessing import StandardScaler
from sklearn.utils.class_weight import compute_class_weight
from sklearn.metrics import confusion_matrix, classification_report
import tensorflow as tf
from tensorflow.keras.models import Sequential # type: ignore
from tensorflow.keras.layers import LSTM, Dense, Dropout, Bidirectional # type: ignore
from tensorflow.keras.callbacks import ( # type: ignore
    EarlyStopping, 
    ModelCheckpoint, 
    ReduceLROnPlateau,
    TensorBoard
)
from tensorflow.keras.optimizers import Adam # type: ignore
import os
import argparse
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime

# ============ 資料增強函數 ============

def temporal_scaling(sequence, scale_factor=0.2):
    """時間軸縮放：隨機加速或減速動作"""
    scale = np.random.uniform(1 - scale_factor, 1 + scale_factor)
    original_length = len(sequence)
    indices = np.linspace(0, original_length - 1, int(original_length * scale))
    
    scaled_seq = np.zeros((len(indices), sequence.shape[1]))
    for col in range(sequence.shape[1]):
        scaled_seq[:, col] = np.interp(indices, np.arange(original_length), sequence[:, col])
    
    # 重新採樣到 150 幀
    final_indices = np.linspace(0, len(scaled_seq) - 1, 150)
    final_seq = np.zeros((150, sequence.shape[1]))
    for col in range(sequence.shape[1]):
        final_seq[:, col] = np.interp(final_indices, np.arange(len(scaled_seq)), scaled_seq[:, col])
    
    return final_seq


def add_gaussian_noise(sequence, noise_level=0.01):
    """添加高斯噪聲模擬偵測誤差"""
    noise = np.random.normal(0, noise_level, sequence.shape)
    return sequence + noise


def random_crop_pad(sequence, target_length=150, crop_ratio=0.1):
    """隨機裁剪與填充"""
    crop_length = int(len(sequence) * (1 - crop_ratio))
    start_idx = np.random.randint(0, max(1, len(sequence) - crop_length))
    cropped = sequence[start_idx:start_idx + crop_length]
    
    # 填充回目標長度
    indices = np.linspace(0, len(cropped) - 1, target_length)
    padded = np.zeros((target_length, sequence.shape[1]))
    for col in range(sequence.shape[1]):
        padded[:, col] = np.interp(indices, np.arange(len(cropped)), cropped[:, col])
    
    return padded


def augment_data(sequences, labels, augment_factor=3):
    """整合增強管線"""
    aug_sequences = []
    aug_labels = []
    
    for seq, label in zip(sequences, labels):
        # 保留原始樣本
        aug_sequences.append(seq)
        aug_labels.append(label)
        
        # 生成增強樣本
        for _ in range(augment_factor):
            aug_seq = seq.copy()
            
            # 隨機應用增強技術
            if np.random.rand() > 0.5:
                aug_seq = temporal_scaling(aug_seq)
            if np.random.rand() > 0.5:
                aug_seq = add_gaussian_noise(aug_seq)
            if np.random.rand() > 0.3:
                aug_seq = random_crop_pad(aug_seq)
            
            aug_sequences.append(aug_seq)
            aug_labels.append(label)
    
    return np.array(aug_sequences), np.array(aug_labels)


# ============ 模型建構函數 ============

def create_model_basic(input_shape=(150, 69), num_classes=3):
    """基礎模型（原始架構改良版）"""
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


# ============ 評估與視覺化 ============

def plot_confusion_matrix(y_true, y_pred, class_names, save_path):
    """繪製混淆矩陣"""
    cm = confusion_matrix(y_true, y_pred)
    plt.figure(figsize=(10, 8))
    sns.heatmap(
        cm, 
        annot=True, 
        fmt='d', 
        cmap='Blues',
        xticklabels=class_names,
        yticklabels=class_names,
        cbar_kws={'label': '樣本數量'}
    )
    plt.ylabel('實際類別', fontsize=12)
    plt.xlabel('預測類別', fontsize=12)
    plt.title('混淆矩陣', fontsize=14, fontweight='bold')
    plt.tight_layout()
    plt.savefig(save_path, dpi=300)
    plt.close()
    print(f"✅ 混淆矩陣已儲存至: {save_path}")


def plot_training_history(history, save_path):
    """繪製訓練歷史"""
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    
    # 準確率
    axes[0].plot(history.history['accuracy'], label='訓練準確率', linewidth=2)
    axes[0].plot(history.history['val_accuracy'], label='驗證準確率', linewidth=2)
    axes[0].set_xlabel('Epoch', fontsize=12)
    axes[0].set_ylabel('準確率', fontsize=12)
    axes[0].set_title('模型準確率', fontsize=14, fontweight='bold')
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)
    
    # 損失
    axes[1].plot(history.history['loss'], label='訓練損失', linewidth=2)
    axes[1].plot(history.history['val_loss'], label='驗證損失', linewidth=2)
    axes[1].set_xlabel('Epoch', fontsize=12)
    axes[1].set_ylabel('損失', fontsize=12)
    axes[1].set_title('模型損失', fontsize=14, fontweight='bold')
    axes[1].legend()
    axes[1].grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(save_path, dpi=300)
    plt.close()
    print(f"✅ 訓練歷史已儲存至: {save_path}")


# ============ 主訓練流程 ============

def main(args):
    print("=" * 60)
    print("🚀 桌球動作分析模型訓練 - 優化版本")
    print("=" * 60)
    
    # 建立輸出目錄
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = f"training_output_{timestamp}"
    os.makedirs(output_dir, exist_ok=True)
    
    # 1. 載入資料（需要根據實際情況調整）
    print("\n📂 載入資料...")
    # TODO: 實作你的資料載入邏輯
    # X_data, y_data = load_your_data(args.data_path)
    
    # 示例：假設已有資料
    # X_data shape: (num_samples, 150, 69)
    # y_data shape: (num_samples,) - 類別標籤 0/1/2
    
    # 暫時使用隨機資料示範
    print("⚠️  使用隨機資料示範（請替換為真實資料）")
    X_data = np.random.randn(300, 150, 69)
    y_data = np.random.randint(0, 3, 300)
    
    # 2. 資料分割
    print("\n✂️  分割資料集...")
    X_temp, X_test, y_temp, y_test = train_test_split(
        X_data, y_data, test_size=0.15, stratify=y_data, random_state=42
    )
    X_train, X_val, y_train, y_val = train_test_split(
        X_temp, y_temp, test_size=0.176, stratify=y_temp, random_state=42  # 0.176 * 0.85 ≈ 0.15
    )
    
    print(f"訓練集: {X_train.shape[0]} 樣本")
    print(f"驗證集: {X_val.shape[0]} 樣本")
    print(f"測試集: {X_test.shape[0]} 樣本")
    
    # 3. 資料增強
    if args.use_augmentation:
        print(f"\n🔄 應用資料增強 (擴增因子={args.augment_factor})...")
        X_train_aug, y_train_aug = augment_data(X_train, y_train, augment_factor=args.augment_factor)
        print(f"增強後訓練集: {X_train_aug.shape[0]} 樣本")
    else:
        X_train_aug, y_train_aug = X_train, y_train
    
    # 4. 標準化
    print("\n📊 標準化特徵...")
    scaler = StandardScaler()
    X_train_aug = scaler.fit_transform(X_train_aug.reshape(-1, 69)).reshape(-1, 150, 69)
    X_val = scaler.transform(X_val.reshape(-1, 69)).reshape(-1, 150, 69)
    X_test = scaler.transform(X_test.reshape(-1, 69)).reshape(-1, 150, 69)
    
    # 儲存 scaler
    import joblib
    scaler_path = os.path.join(output_dir, 'scaler.pkl')
    joblib.dump(scaler, scaler_path)
    print(f"✅ Scaler 已儲存至: {scaler_path}")
    
    # 5. One-hot encoding
    from tensorflow.keras.utils import to_categorical # type: ignore
    y_train_cat = to_categorical(y_train_aug, num_classes=3)
    y_val_cat = to_categorical(y_val, num_classes=3)
    y_test_cat = to_categorical(y_test, num_classes=3)
    
    # 6. 計算類別權重
    print("\n⚖️  計算類別權重...")
    class_weights = compute_class_weight(
        'balanced',
        classes=np.unique(y_train_aug),
        y=y_train_aug
    )
    class_weight_dict = dict(enumerate(class_weights))
    print(f"類別權重: {class_weight_dict}")
    
    # 7. 建立模型
    print(f"\n🧠 建立模型 (架構={args.model_type})...")
    if args.model_type == 'basic':
        model = create_model_basic()
    elif args.model_type == 'bidirectional':
        model = create_model_bidirectional()
    elif args.model_type == 'deep':
        model = create_model_deep()
    else:
        raise ValueError(f"未知的模型類型: {args.model_type}")
    
    model.compile(
        optimizer=Adam(learning_rate=args.learning_rate),
        loss='categorical_crossentropy',
        metrics=['accuracy']
    )
    model.summary()
    
    # 8. 配置 Callbacks
    print("\n⚙️  配置訓練回調...")
    callbacks = [
        EarlyStopping(
            monitor='val_loss',
            patience=args.early_stop_patience,
            restore_best_weights=True,
            verbose=1
        ),
        ModelCheckpoint(
            os.path.join(output_dir, 'best_model.h5'),
            monitor='val_accuracy',
            save_best_only=True,
            mode='max',
            verbose=1
        ),
        ReduceLROnPlateau(
            monitor='val_loss',
            factor=0.5,
            patience=10,
            min_lr=1e-6,
            verbose=1
        ),
        TensorBoard(
            log_dir=os.path.join(output_dir, 'logs'),
            histogram_freq=1
        )
    ]
    
    # 9. 訓練模型
    print("\n🏋️  開始訓練...")
    history = model.fit(
        X_train_aug, y_train_cat,
        validation_data=(X_val, y_val_cat),
        epochs=args.epochs,
        batch_size=args.batch_size,
        class_weight=class_weight_dict,
        callbacks=callbacks,
        verbose=1
    )
    
    # 10. 評估模型
    print("\n📈 評估模型...")
    test_loss, test_acc = model.evaluate(X_test, y_test_cat, verbose=0)
    print(f"✅ 測試集準確率: {test_acc:.4f}")
    print(f"✅ 測試集損失: {test_loss:.4f}")
    
    # 11. 預測與分析
    print("\n🔍 生成預測...")
    y_pred = model.predict(X_test)
    y_pred_classes = np.argmax(y_pred, axis=1)
    y_true_classes = np.argmax(y_test_cat, axis=1)
    
    # 12. 混淆矩陣
    class_names = ['Bad', 'Good', 'Normal']
    cm_path = os.path.join(output_dir, 'confusion_matrix.png')
    plot_confusion_matrix(y_true_classes, y_pred_classes, class_names, cm_path)
    
    # 13. 分類報告
    print("\n📊 分類報告:")
    report = classification_report(
        y_true_classes, 
        y_pred_classes,
        target_names=class_names,
        digits=4
    )
    print(report)
    
    # 儲存報告
    report_path = os.path.join(output_dir, 'classification_report.txt')
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)
    print(f"✅ 分類報告已儲存至: {report_path}")
    
    # 14. 訓練歷史視覺化
    history_path = os.path.join(output_dir, 'training_history.png')
    plot_training_history(history, history_path)
    
    # 15. 儲存最終模型
    final_model_path = os.path.join(output_dir, 'final_model.h5')
    model.save(final_model_path)
    print(f"\n✅ 最終模型已儲存至: {final_model_path}")
    
    print("\n" + "=" * 60)
    print("🎉 訓練完成！")
    print(f"📁 所有輸出已儲存至: {output_dir}")
    print("=" * 60)
    
    # 返回結果
    return {
        'model': model,
        'history': history,
        'test_accuracy': test_acc,
        'output_dir': output_dir
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='優化版桌球動作分析模型訓練')
    
    # 資料參數
    parser.add_argument('--data_path', type=str, default='./training_data',
                        help='訓練資料路徑')
    
    # 模型參數
    parser.add_argument('--model_type', type=str, default='basic',
                        choices=['basic', 'bidirectional', 'deep'],
                        help='模型架構類型')
    
    # 訓練參數
    parser.add_argument('--epochs', type=int, default=150,
                        help='訓練輪數')
    parser.add_argument('--batch_size', type=int, default=32,
                        help='批次大小')
    parser.add_argument('--learning_rate', type=float, default=0.001,
                        help='學習率')
    parser.add_argument('--early_stop_patience', type=int, default=15,
                        help='早停耐心值')
    
    # 資料增強參數
    parser.add_argument('--use_augmentation', action='store_true',
                        help='是否使用資料增強')
    parser.add_argument('--augment_factor', type=int, default=3,
                        help='資料增強因子')
    
    args = parser.parse_args()
    
    # 執行訓練
    results = main(args)
