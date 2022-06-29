import sys
import cv2
import time

capture_index = 0
max_capture_index = 10
vc = None
while True:
    try:
        # On MacOS, make sure to install opencv with "brew install opencv" and then link it with "brew link --overwrite opencv"
        # Also remove CAP_DSHOW for MacOS
        # vc = cv2.VideoCapture(capture_index, cv2.CAP_DSHOW)
        vc = cv2.VideoCapture(capture_index, cv2.CAP_AVFOUNDATION)
        time.sleep(1)
        if vc.isOpened():  # Checks the stream
            print(f"VideoCapture {capture_index} OPEN")
            break
        else:
            print(f"VideoCapture {capture_index} CLOSED")
            capture_index += 1
        if capture_index > max_capture_index:
            break
    except Exception as e:
        print(f"Exception opening VideoCapture {capture_index}, stopping...")
        sys.exit()
while True:
    vc.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
    vc.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
    frameSize = (int(vc.get(cv2.CAP_PROP_FRAME_WIDTH)),int(vc.get(cv2.CAP_PROP_FRAME_HEIGHT)))
    result, frame = vc.read()
    cv2.imshow("Test", frame)
    cv2.waitKey(1)