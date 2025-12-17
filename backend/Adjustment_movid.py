import os
import random
import cv2
import numpy as np


def ensure_dir(path: str):
    """確保資料夾存在。"""
    if not os.path.exists(path):
        os.makedirs(path, exist_ok=True)


def random_augmentation_params():
    """
    產生單次增強使用的隨機參數：
    - 旋轉角度：-5 ~ +5 度
    - 水平位移：-200 ~ +200 像素
    - 縮放倍率：輕微隨機縮放，例如 0.9 ~ 1.1
    """
    angle = random.uniform(-5.0, 5.0)
    tx = random.uniform(-200.0, 200.0)  # 左右平移
    scale = random.uniform(0.9, 1.1)
    return angle, tx, scale


def augment_frame(frame: np.ndarray, angle: float, tx: float, scale: float) -> np.ndarray:
    """對單張影格做旋轉 + 水平平移 + 輕微縮放。"""
    h, w = frame.shape[:2]
    center = (w / 2.0, h / 2.0)

    # 取得旋轉 + 縮放矩陣
    M = cv2.getRotationMatrix2D(center, angle, scale)

    # 加入水平位移（tx）；只移動 x 方向
    M[0, 2] += tx

    # 進行仿射變換，邊界用黑色補
    augmented = cv2.warpAffine(frame, M, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0))
    return augmented


def augment_video(input_path: str, output_path: str, angle: float, tx: float, scale: float):
    """讀取一部影片並用固定的隨機參數做整部影片的增強後輸出。"""
    cap = cv2.VideoCapture(input_path)
    if not cap.isOpened():
        print(f"無法開啟影片: {input_path}")
        return

    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    # 使用與其他程式相同的編碼器 'avc1'
    fourcc = cv2.VideoWriter_fourcc(*"avc1")
    writer = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    if not writer.isOpened():
        print(f"無法建立輸出影片: {output_path}")
        cap.release()
        return

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        aug_frame = augment_frame(frame, angle, tx, scale)
        writer.write(aug_frame)

    cap.release()
    writer.release()
    print(f"完成增強並輸出: {output_path}")


def process_folder(input_folder: str, output_folder: str, num_aug: int = 5):
    """
    對資料夾中的每一支 mp4 影片做 num_aug 次隨機增強：
    - 每支原始影片會產生 num_aug 個新影片
    - 檔名格式：1.mp4, 2.mp4, 3.mp4, ...
    """
    ensure_dir(output_folder)

    video_files = [
        f
        for f in os.listdir(input_folder)
        if f.lower().endswith(".mp4")
    ]

    if not video_files:
        print(f"資料夾 {input_folder} 中沒有找到 mp4 影片")
        return

    print(f"開始處理資料夾: {input_folder}，共 {len(video_files)} 個影片")

    counter = 1  # 從 1 開始編號

    for filename in video_files:
        input_path = os.path.join(input_folder, filename)

        for i in range(num_aug):
            angle, tx, scale = random_augmentation_params()
            output_name = f"{counter}.mp4"
            output_path = os.path.join(output_folder, output_name)

            print(
                f"處理 {input_path} -> {output_path} | "
                f"angle={angle:.2f}, tx={tx:.1f}, scale={scale:.3f}"
            )
            augment_video(input_path, output_path, angle, tx, scale)
            counter += 1  # 遞增計數器

    print(f"✓ 資料夾 {input_folder} 處理完成，輸出到 {output_folder}")


def main():
    # 根據需求處理 bad / good 資料夾
    process_folder("bad", "bad_output_movid", num_aug=5)
    process_folder("good", "good_output_movid", num_aug=5)


if __name__ == "__main__":
    main()


