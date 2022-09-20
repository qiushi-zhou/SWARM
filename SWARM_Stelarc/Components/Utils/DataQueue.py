import datetime
import base64
from .FPSCounter import FPSCounter
from collections import deque

class DataQueue:
    def __init__(self, size=None, target_fps=-1):
        self.fps_counter = FPSCounter()
        self.buffer_size = size
        self.buffer = deque([])
        self.target_fps = target_fps

    def fps(self):
      return self.fps_counter.fps

    def insert_data(self, data):
      if len(self.buffer) >= self.buffer_size:
          return
      if data is None:
        return
      self.buffer.append(data)

    def clear(self):
      self.buffer.clear()

    def discard_next(self):
      self.fps_counter.update()
      if self.is_empty():
        return None
      return self.buffer.popleft()

    def pop_data(self):
      if self.is_empty():
        return None
      # if self.target_fps > 0:
      #   if self.fps() > self.target_fps:
      #     self.fps_counter.update(1)
      #     self.buffer.popleft()
      #     return None
      self.fps_counter.update(1)
      return self.buffer.popleft()

    def time_since_last_pop(self):
      return self.fps_counter.time_since_last_update()

    def is_full(self):
      if len(self.buffer) > self.buffer_size:
        return True
      return False

    def is_empty(self):
      if len(self.buffer) <= 0:
        return True
      return False

    def size(self):
      return self.buffer_size

    def count(self):
      return len(self.buffer)
