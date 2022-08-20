import time
class FPSCounter():
    def __init__(self, reset_time=10):
      self.reset_time = reset_time
      self.fps = 0
      self.reset()
      
    def reset(self):
      self.frame_count = 0
      self.start_time = time.time()
      
    def update(self):
      elapsed = time.time() - self.start_time
      self.fps = int(self.frame_count / (elapsed))
      if elapsed >= self.reset_time:
        self.reset()
      
