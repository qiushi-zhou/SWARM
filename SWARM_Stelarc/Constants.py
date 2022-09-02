SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
scaling = 1
SCREEN_WIDTH = int(SCREEN_WIDTH*scaling)
SCREEN_HEIGHT = int(SCREEN_HEIGHT*scaling)
# SCREEN_WIDTH = 850
# SCREEN_HEIGHT = 480
import os

openpose_modelfolder = "../openpose/models"
if os.name == 'nt':
  if 'M931' in os.environ['COMPUTERNAME']:
    PATH = 'D:/Coding/GitHub/SWARM'
    start_capture_index = 0
  else:
    PATH = 'C:/Users/Admin/Documents/GitHub/SWARM'
    start_capture_index = 2
  print(f"Using Windows, openpose enabled. Capture index: {start_capture_index}")
else:
  print(f"Using MacBook M1, openpose disabled")
  PATH = '/Users/marinig/Documents/GitHub/SWARM'
  start_capture_index = 0
print("\n")

openpose_modelfolder = f"{PATH}/openpose/models"
max_capture_index = 10
use_processing=True
use_openpose=True

max_cosine_distance = 1
nn_budget = None
nms_max_overlap = 1.0
max_age = 100
n_init = 20
font_size = int(17*scaling)


inner_radius = 50
outer_radius = 200



