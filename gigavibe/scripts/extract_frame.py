"""Извлекает один кадр из видео и сохраняет как JPG (источник лица для тестов)."""

import sys

import cv2

src = sys.argv[1] if len(sys.argv) > 1 else "assets/driving/d0.mp4"
dst = sys.argv[2] if len(sys.argv) > 2 else "data/test_from_driving.jpg"
frame_idx = int(sys.argv[3]) if len(sys.argv) > 3 else 15

cap = cv2.VideoCapture(src)
cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
ok, frame = cap.read()
cap.release()
if not ok:
    print("FAIL: не прочитать кадр", src)
    sys.exit(1)
cv2.imwrite(dst, frame)
print("saved", dst, frame.shape)
