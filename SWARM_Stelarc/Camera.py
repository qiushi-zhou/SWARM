from people_graph import *
from matplotlib import path
from utils import Point

class Camera:
    def __init__(self, screen_w, screen_h, config_data):
        self.screen_w = screen_w
        self.screen_h = screen_h
        self.p_graph = PeopleGraph()
        self.update_config(config_data)
    
        # q_col = 0 if (i % 2) == 0 else 1
        # q_row = 0 if i < 2 else 1
        # start_x = 0 if q_col <= 0 else Constants.SCREEN_WIDTH / 2
        # end_x = Constants.SCREEN_WIDTH / 2 if q_col <= 0 else Constants.SCREEN_WIDTH
        # start_y = 0 if q_row <= 0 else Constants.SCREEN_HEIGHT / 2
        # end_y = Constants.SCREEN_HEIGHT / 2 if q_row <= 0 else Constants.SCREEN_HEIGHT

        # start_x += Constants.SCREEN_WIDTH * self.cameras_padding
        # end_x -= Constants.SCREEN_WIDTH * self.cameras_padding
        # start_y += Constants.SCREEN_HEIGHT * self.cameras_padding
        # end_y -= Constants.SCREEN_HEIGHT * self.cameras_padding
        
    def update_config(self, config_data):
        self.enabled = config_data.get("enabled", self.enabled)
        self.origin = config_data.get("origin", self.origin)
        self.anchor = config_data.get("anchor", self.anchor)
        
        self.path_points = config_data.get("path", self.path_points)
        self.path_vertices = [Point(p['x'], p['y']) for p in self.path_points]
        self.build_path()
        
        self.min_point = Point(screen_w, screen_h)
        self.max_point = Point(-1, -1)
        self.update_minmax()
        
        self.machine_position = config_data.get("machine_position", None)
        if self.machine_position is None:
            mx = self.min_point.x + ((self.max_point.x - self.min_point.x)/2)
            my = self.max_point.y
            self.machine_position = Point(mx, my)        
        
    def build_path(self):
        vertices = [(p.x, p.y) for vertex in self.path_vertices]
        self.path = path.Path(vertices)
        
    def update_minmax(self):        
        for vertex in self.path_vertices:
            if vertex.x > self.max_point.x:
                self.max_point.x = vertex.x
            if vertex.y > self.max_point.y:
                self.max_point.y = vertex.y
            if vertex.x < self.min_point.x:
                self.min_point.x = vertex.x
            if vertex.y < self.min_point.y:
                self.min_point.y = vertex.y
    
    def check_track(self, min_p, chest_p):
        if self.is_in_camera(point=min_p):
            self.people_graph.add_node(x=chest_p.x, y=chest_p.y)
        
    def is_in_camera(self, x=-1, y=-1, point=None):
        if point is None:
            point = (x,y)
        return self.path.contains_point(point)
        # return self.start_x <= x <= self.end_x and self.start_y <= y <= self.end_y
    
    def update_graph(self):
        self.p_graph.update_graph(machine_pos=self.machine_position)