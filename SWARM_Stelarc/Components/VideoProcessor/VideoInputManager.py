from ..Utils.FPSCounter import FPSCounter
from ..SwarmComponentMeta import SwarmComponentMeta
from sys import platform
import time
from collections import deque
import threading

class VideoInputManager(SwarmComponentMeta):
    def __init__(self, logger, tasks_manager, screen_w=500, screen_h=500, start_capture_index=0, multi_threaded=True):
        self.screen_w = screen_w
        self.screen_h = screen_h
        super(VideoInputManager, self).__init__(logger, tasks_manager, "VideoInputManager")
        import cv2
        self.cv2 = cv2
        self.cap = None
        self.capture_index = start_capture_index
        self.max_capture_index = 10
        self.buffer_size = 3
        self.frame_buffer = deque([])
        self.frame_shape = None
        self.frame_size = (0,0)
        self.fps_counter = FPSCounter()
        self.last_fps = 0
        self.multi_threaded = multi_threaded
        self.background_task = None
        if self.multi_threaded:
            self.background_task = self.tasks_manager.add_task("VI_start", None, self.setup_capture, None).start()
            self.frame_read_lock = self.background_task.read_lock
        else:
            self.setup_capture()

    def update_frame(self, tasks_manager=None):
        if self.cap is not None:
            if len(self.frame_buffer) >= self.buffer_size:
                return True
            grabbed, frame = self.cap.read()
            self.frame_shape = frame.shape
            with self.frame_read_lock:
                self.frame_buffer.append(frame)
            self.fps_counter.frame_count += 1
            self.fps_counter.update()
            self.last_fps = self.fps_counter.fps
        return True
        
    def setup_capture(self, tasks_manager=None):
        while True:
            try:
                if platform == "win32":
                    self.cap = self.cv2.VideoCapture(self.capture_index, self.cv2.CAP_DSHOW)
                else:
                    # On MacOS, make sure to install opencv with "brew install opencv" and then link it with "brew link --overwrite opencv"
                    # Also remove CAP_DSHOW for MacOS
                    self.cap = self.cv2.VideoCapture(self.capture_index, self.cv2.CAP_AVFOUNDATION)
                time.sleep(1)
                if self.cap.isOpened():  # Checks the stream
                    print(f"VideoCapture {self.capture_index} OPEN")
                    break
                else:
                    print(f"VideoCapture {self.capture_index} CLOSED")
                    self.capture_index += 1
                if self.capture_index > self.max_capture_index:
                    break
            except Exception as e:
                print(f"Exception opening VideoCapture {self.capture_index}: {e}")
                return

        self.cap.set(self.cv2.CAP_PROP_BUFFERSIZE, 3)
        self.cap.set(self.cv2.CAP_PROP_FRAME_WIDTH, self.screen_w)
        self.cap.set(self.cv2.CAP_PROP_FRAME_HEIGHT, self.screen_h)
        self.frame_size = (int(self.cap.get(self.cv2.CAP_PROP_FRAME_WIDTH)), int(self.cap.get(self.cv2.CAP_PROP_FRAME_HEIGHT)))
        if self.multi_threaded:
            self.background_task = self.tasks_manager.add_task("VI", None, self.update_frame, None, None).start()
            self.frame_read_lock = self.background_task.read_lock
        return False
    
    def update_config(self):
      pass
        
    def update_config_data(self, data, last_modified_time):
      pass

    def get_last_frame(self):
        if len(self.frame_buffer) > 0:
            with self.frame_read_lock:
                return self.frame_buffer.popleft()
        return None
  
    def get_frame(self):
        if self.multi_threaded:
            return self.get_last_frame()
        return self.get_last_frame()
    
    def update(self, debug=False):
        if debug:
            print(f"Updating VideoInput Manager")
        if not self.multi_threaded:
            self.update_frame()
        self.cv2.waitKey(1)
    
    def draw(self, left_text_pos, debug=False):
        if debug:
            print(f"Drawing VideoInput Manager")
        left_text_pos = self.logger.add_text_line(f"VI - FPS: {self.last_fps}, Frame Buffer: {len(self.frame_buffer)}, Size: {self.frame_shape}", (255, 255, 0), left_text_pos)