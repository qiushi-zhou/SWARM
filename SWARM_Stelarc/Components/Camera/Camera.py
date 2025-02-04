from matplotlib import path
from ..Utils.utils import Point
from .people_graph import PeopleGraph

class Camera:
    def __init__(self, app_logger, id, screen_w, screen_h, config_data, init_graph=True):
        self.app_logger = app_logger;
        if init_graph:
            self.p_graph = PeopleGraph()
        self.id = id
        self.p_graph.edge_threshold = config_data.get("group_distance_threshold", -1)
        self.screen_w = screen_w
        self.screen_h = screen_h
        self.enabled = config_data.get("enabled", False)
        self.anchor = config_data.get("anchor", 'top')
        self.color = config_data.get('color', [0, 0, 255])
        self.path_points = config_data.get("path", [])
        origin_data = config_data.get("origin", {'x': 0, 'y': 0})
        ox, oy = self.parse_point(origin_data)
        self.origin = Point(ox, oy)
        self.path = path.Path([(0,0)])
        if len(self.path_points) > 0:
            self.path_vertices = []
            debug_str = f"Camera Vertices: [ "
            for p in self.path_points:
                x,y = self.parse_point(p)
                debug_str += f"[{x}, {y}], "
                self.path_vertices.append(Point(x+self.origin.x, y+self.origin.y))
            x,y = self.parse_point(self.path_points[0])
            self.path_vertices.append(Point(x+self.origin.x, y+self.origin.y))
            x,y = self.parse_point(self.path_points[len(self.path_points)-1])
            self.path_vertices.append(Point(x+self.origin.x, y+self.origin.y))

            self.app_logger.debug(f"{debug_str} ]")
            self.build_path()
        text_position = config_data.get("text_position", origin_data)
        tx, ty = self.parse_point(text_position)
        self.text_position = Point(tx+10, ty+10)

        self.min_point = Point(screen_w, screen_h)
        self.max_point = Point(-1, -1)
        self.update_minmax()

        self.machine_position = config_data.get("machine_position", None)
        if self.machine_position is None:
            mx = self.min_point.x + ((self.max_point.x - self.min_point.x)/2)
            my = self.max_point.y
            self.machine_position = Point(mx, my)

    def parse_point(self, p):
        x = 0
        y = 0
        try:
            x = int(p['x'])
        except:
            try:
                expr = str(p['x']).lower().split('*')
                if 'w' in expr[0]:
                    x = self.screen_w * float(expr[1])
                else:
                    x = self.screen_h * float(expr[1])
            except:
                x = 0

        try:
            y = float(p['y'])
        except:
            try:
                expr = str(p['y']).lower().split('*')
                if 'w' in expr[0]:
                    y = self.screen_w * float(expr[1])
                else:
                    y = self.screen_h * float(expr[1])
            except:
                y = 0
        return x,y

    def update_config(self, screen_w, screen_h, config_data, reset_graph=False):
        Camera.__init__(self, self.id, screen_w, screen_h, config_data, init_graph=reset_graph)

    def build_path(self):
        vertices = [[v.x, v.y] for v in self.path_vertices]
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
    
    def check_track(self, points, chest_p):
        if not self.enabled:
            return
        for p in points:
            if self.is_in_camera(p.x, p.y):
                self.p_graph.add_node(x=chest_p.x, y=chest_p.y)
                return

    def is_in_camera(self, x=-1, y=-1):
        return self.path.contains_point([x, y])
        # return self.start_x <= x <= self.end_x and self.start_y <= y <= self.end_y
    
    def update_graph(self):
        if not self.enabled:
            return
        self.p_graph.update_graph(machine_pos=self.machine_position)

    def draw_debug(self, logger, draw_graph_data=True, surfaces=None):
        if not self.enabled:
            return
        if len(self.path_vertices) > 0:
            for j in range(0, len(self.path_vertices) - 1):
                p1 = self.path_vertices[j]
                p2 = self.path_vertices[j + 1]
                thickness = 2
                logger.draw_line(p1, p2, self.color, thickness, surfaces)
            self.p_graph.draw_edges(logger, surfaces=surfaces)
            self.p_graph.draw_nodes(logger, surfaces=surfaces)
            self.p_graph.draw_dist_from_machine(logger,
                                                Point(int(self.machine_position.x), int(self.machine_position.y)), surfaces=surfaces)
        if draw_graph_data:
            self.p_graph.draw_debug_text(logger, Point(int(self.text_position.x), int(self.text_position.y)),
                                         camera_n=self.id, surfaces=surfaces)
    def get_data(self):
        data = {}
        data['graph'] = self.p_graph.get_graph_data()
        data['machine_pos'] = {'x': self.machine_position.x, 'y': self.machine_position.y}
        data['camera_path'] = self.path_points
        data['screen'] = {'width': self.screen_w, 'height': self.screen_h}
        return data