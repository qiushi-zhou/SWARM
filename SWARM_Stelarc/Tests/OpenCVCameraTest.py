import cv2
import threading
import time
import datetime
import numpy as np
from sys import platform

class FPSCounter():
  def __init__(self, reset_time=10):
    self.reset_time = reset_time
    self.fps = 0
    self.frame_count = 0
    self.start_time = 0
    self.last_frame_time = time.time()

  def reset(self):
    self.frame_count = 0
    self.start_time = time.time()
    self.last_frame_time = time.time()

  def time_since_last_update(self):
    return time.time() - self.last_frame_time

  def update(self, new_frames=0):
    if new_frames > 0:
      self.frame_count += new_frames
      self.last_frame_time = time.time()
    elapsed = time.time() - self.start_time
    if elapsed > 0:
      self.fps = int(self.frame_count / (elapsed))
      if elapsed >= self.reset_time:
        self.reset()


class OpenCVCamera:
    def __init__(self, cam_id, size, cam_name=None):
        self.size = size
        self.cam_id = cam_id
        self.cam_name = cam_name
        if self.cam_name is None:
            self.cam_name = f'Camera {cam_id}'
        self.cam = None
        self.last_frame = None
        self.cam = None
        self.fps_counter = FPSCounter()
        self.thread = threading.Thread(target=self.capture_loop, args=[])
        self.thread_started = True
        self._stop = threading.Event()
        self.thread.start()
        self.initialized = False
        self.total_frames = 0
        self.last_thread_name = "None"
        self.frame_shape = [-1, -1]
        self.ready = False

    def capture_loop(self):
        res_str = f"Cap {self.cam_id}\t{self.cam_name}\t{self.thread.name}"
        try:
            if platform == "win32":
                self.cam = cv2.VideoCapture(self.cam_id, cv2.CAP_DSHOW)
            else:
                # On MacOS, make sure to install opencv with "brew install opencv" and then link it with "brew link --overwrite opencv"
                # Also remove CAP_DSHOW for MacOS
                self.cam = cv2.VideoCapture(self.cam_id, cv2.CAP_AVFOUNDATION)
        except Exception as e:
            print(f"Error opening VideoCapture {self.cam_id}")
            pass
        self.initialized = True
        if self.cam is None or not self.cam.isOpened():
            print(res_str +" FAILED")
            self.thread_started = False
            self._stop.set()
            return
        self.ready = True
        print(res_str +" OPENED")
        while self.thread_started:
            self.last_thread_name = threading.current_thread().name
            if self._stop.isSet():
                break
            if self.cam is not None and self.cam.isOpened():
                rval, frame = self.cam.read()
                if frame is not None:
                    self.frame_shape = frame.shape
                    self.last_frame = self.process_frame(frame)
                    self.fps_counter.update(1)
                    self.total_frames = self.total_frames + 1 if self.total_frames < 100 else 0

                time.sleep(0.001)
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
                lines = [f"Cap {self.cam_id} {self.cam_name}: {self.frame_shape[1]} x {self.frame_shape[0]}",
                         f"Frames: {self.total_frames}",
                         f"FPS: {self.fps_counter.fps:.2f} / {self.cam.get(cv2.CAP_PROP_FPS):.2f}",
                         f"{self.last_thread_name} / {threading.activeCount()}"
                         ]
                y_offset = 40
                font_scaling = 0.35
                for idx in range(0, len(lines)):
                    frame = cv2.putText(frame, lines[idx], (10, int(y_offset * (idx+1) * font_scaling)), cv2.FONT_HERSHEY_SIMPLEX, font_scaling, (0, 255, 0), 1, cv2.LINE_AA)

        return frame

class OpenCVCamerasManager:
    def __init__(self, cols=5, max_idx=10):
        self.title = "Cameras Preview"
        self.hd_scaling = 0.25
        self.cols = cols
        self.size = {'width': int(1280 * self.hd_scaling), 'height': int(720 * self.hd_scaling)}
        self.cameras = []
        self.max_idx = max_idx
        self.print_delay = 5
        self.last_print_time = time.time() - ((self.print_delay-1))
        cv2.namedWindow(self.title)

    def init_cameras(self):
        devices = []
        if platform == 'win32':
            from pygrabber.dshow_graph import FilterGraph
            graph = FilterGraph()
            devices = graph.get_input_devices()
            self.print_delay = 1
        max_idx = self.max_idx if len(devices) <= 0 else len(devices)
        for idx in range(0, max_idx):
            cam_name = f'Camera {idx}'
            if idx < len(devices):
                cam_name = devices[idx]
            cam = OpenCVCamera(idx, self.size, cam_name)
            self.cameras.append(cam)

    def get_collage(self):
        total_frames = 0
        vstacks = []
        hstacks = []
        alive_threads = []
        inactive_cams_idx = []
        for i in range(0, len(self.cameras)):
            cam = self.cameras[i]
            if cam.thread.is_alive():
                alive_threads.append(f"{cam.cam_name} {cam.thread.name} {cam.total_frames}")
            if cam.ready:
                frame = cam.get_frame()
                if frame is not None:
                    hstacks.append(frame)
                    total_frames += 1
                if len(hstacks) >= self.cols:
                    try:
                        vstacks.append(np.hstack(hstacks))
                    except Exception as e:
                        print(f"Exception stacking horizontally: {e}")
            else:
                if cam.initialized:
                    inactive_cams_idx.append(i)
        if len(inactive_cams_idx) > 0:
            for cam_idx in inactive_cams_idx:
                del self.cameras[cam_idx]
        if time.time() - self.last_print_time >= self.print_delay:
            self.last_print_time = time.time()
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
            time.sleep(0.001)
            key = cv2.waitKey(1)
            if key == 27:  # exit on ESC
                return
            # print(f"Active threads {threading.activeCount()}", end='\r')

if __name__ == '__main__':
    manager = OpenCVCamerasManager()
    manager.init_cameras()
    manager.start_loop()
