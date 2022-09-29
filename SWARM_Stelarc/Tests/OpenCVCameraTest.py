import cv2
import threading
import time
import datetime
from SWARM_Stelarc.Components.Utils.FPSCounter import FPSCounter
import numpy as np

class OpenCVCamera:
    def __init__(self, cam_id, size):
        self.size = size
        self.cam_id = cam_id
        self.cam = None
        self.last_frame = None
        self.cam = None
        self.fps_counter = FPSCounter()
        self.thread = threading.Thread(target=self.capture_loop, args=[])
        self.thread_started = True
        self._stop = threading.Event()
        self.thread.start()
        self.initialized = False

    def capture_loop(self):
        try:
            self.cam = cv2.VideoCapture(self.cam_id)
        except Exception as e:
            pass
        if self.cam is None or not self.cam.isOpened():
            self.initialized = False
            print(f"Capture {self.cam_id} on Thread {self.thread.name} FAILED")
            self.thread_started = False
            self._stop.set()
            return
        self.initialized = True
        print(f"Capture {self.cam_id} on Thread {self.thread.name} OPENED")
        while self.thread_started:
            if self._stop.isSet():
                break
            if self.cam is not None and self.cam.isOpened():
                rval, frame = self.cam.read()
                if frame is not None:
                    self.last_frame = self.process_frame(frame)
                    self.fps_counter.update(1)
                time.sleep(0.01)
        self.cam.release()

    def process_frame(self, frame, dbg_info=True):
        b_size = 5
        if frame is not None:
            frame = cv2.resize(frame, (self.size['width'], self.size['height']))
            frame = cv2.copyMakeBorder(frame, top=b_size, bottom=b_size, left=b_size, right=b_size, borderType=cv2.BORDER_CONSTANT, value=[255, 255, 255])
        return frame

    def get_frame(self, dbg_info=True):
        frame = None
        if self.last_frame is not None:
            frame = self.last_frame.copy()
            if dbg_info:
                dbg_string = f"Capture {self.cam_id}. FPS: {self.fps_counter.fps:.2f}. {threading.current_thread().name} / {threading.activeCount()}"
                frame = cv2.putText(frame, dbg_string, (10,20),  cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0,255,0), 1, cv2.LINE_AA)
        return frame

class OpenCVCamerasManager:
    def __init__(self, cols=5, max_idx=10):
        self.title = "Cameras Preview"
        self.hd_scaling = 0.25
        self.cols = cols
        self.size = {'width': int(1280 * self.hd_scaling), 'height': int(720 * self.hd_scaling)}
        self.cameras = []
        self.max_idx = max_idx
        cv2.namedWindow(self.title)

    def init_cameras(self):
        for idx in range(0, self.max_idx):
            cam = OpenCVCamera(idx, self.size)
            self.cameras.append(cam)
    def get_collage(self):
        total_frames = 0
        vstacks = []
        hstacks = []
        alive_threads = []
        for cam in self.cameras:
            if cam.thread.is_alive():
                alive_threads.append(f"{cam.cam_id} {cam.thread.name}")
            if cam.initialized:
                frame = cam.get_frame()
                if frame is not None:
                    hstacks.append(frame)
                    total_frames += 1
                if len(hstacks) >= self.cols:
                    try:
                        vstacks.append(np.hstack(hstacks))
                    except Exception as e:
                        print(f"Exception stacking horizontally: {e}")
        print(f"{datetime.datetime.now()}\tGrid {total_frames} : {len(hstacks)} x {len(vstacks)} \t{len(alive_threads)} / {len(self.cameras)} Alive Threads\t{alive_threads}", end='\n', flush=True)
        try:
            vstacks.append(np.hstack(hstacks))
            return np.vstack(vstacks)
        except Exception as e:
            # print(f"Exception Building collage: {e}")
            pass

    def start_loop(self):
        while True:
            output = None
            try:
                output = self.get_collage()
                cv2.imshow(self.title, output)
            except Exception as e:
                # print(f"Exception getting collage: {e}")
                pass
            time.sleep(0.01)
            key = cv2.waitKey(1)
            if key == 27:  # exit on ESC
                return
            # print(f"Active threads {threading.activeCount()}", end='\r')

if __name__ == '__main__':
    manager = OpenCVCamerasManager()
    manager.init_cameras()
    manager.start_loop()
