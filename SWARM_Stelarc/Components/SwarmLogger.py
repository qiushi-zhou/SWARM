from .Utils.utils import Point
from .GUIManager.SceneManager import SceneManager, SceneDrawerType

class SwarmLogger:
    class DebugLine:
        def __init__(self, text, color, pos, font=None, font_size=0.4, line_height=-1):
            self.text = text
            self.color = color
            self.pos = pos
            self.font = font
            self.font_size = font_size
            self.line_height = line_height
            if line_height < 0:
                self.line_height = self.font_size

    class SurfaceLogger:
        def __init__(self, name, surface):
            self.name = name
            self.surface = surface
            self.line_buffer = []

    def __init__(self):
        self.draw_type = SceneDrawerType.NONE
        self.drawer = None
        self.surfaces = {}
        self.font_size = 20
        self.font = None
        self.line_height = 1

    def set_drawer(self, drawer):
        if 'cv2' in drawer.__name__:
            self.draw_type = SceneDrawerType.OPENCV
        else:
            self.draw_type = SceneDrawerType.PYGAME
        self.drawer = drawer

    def set_font(self, font=None, font_size=20, line_height=-1):
        self.font = font
        self.line_height = line_height
        self.font_size = font_size
        if line_height < 0:
            self.line_height = self.font_size*0.8

    def add_surface(self, surface, name):
        self.surfaces[name] = SwarmLogger.SurfaceLogger(name, surface)

    def loop_surfaces(self, fun, s_names, *args, **kwargs):
        ret = None
        # print(f"loop surfaces {s_names}")
        if s_names is None:
            for s_name in self.surfaces:
                ret = fun(self.surfaces[s_name], *args, **kwargs)
        elif isinstance(s_names, list):
            for s_name in s_names:
                ret = fun(self.surfaces[s_name], *args, **kwargs)
        else:
            ret = fun(self.surfaces[s_names], *args, **kwargs)
        return ret

    def draw_frame(self, bg_color, frame, s_names=None):
        # print(f"Drawing frame on {s_names}")
        return self.loop_surfaces(self.draw_frame_surface, s_names, bg_color, frame)

    def draw_frame_surface(self, surface, bg_color, frame):
        surface.surface.fill(bg_color)
        if frame is not None:
            pgImg = self.drawer.image.frombuffer(frame.tostring(), frame.shape[1::-1], "BGR")
            try:
                surface.surface.blit(pgImg, (0,0))
            except Exception as e:
                print(f"Surface {surface.name} locked during blit: {e}")

    def draw_line(self, start, end, color, thickness, s_names=None):
        # print(f"Drawing line on {s_names}")
        return self.loop_surfaces(self.draw_line_surface, s_names, start, end, color, thickness)

    def draw_line_surface(self, surface, start, end, color, thickness):
        if self.draw_type == SceneDrawerType.OPENCV:
            return self.drawer.line(surface.surface, (int(start.x), int(start.y)), (int(end.x), int(end.y)), color, thickness)
        elif self.draw_type == SceneDrawerType.PYGAME:
            return self.drawer.draw.line(surface.surface, color=color, start_pos=(int(start.x), int(start.y)), end_pos=(int(end.x), int(end.y)), width=thickness)

    def draw_circle(self, center, color, radius, thickness, s_names=None):
        # print(f"Drawing circle on {s_names}")
        return self.loop_surfaces(self.draw_circle_surface, s_names, center, color, radius, thickness)

    def draw_circle_surface(self, surface, center, color, radius, thickness):
        if self.draw_type == SceneDrawerType.OPENCV:
            return self.drawer.circle(surface.surface, (int(center.x), int(center.y)), radius, color, thickness)
        elif self.draw_type == SceneDrawerType.PYGAME:
            return self.drawer.draw.circle(surface.surface, color=color, center=(int(center.x), int(center.y)), radius=radius, width=thickness)

    def add_text_line(self, line, color, pos, font=None, line_height=-1, s_names=None):
        # print(f"Adding text line on {s_names}")
        return self.loop_surfaces(self.add_text_line_surface, s_names, line, color, pos, font, line_height)

    def add_text_line_surface(self, surface, line, color, pos, font=None, line_height=-1):
        if line_height < 0:
            line_height = self.line_height
        surface.line_buffer.append(self.DebugLine(line, color, Point(pos.x, pos.y), font, line_height))
        pos.y += line_height
        return pos

    def flush_text_lines(self, debug=False, draw=True, s_names=None):
        return self.loop_surfaces(self.flush_text_lines_surface, s_names, debug, draw)

    def flush_text_lines_surface(self, surface, debug=False, draw=True):
        if debug:
            print(f"Flushing {surface.name} buffer, Lines: {len(surface.line_buffer)}, draw: {draw}")
        while len(surface.line_buffer) > 0:
            line = surface.line_buffer.pop()
            if draw:
                try:
                    text_x = line.pos.x
                    text_y = line.pos.y
                    if self.draw_type == SceneDrawerType.OPENCV:
                        self.drawer.putText(surface.surface, line.text, (int(text_x), int(text_y)), 0, line.font_size,
                                            line.color, 2)
                    elif self.draw_type == SceneDrawerType.PYGAME:
                        # print(f"{surface.name} {line.text}, {line.pos.x} {line.pos.y}, {line.color}")
                        surface.surface.blit(self.font.render(line.text, True, line.color), (int(text_x), int(text_y)))
                except Exception as e:
                    print(f"Error printing line to surface {surface.name} {e} ({line.text})")
                    pass

