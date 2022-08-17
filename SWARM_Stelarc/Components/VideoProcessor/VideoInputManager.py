from Utils.FPSCounter import FPSCounter
from ..SwarmComponentMeta import SwarmComponentMeta
from sys import platform
import time
import threading

class VideoInputManager(SwarmComponentMeta):
    def __init__(self, logger, screen_w=500, screen_h=500, start_capture_index=0, multi_threaded=True):
        self.screen_w = screen_w
        self.screen_h = screen_h
        super(VideoInputManager, self).__init__(logger, "VideoInputManager")
        import cv2
        self.cv2 = cv2
        self.cap = None
        self.capture_index = start_capture_index
        self.max_capture_index = 10
        self.frame = None
        self.latest_frame = None
        self.frame_size = (0,0)
        self.fps_counter = FPSCounter()
        self.setup_capture()
        self.multi_threaded = multi_threaded
        if self.multi_threaded:
            self.thread_started = False
            self.read_lock = threading.Lock()
            self.start_mt_stream()
            
    def start_mt_stream(self):
        if self.thread_started:
            print('[!] Threaded video capturing has already been started.')
            return None
        self.thread_started = True
        self.thread = threading.Thread(target=self.get_frame_async, args=())
        self.thread.start()
        return self
    
    def get_frame_async(self):
        while self.thread_started:
            grabbed, frame = self.cap.read()
            with self.read_lock:
                self.latest_frame = frame
        
    def setup_capture(self):      
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
    
    def update_config(self):
      pass
        
    def update_config_data(self, data, last_modified_time):
      pass
  
    def get_frame(self):
        return self.frame
    
    def update(self):
        if not self.multi_threaded:
            result, self.frame = self.cap.read()
        else:
            with self.read_lock:
                self.frame = self.latest_frame
        if self.frame is not None:
            self.fps_counter.frame_count += 1
            self.fps_counter.update()
        self.cv2.waitKey(1)
    
    def draw(self, left_text_pos):
        if self.frame is None:
            shape = "NO FRAME"
        else:
            shape = self.frame.shape
        left_text_pos = self.logger.add_text_line(f"Frame size: {shape}, FPS: {self.fps_counter.fps}", (255, 255, 0), left_text_pos)