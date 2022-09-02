from ..Utils.FPSCounter import FPSCounter
from ..SwarmComponentMeta import SwarmComponentMeta
from sys import platform
import time
from collections import deque
import threading

class VideoInputManager(SwarmComponentMeta):
    def __init__(self, logger, tasks_manager, screen_w=500, screen_h=500, start_capture_index=0):
        self.screen_w = screen_w
        self.screen_h = screen_h
        super(VideoInputManager, self).__init__(logger, tasks_manager, "VideoInputManager")
        import cv2
        self.cv2 = cv2
        self.cap = None
        self.capture_index = start_capture_index
        self.max_capture_index = 10
        self.buffer_size = 10
        self.latest_frame = None
        self.frame_buffer = deque([])
        self.frame_shape = None
        self.frame_size = (0,0)
        self.fps_counter = FPSCounter()
        self.multi_threaded = False
        self.background_task = self.tasks_manager.add_task("VI", None, self.capture_frame, None)
        self.buffer_lock = self.background_task.buffer_lock

    def init(self):
        pass

    def set_mt(self, enabled):
        if enabled:
            if not self.multi_threaded:
                self.background_task.start()
            self.multi_threaded = True
            return

        if self.multi_threaded:
            self.background_task.stop()
        self.multi_threaded = False

    def capture_frame(self, tasks_manager=None, async_loop=None):
        if self.cap is None:
            self.setup_capture()
            return True
        if len(self.frame_buffer) >= self.buffer_size:
            return True
        grabbed, frame = self.cap.read()
        self.frame_shape = frame.shape
        with self.buffer_lock:
            self.frame_buffer.append(frame)
        self.fps_counter.update(new_frames=1)
        return True
        
    def setup_capture(self, tasks_manager=None, async_loop=None):
        while True:
            try:
                if platform == "win32":
                    self.cap = self.cv2.VideoCapture(self.capture_index, self.cv2.CAP_DSHOW)
                else:
                    # On MacOS, make sure to install opencv with "brew install opencv" and then link it with "brew link --overwrite opencv"
                    # Also remove CAP_DSHOW for MacOS
                    self.cap = self.cv2.VideoCapture(self.capture_index, self.cv2.CAP_AVFOUNDATION)
                time.sleep(0.1)
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
                self.cap = None
                return False

        self.cap.set(self.cv2.CAP_PROP_BUFFERSIZE, 3)
        self.cap.set(self.cv2.CAP_PROP_FRAME_WIDTH, self.screen_w)
        self.cap.set(self.cv2.CAP_PROP_FRAME_HEIGHT, self.screen_h)
        self.frame_size = (int(self.cap.get(self.cv2.CAP_PROP_FRAME_WIDTH)), int(self.cap.get(self.cv2.CAP_PROP_FRAME_HEIGHT)))
        return False
    
    def update_config(self):
      pass
        
    def update_config_data(self, data, last_modified_time):
      pass
  
    def get_frame(self):
        if len(self.frame_buffer) <= 0:
            return None
        if self.multi_threaded:
            with self.buffer_lock:
                self.latest_frame = self.frame_buffer.popleft()
        return self.latest_frame
    
    def update(self, debug=False):
        if debug:
            print(f"Updating VideoInput Manager")
        if not self.multi_threaded:
            self.capture_frame()
        self.cv2.waitKey(1)
    
    def draw(self, left_text_pos, debug=False, surfaces=None):
        if debug:
            print(f"Drawing VideoInput Manager")
        left_text_pos = self.logger.add_text_line(f"VI - FPS: {self.last_fps}, Frame Buffer: {len(self.frame_buffer)}, Size: {self.frame_shape}", (255, 255, 0), left_text_pos, surfaces)