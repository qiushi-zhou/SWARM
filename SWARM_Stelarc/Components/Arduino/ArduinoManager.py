from .Arduino import Arduino
from ..SwarmComponentMeta import SwarmComponentMeta
import datetime
import time


class ArduinoManager(SwarmComponentMeta):
    def __init__(self, app_logger, ui_drawer, tasks_manager, arduino_port="COM4", mockup_commands=True):
        super(ArduinoManager, self).__init__(ui_drawer, tasks_manager, "ArduinoManager", r'ArduinoConfig.yaml',
                                             self.update_config_data)
        self.app_logger = app_logger
        self.multi_threaded = False
        self.background_task = self.tasks_manager.add_task("AR", None, self.update_arduino_status, None)
        self.arduino = Arduino(self.app_logger, port=arduino_port, mockup_commands=mockup_commands)

    def update_config(self):
        super().update_config_from_file(self.app_logger, self.tag, self.config_filename, self.last_modified_time)

    def init(self):
        if not self.multi_threaded:
            if self.background_task.is_running():
                print(f"Stopping {self.background_task.name} background task")
                self.background_task.stop()
        else:
            if not self.background_task.is_running():
                print(f"Starting {self.background_task.name} background task")
                self.background_task.start()

    def update_config_data(self, data, last_modified_time):
        self.config_data = data
        self.arduino.update_config(self.config_data)
        self.last_modified_time = last_modified_time

    def update_arduino_status(self, task_manager=None):
        self.arduino.update_status()
        if self.arduino.status.id != self.arduino.statuses['not_initialized'].id:
            time.sleep(0.1)
        return True

    def update(self, debug=False):
        self.arduino.update_status()

    def draw(self, start_pos, debug=False, surfaces=None):
        if debug:
            print(f"Drawing Arduino Manager")

        arduino = self.arduino
        prefix = "(Normal)"
        color = (0, 255, 0)
        if arduino.mockup_commands:
            prefix = "(Mockup Commands)"
            color = (100, 100, 255)
        if arduino.not_operational:
            prefix = "(Not Operational )"
            color = (255, 0, 0)
        arduino_cmd_dbg = f"{prefix} Last Command: {arduino.last_command}"
        if arduino.last_command is not None:
            arduino_cmd_dbg += f" sent at {arduino.statuses['command_sent'].started_time.strftime('%Y-%m-%d %H:%M:%S')}"

        now = datetime.datetime.now()

        start_pos.y += self.ui_drawer.line_height
        time_str = f"Time of the day: {now.hour:>02d}:{now.minute:>02d}"
        start_pos = self.ui_drawer.add_text_line(time_str, color, start_pos, surfaces)
        start_pos.y -= self.ui_drawer.line_height

        time_str = f"Working Hours {arduino.working_hours[0].tm_hour:>02d}:{arduino.working_hours[0].tm_min:>02d} - {arduino.working_hours[1].tm_hour:>02d}:{arduino.working_hours[1].tm_min:>02d}"
        start_pos = self.ui_drawer.add_text_line(time_str, color, start_pos, surfaces)
        start_pos.y -= self.ui_drawer.line_height

        date_str = f"Day of the week: {now.strftime('%A')}"
        start_pos = self.ui_drawer.add_text_line(date_str, color, start_pos, surfaces)
        start_pos.y -= self.ui_drawer.line_height

        date_str = f"Working Days: {arduino.working_days}"
        start_pos = self.ui_drawer.add_text_line(date_str, color, start_pos, surfaces)
        start_pos.y -= self.ui_drawer.line_height

        start_pos = self.ui_drawer.add_text_line(arduino_cmd_dbg, color, start_pos, surfaces)

        for s_idx in arduino.statuses:
            s = arduino.statuses[s_idx]
            color = (0, 120, 120)
            arduino_status_dbg = "  "
            timeout = s.get_timeout(arduino.mockup_commands, arduino.not_operational)
            remaining = timeout
            if arduino.status.id == s.id:
                color = (0, 180, 255)
                arduino_status_dbg = "> "
                elapsed = (datetime.datetime.now() - s.started_time).seconds
                remaining = timeout - elapsed
            arduino_status_dbg += f"{s.id} "
            arduino_status_dbg += f"{s.title} - "
            if timeout > 0:
                arduino_status_dbg += f" Wait: {remaining} / {timeout} s {s.extra}"
            else:
                arduino_status_dbg += f" Waiting: {remaining} s {s.extra}"

            start_pos = self.ui_drawer.add_text_line(arduino_status_dbg, color, start_pos, surfaces)
            start_pos.y -= self.ui_drawer.line_height
        return
