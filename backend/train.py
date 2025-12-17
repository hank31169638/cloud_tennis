import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
import torchvision.transforms as transforms
from torchvision.models.video import r3d_18, R3D_18_Weights
import cv2
import numpy as np
import os
from tqdm import tqdm
from sklearn.model_selection import train_test_split
import random

# 設定隨機種子
def set_seed(seed=42):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed(seed)
        torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False

set_seed(42)

# 檢查 CUDA 是否可用
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
print(f'使用設備: {device}')
if torch.cuda.is_available():
    print(f'GPU: {torch.cuda.get_device_name(0)}')

class VideoDataset(Dataset):
    """影片資料集類別"""
    def __init__(self, video_paths, labels, num_frames=16, transform=None):
        self.video_paths = video_paths
        self.labels = labels
        self.num_frames = num_frames
        self.transform = transform
    
    def __len__(self):
        return len(self.video_paths)
    
    def __getitem__(self, idx):
        video_path = self.video_paths[idx]
        label = self.labels[idx]
        
        # 讀取影片並提取影格
        frames = self.load_video(video_path)
        
        # 轉換為 tensor
        frames = torch.FloatTensor(frames)
        frames = frames.permute(3, 0, 1, 2)  # (T, H, W, C) -> (C, T, H, W)
        
        # 正規化到 [0, 1]
        frames = frames / 255.0
        
        if self.transform:
            frames = self.transform(frames)
        
        return frames, label
    
    def load_video(self, video_path):
        """從影片中提取固定數量的影格"""
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError(f"無法開啟影片: {video_path}")
        
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        
        # 計算要提取的影格索引
        if total_frames <= self.num_frames:
            # 如果影片影格數不足，重複最後一幀
            frame_indices = list(range(total_frames))
            while len(frame_indices) < self.num_frames:
                frame_indices.append(frame_indices[-1])
        else:
            # 均勻採樣
            frame_indices = np.linspace(0, total_frames - 1, self.num_frames, dtype=int)
        
        frames = []
        frame_idx = 0
        
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            
            if frame_idx in frame_indices:
                # 調整大小到 112x112 (R3D 模型的標準輸入)
                frame = cv2.resize(frame, (112, 112))
                frames.append(frame)
            
            frame_idx += 1
            
            if len(frames) >= self.num_frames:
                break
        
        cap.release()
        
        # 如果影格數不足，用最後一幀填充
        while len(frames) < self.num_frames:
            frames.append(frames[-1] if frames else np.zeros((112, 112, 3), dtype=np.uint8))
        
        # 轉換為 numpy array
        frames = np.array(frames[:self.num_frames])
        
        return frames

def load_video_paths(bad_folder, good_folder):
    """載入所有影片路徑和標籤"""
    video_paths = []
    labels = []
    
    # 載入不標準的影片 (label = 0)
    if os.path.exists(bad_folder):
        bad_videos = [os.path.join(bad_folder, f) for f in os.listdir(bad_folder) 
                     if f.lower().endswith('.mp4')]
        video_paths.extend(bad_videos)
        labels.extend([0] * len(bad_videos))
        print(f'載入 {len(bad_videos)} 個不標準影片')
    
    # 載入標準的影片 (label = 1)
    if os.path.exists(good_folder):
        good_videos = [os.path.join(good_folder, f) for f in os.listdir(good_folder) 
                      if f.lower().endswith('.mp4')]
        video_paths.extend(good_videos)
        labels.extend([1] * len(good_videos))
        print(f'載入 {len(good_videos)} 個標準影片')
    
    return video_paths, labels

def train_model(model, train_loader, val_loader, num_epochs=20, learning_rate=0.001):
    """訓練模型"""
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=learning_rate, weight_decay=1e-4)
    scheduler = optim.lr_scheduler.StepLR(optimizer, step_size=7, gamma=0.1)
    
    best_val_acc = 0.0
    train_losses = []
    train_accs = []
    val_losses = []
    val_accs = []
    
    for epoch in range(num_epochs):
        # 訓練階段
        model.train()
        train_loss = 0.0
        train_correct = 0
        train_total = 0
        
        train_pbar = tqdm(train_loader, desc=f'Epoch {epoch+1}/{num_epochs} [Train]')
        for videos, labels in train_pbar:
            videos = videos.to(device)
            labels = labels.to(device)
            
            optimizer.zero_grad()
            outputs = model(videos)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()
            
            train_loss += loss.item()
            _, predicted = torch.max(outputs.data, 1)
            train_total += labels.size(0)
            train_correct += (predicted == labels).sum().item()
            
            train_pbar.set_postfix({
                'loss': f'{loss.item():.4f}',
                'acc': f'{100*train_correct/train_total:.2f}%'
            })
        
        train_loss /= len(train_loader)
        train_acc = 100 * train_correct / train_total
        train_losses.append(train_loss)
        train_accs.append(train_acc)
        
        # 驗證階段
        model.eval()
        val_loss = 0.0
        val_correct = 0
        val_total = 0
        
        with torch.no_grad():
            val_pbar = tqdm(val_loader, desc=f'Epoch {epoch+1}/{num_epochs} [Val]')
            for videos, labels in val_pbar:
                videos = videos.to(device)
                labels = labels.to(device)
                
                outputs = model(videos)
                loss = criterion(outputs, labels)
                
                val_loss += loss.item()
                _, predicted = torch.max(outputs.data, 1)
                val_total += labels.size(0)
                val_correct += (predicted == labels).sum().item()
                
                val_pbar.set_postfix({
                    'loss': f'{loss.item():.4f}',
                    'acc': f'{100*val_correct/val_total:.2f}%'
                })
        
        val_loss /= len(val_loader)
        val_acc = 100 * val_correct / val_total
        val_losses.append(val_loss)
        val_accs.append(val_acc)
        
        scheduler.step()
        
        print(f'\nEpoch {epoch+1}/{num_epochs}:')
        print(f'  Train Loss: {train_loss:.4f}, Train Acc: {train_acc:.2f}%')
        print(f'  Val Loss: {val_loss:.4f}, Val Acc: {val_acc:.2f}%')
        print(f'  Learning Rate: {scheduler.get_last_lr()[0]:.6f}\n')
        
        # 儲存最佳模型
        if val_acc > best_val_acc:
            best_val_acc = val_acc
            torch.save(model.state_dict(), 'table_tennis_model.pth')
            print(f'✓ 儲存最佳模型 (Val Acc: {val_acc:.2f}%)\n')
    
    return train_losses, train_accs, val_losses, val_accs

def main():
    # 資料路徑
    bad_folder = 'bad_output_movid'
    good_folder = 'good_output_movid'
    
    # 載入資料
    print('載入影片資料...')
    video_paths, labels = load_video_paths(bad_folder, good_folder)
    
    if len(video_paths) == 0:
        print('錯誤: 沒有找到任何影片檔案!')
        return
    
    print(f'總共載入 {len(video_paths)} 個影片')
    print(f'不標準: {labels.count(0)} 個, 標準: {labels.count(1)} 個\n')
    
    # 分割訓練集和驗證集
    train_paths, val_paths, train_labels, val_labels = train_test_split(
        video_paths, labels, test_size=0.2, random_state=42, stratify=labels
    )
    
    print(f'訓練集: {len(train_paths)} 個影片')
    print(f'驗證集: {len(val_paths)} 個影片\n')
    
    # 建立資料集
    train_dataset = VideoDataset(train_paths, train_labels, num_frames=16)
    val_dataset = VideoDataset(val_paths, val_labels, num_frames=16)
    
    # 建立資料載入器
    batch_size = 4 if torch.cuda.is_available() else 2
    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True, num_workers=2)
    val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False, num_workers=2)
    
    # 載入預訓練的 R3D-18 模型
    print('載入預訓練模型...')
    model = r3d_18(weights=R3D_18_Weights.KINETICS400_V1)
    
    # 修改最後一層為二分類
    num_features = model.fc.in_features
    model.fc = nn.Linear(num_features, 2)
    
    model = model.to(device)
    print(f'模型參數數量: {sum(p.numel() for p in model.parameters()):,}\n')
    
    # 訓練模型
    print('開始訓練...\n')
    train_losses, train_accs, val_losses, val_accs = train_model(
        model, train_loader, val_loader, num_epochs=20, learning_rate=0.001
    )
    
    print('\n訓練完成!')
    print(f'最佳驗證準確率: {max(val_accs):.2f}%')
    print('模型已儲存為: table_tennis_model.pth')

if __name__ == '__main__':
    main()

