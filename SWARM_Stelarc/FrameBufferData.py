from Camera import Camera
from utils import Point

class SingleFrameData():
    def __init__(self, cameras=None):
        self.people_in_frame = 0 # Number of people across all cameras
        self.groups_in_frame = 0
        self.avg_people_distance = 0
        self.avg_machine_distance = 0
        if cameras is not None:
            total_avg_distance = 0
            total_avg_machine_distance = 0
            total_cameras = 0
            for camera in cameras:
                if camera.enabled:
                    total_cameras += 1
                    self.people_in_frame += camera.p_graph.n_people
                    self.groups_in_frame += camera.p_graph.n_groups
                    total_avg_distance += camera.p_graph.avg_people_distance
                    total_avg_machine_distance += camera.p_graph.avg_machine_distance
            self.avg_people_distance = total_avg_distance / total_cameras
            self.avg_machine_distance = total_avg_machine_distance / total_cameras

    def update_frame_data(self, cameras=None):
        SingleFrameData.__init__(self, cameras)


class FramesData():
    def __init__(self, total_d=0, avg_d=0, non_zeroes=0, min_d=1000000, max_d=0):
      self.sum = total_d
      self.avg = avg_d
      self.non_zeroes = non_zeroes
      self.min = min_d
      self.max = max_d
      
    def reset(self):
        FramesData.__init__(self)
      
    def update(self, data):
      self.sum += data
      self.non_zeroes += 1 if data > 0 else 0
      self.min = data if data < self.min else self.min
      self.max = data if data > self.max else self.max
      self.avg = self.sum
      if self.non_zeroes > 0:
        self.avg = self.sum / self.non_zeroes
      
  
class FrameBuffer():           
    def __init__(self, buffer_size=10):
        self.frames = [SingleFrameData() for i in range(0, buffer_size)]
        self.frame_to_update_idx = 0
        
        self.people_data = FramesData()
        self.groups_data = FramesData()
        self.distance_data = FramesData()
        self.machine_distance_data = FramesData()        
        
    def add_frame_data(self, cameras):
        self.frames[self.frame_to_update_idx].update_frame_data(cameras)
        self.frame_to_update_idx += 1 
        if self.frame_to_update_idx >= len(self.frames):
          self.frame_to_update_idx = 0
        self.update_framebuffer_data()

    def update_framebuffer_data(self):
        self.people_data.reset()
        self.groups_data.reset()
        self.distance_data.reset()
        self.machine_distance_data.reset()
        for f in self.frames:
          self.people_data.update(f.people_in_frame)
          self.groups_data.update(f.groups_in_frame)
          self.distance_data.update(f.avg_people_distance)
          self.machine_distance_data.update(f.avg_machine_distance)

    def size(self):
        return len(self.frames)