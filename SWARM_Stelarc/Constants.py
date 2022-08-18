SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
scaling = 1
SCREEN_WIDTH = int(SCREEN_WIDTH*scaling)
SCREEN_HEIGHT = int(SCREEN_HEIGHT*scaling)
# SCREEN_WIDTH = 850
# SCREEN_HEIGHT = 480
import os

if os.name == 'nt':
  print(f"Using Windows, openpose enabled")
  use_openpose = True
  PATH = 'C:/Users/Admin/Documents/GitHub/SWARM'
  openpose_modelfolder = "C:/Users/Admin/Documents/GitHub/SWARM/openpose/models"
  start_capture_index = 2
else:
  print(f"Using MacBook M1, openpose disabled")
  use_openpose = False
  PATH = '/Users/marinig/Documents/GitHub/SWARM'
  openpose_modelfolder = "/Users/marinig/Documents/GitHub/SWARM/openpose/models"
  start_capture_index = 0
print("\n")
max_capture_index = 10  


max_cosine_distance = 1
nn_budget = None
nms_max_overlap = 1.0
max_age = 100
n_init = 20
font_size = int(17*scaling)


draw_openpose = True
draw_graph = True
draw_cameras_data = True
draw_behavior_data = True
draw_map = False

inner_radius = 50
outer_radius = 200



