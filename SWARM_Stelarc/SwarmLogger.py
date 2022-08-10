from utils import Point

class SwarmLogger:
    OPENCV = 'cv'
    PYGAME = 'pygame'
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

    def __init__(self, drawer, canvas, font=None, font_size=20, line_height=-1):
        self.canvas = canvas
        self.drawer = drawer
        self.draw_type = SwarmLogger.PYGAME
        if 'cv2' in drawer.__name__:
            self.draw_type = SwarmLogger.OPENCV
        self.font = font
        self.line_height = line_height
        self.font_size = font_size
        if line_height < 0:
            self.line_height = self.font_size*0.8
        self.buffer = []

    def update_canvas(self, canvas):
        self.canvas = canvas

    def draw_line(self, start, end, color, thickness):
        if self.draw_type == SwarmLogger.OPENCV:
            self.drawer.line(self.canvas, (int(start.x), int(start.y)), (int(end.x), int(end.y)), color, thickness)
        else:
            self.drawer.draw.line(self.canvas, color=color, start_pos=(int(start.x), int(start.y)), end_pos=(int(end.x), int(end.y)), width=thickness)

    def draw_circle(self, center, color, radius, thickness):
        if self.draw_type == SwarmLogger.OPENCV:
            self.drawer.circle(self.canvas, (int(center.x), int(center.y)), radius, color, thickness)
        else:
            self.drawer.draw.circle(self.canvas, color=color, center=(int(center.x), int(center.y)), radius=radius, width=thickness)

    def add_text_line(self, line, color, pos, font=None, line_height=-1):
        if line_height < 0:
            line_height = self.line_height
        self.buffer.append(self.DebugLine(line, color, Point(pos.x, pos.y), font, line_height))
        pos.y += line_height
        # return Point(pos.x, pos.y+line_height)
        return pos

    def flush_text_lines(self):
        print(f"Flushing {len(self.buffer)} lines")
        while len(self.buffer) > 0:
            line = self.buffer.pop()
            text_x = line.pos.x
            text_y = line.pos.y
            if self.draw_type == SwarmLogger.OPENCV:
                self.drawer.putText(self.canvas, line.text, (int(text_x), int(text_y)), 0, line.font_size, line.color, 2)
            else:
                # print(f"{line.text}, {line.pos.x} {line.pos.y}, {line.color}")
                self.canvas.blit(self.font.render(line.text, True, line.color), (int(text_x), int(text_y)))

