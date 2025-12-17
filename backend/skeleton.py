import os
import numpy as np

# 嘗試導入 cv2 和 mediapipe（雲端部署可能沒有這些套件）
try:
    import cv2
    import mediapipe as mp
    MEDIAPIPE_AVAILABLE = True
except ImportError:
    MEDIAPIPE_AVAILABLE = False
    cv2 = None
    mp = None

class PoseExtractor:
    def __init__(self):
        if not MEDIAPIPE_AVAILABLE:
            raise RuntimeError("MediaPipe 未安裝，姿勢提取功能無法使用")
        
        # 初始化 MediaPipe 姿勢檢測器
        self.mp_pose = mp.solutions.pose
        self.mp_drawing = mp.solutions.drawing_utils
        self.pose = self.mp_pose.Pose(
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
            model_complexity=1  # 0=輕量, 1=標準, 2=高精度
        )
        
        # 定義要排除的臉部關鍵點索引（1-10 為臉部，保留0=鼻子）
        self.face_landmark_indices = set(range(1, 11))  # 1-10 為臉部關鍵點，保留0（鼻子）
        
        # 創建包含鼻子和身體的連接線
        self.body_connections = self._create_body_connections()
    
    def _create_body_connections(self):
        # 創建包含鼻子和身體的連接線（只排除其他臉部關鍵點）
        # MediaPipe Pose 的完整連接線
        all_connections = self.mp_pose.POSE_CONNECTIONS
        
        # 保留所有連接線，只要它們不包含除鼻子外的其他臉部關鍵點
        body_connections = []
        for connection in all_connections:
            start_idx, end_idx = connection
            # 如果連接線的兩端都不在排除的臉部關鍵點範圍內，則保留
            if start_idx not in self.face_landmark_indices and \
               end_idx not in self.face_landmark_indices:
                body_connections.append(connection)
        
        # 手動添加鼻子到肩膀的連接線（因為原始連接線中鼻子只連接到臉部關鍵點）
        # 索引 0: 鼻子, 索引 11: 左肩, 索引 12: 右肩
        # 連接到兩個肩膀，使連接更對稱
        body_connections.append((0, 11))  # 鼻子到左肩
        body_connections.append((0, 12))  # 鼻子到右肩
        
        return body_connections
    
    def _draw_body_landmarks(self, image, original_landmarks):
        # 手動繪製鼻子和身體的關鍵點和連接線（只保留鼻子，排除其他臉部）
        h, w, _ = image.shape
        
        # 繪製關鍵點（保留鼻子索引0，排除其他臉部關鍵點1-10）
        for orig_idx, landmark in enumerate(original_landmarks.landmark):
            if orig_idx not in self.face_landmark_indices:  # 保留0（鼻子）和11-32（身體）
                x = int(landmark.x * w)
                y = int(landmark.y * h)
                # 鼻子用不同顏色標示
                if orig_idx == 0:
                    cv2.circle(image, (x, y), 5, (255, 0, 0), -1)  # 藍色圓點（鼻子）
                else:
                    cv2.circle(image, (x, y), 4, (0, 0, 255), -1)  # 紅色圓點（身體）
        
        # 繪製連接線（包含鼻子與身體的連接）
        for connection in self.body_connections:
            start_idx, end_idx = connection
            start_landmark = original_landmarks.landmark[start_idx]
            end_landmark = original_landmarks.landmark[end_idx]
            
            start_x = int(start_landmark.x * w)
            start_y = int(start_landmark.y * h)
            end_x = int(end_landmark.x * w)
            end_y = int(end_landmark.y * h)
            
            cv2.line(image, (start_x, start_y), (end_x, end_y), (0, 255, 0), 2)  # 綠色線條
    
    def extract_pose_from_video(self, input_video_path, output_video_path=None):
        # 開啟影片
        cap = cv2.VideoCapture(input_video_path)
        
        if not cap.isOpened():
            print(f"錯誤：無法開啟影片 {input_video_path}")
            return
        
        # 獲取影片屬性
        fps = int(cap.get(cv2.CAP_PROP_FPS))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        # 指定輸出路徑，設定影片寫入器
        writer = None
        if output_video_path:
            fourcc = cv2.VideoWriter_fourcc(*'avc1') 
            writer = cv2.VideoWriter(output_video_path, fourcc, fps, (width, height))
        
        
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            
            # 轉換 BGR 到 RGB（MediaPipe 需要 RGB）
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # 檢測姿勢
            results = self.pose.process(rgb_frame)
            
            # 創建黑色背景（只儲存骨架，不儲存原始影片內容）
            annotated_frame = np.zeros((height, width, 3), dtype=np.uint8)
            
            if results.pose_landmarks:
                # 手動繪製身體和四肢的關鍵點和連接線（排除臉部）
                self._draw_body_landmarks(annotated_frame, results.pose_landmarks)
            

            # 如果指定輸出路徑，寫入影片
            if writer:
                writer.write(annotated_frame)
            else:
                # 顯示即時預覽
                cv2.imshow('Pose Extraction', annotated_frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
        
        # 清理資源
        cap.release()
        if writer:
            writer.release()
        cv2.destroyAllWindows()


    # 提取姿勢數據（關鍵點座標）並返回
    def extract_pose_data(self, input_video_path):
        cap = cv2.VideoCapture(input_video_path)
        pose_data = []
        
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self.pose.process(rgb_frame)
            
            frame_data = {
                'frame_number': len(pose_data),
                'landmarks': None
            }
            
            if results.pose_landmarks:
                landmarks = []
                # 只提取鼻子和身體的關鍵點（排除其他臉部關鍵點）
                for idx, landmark in enumerate(results.pose_landmarks.landmark):
                    if idx not in self.face_landmark_indices:  # 保留0（鼻子）和11-32（身體）
                        landmarks.append({
                            'index': idx,
                            'x': landmark.x,
                            'y': landmark.y,
                            'z': landmark.z,
                            'visibility': landmark.visibility
                        })
                frame_data['landmarks'] = landmarks
            
            pose_data.append(frame_data)
        
        cap.release()
        return pose_data


def main(input_folder, output_folder):
  
    extractor = PoseExtractor()
    
    # 確保輸出目錄存在
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
        print(f"已創建輸出目錄: {output_folder}")
    
    # 取得資料夾內所有影片檔案（只抓副檔名符合的）
    video_files = [
        f for f in os.listdir(input_folder)
        if f.lower().endswith((".mp4", ".avi", ".mov", ".mkv"))
    ]

    if not video_files:
        print(f"資料夾 {input_folder} 中沒有找到影片檔案")
        return


    # 依序處理每個影片
    i = 1
    for filename in video_files:
        input_video = os.path.join(input_folder, filename)
        
        # 使用數字編號來命名輸出檔案 (1.mp4, 2.mp4, 3.mp4...)
        output_video = os.path.join(output_folder, f"{i}.mp4")
        # 提取骨架並儲存到輸出影片
        extractor.extract_pose_from_video(input_video, output_video)
        print(f"{input_video}處理完成")
        i += 1
    
    print(f"\n✓ 資料夾 {input_folder} 處理完成！")
    print("=" * 50)


if __name__ == "__main__":
    main("good_input_movid", "good_output_movid")
    main("normal_input_movid", "normal_output_movid")
    main("bad_input_movid", "bad_output_movid")
    