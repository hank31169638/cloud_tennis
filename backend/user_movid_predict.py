import torch
import torch.nn as nn
import torchvision.transforms as transforms
from torchvision.models.video import r3d_18, R3D_18_Weights
import cv2
import numpy as np
import os

# 檢查 CUDA 是否可用
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
print(f'使用設備: {device}')
if torch.cuda.is_available():
    print(f'GPU: {torch.cuda.get_device_name(0)}\n')

def load_video_frames(video_path, num_frames=16):
    """從影片中提取固定數量的影格"""
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError(f"無法開啟影片: {video_path}")
    
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    
    print(f'影片資訊: {total_frames} 影格, FPS: {fps:.2f}')
    
    # 計算要提取的影格索引
    if total_frames <= num_frames:
        # 如果影片影格數不足，重複最後一幀
        frame_indices = list(range(total_frames))
        while len(frame_indices) < num_frames:
            frame_indices.append(frame_indices[-1])
    else:
        # 均勻採樣
        frame_indices = np.linspace(0, total_frames - 1, num_frames, dtype=int)
    
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
        
        if len(frames) >= num_frames:
            break
    
    cap.release()
    
    # 如果影格數不足，用最後一幀填充
    while len(frames) < num_frames:
        frames.append(frames[-1] if frames else np.zeros((112, 112, 3), dtype=np.uint8))
    
    # 轉換為 numpy array
    frames = np.array(frames[:num_frames])
    
    return frames

def preprocess_video(video_path, num_frames=16):
    """預處理影片為模型輸入格式"""
    # 載入影格
    frames = load_video_frames(video_path, num_frames)
    
    # 轉換為 tensor
    frames = torch.FloatTensor(frames)
    frames = frames.permute(3, 0, 1, 2)  # (T, H, W, C) -> (C, T, H, W)
    
    # 正規化到 [0, 1]
    frames = frames / 255.0
    
    # 添加 batch 維度
    frames = frames.unsqueeze(0)  # (1, C, T, H, W)
    
    return frames

def load_model(model_path='table_tennis_model.pth'):
    """載入訓練好的模型"""
    # 載入預訓練的 R3D-18 模型
    model = r3d_18(weights=R3D_18_Weights.KINETICS400_V1)
    
    # 修改最後一層為二分類
    num_features = model.fc.in_features
    model.fc = nn.Linear(num_features, 2)
    
    # 載入訓練好的權重
    if os.path.exists(model_path):
        model.load_state_dict(torch.load(model_path, map_location=device))
        print(f'✓ 成功載入模型: {model_path}\n')
    else:
        raise FileNotFoundError(f'找不到模型檔案: {model_path}')
    
    model = model.to(device)
    model.eval()
    
    return model

def predict_video(model, video_path):
    """預測影片的動作是否標準"""
    print(f'正在處理影片: {video_path}\n')
    
    # 預處理影片
    video_tensor = preprocess_video(video_path)
    video_tensor = video_tensor.to(device)
    
    # 進行預測
    with torch.no_grad():
        outputs = model(video_tensor)
        probabilities = torch.nn.functional.softmax(outputs, dim=1)
        predicted_class = torch.argmax(outputs, dim=1).item()
        confidence = probabilities[0][predicted_class].item()
    
    # 結果
    class_names = ['不標準', '標準']
    result = class_names[predicted_class]
    
    print('=' * 50)
    print('預測結果:')
    print(f'  動作: {result}')
    print(f'  信心度: {confidence*100:.2f}%')
    print(f'  不標準機率: {probabilities[0][0].item()*100:.2f}%')
    print(f'  標準機率: {probabilities[0][1].item()*100:.2f}%')
    print('=' * 50)
    
    return result, confidence, probabilities[0].cpu().numpy()

def main():
    # 模型路徑
    model_path = 'table_tennis_model.pth'
    
    # 檢查模型是否存在
    if not os.path.exists(model_path):
        print(f'錯誤: 找不到模型檔案 {model_path}')
        print('請先執行 train.py 來訓練模型')
        return
    
    # 載入模型
    print('載入模型...')
    model = load_model(model_path)
    
    # 預測影片
    video_path = 'test.mp4'
    
    if not os.path.exists(video_path):
        print(f'錯誤: 找不到影片檔案 {video_path}')
        return
    
    try:
        result, confidence, probabilities = predict_video(model, video_path)
        
        # 返回結果
        return {
            'prediction': result,
            'confidence': confidence,
            'probabilities': {
                '不標準': float(probabilities[0]),
                '標準': float(probabilities[1])
            }
        }
    except Exception as e:
        print(f'預測時發生錯誤: {str(e)}')
        import traceback
        traceback.print_exc()
        return None

if __name__ == '__main__':
    main()

