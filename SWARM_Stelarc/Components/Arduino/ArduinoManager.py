from .Arduino import Arduino
from ..SwarmComponentMeta import SwarmComponentMeta
import datetime

class ArduinoManager(SwarmComponentMeta):
    def __init__(self, logger, arduino_port="COM4", mockup_commands=True):
        super(ArduinoManager, self).__init__(logger, "ArduinoManager", r'./ArduinoConfig.yaml', self.update_config_data)
        self.arduino = Arduino(port=arduino_port, mockup_commands=mockup_commands)
    
    def update_config(self):
      super().update_config_from_file(self.tag, self.config_filename, self.last_modified_time)
      
    def update_config_data(self, data, last_modified_time):
      self.config_data = data
      self.arduino.update_config(self.config_data)
      self.last_modified_time = last_modified_time      
    
    def update(self, debug=False):
      if debug:
          print(f"Arduino status updated!")
      self.arduino.update_status()
    
    def draw(self, start_pos, debug=False):
      arduino = self.arduino
      prefix = "(Normal)"
      color = (0, 255, 0)
      if arduino.mockup_commands:
          prefix = "(Mockup Commands)"
          color = (0, 0, 255)
      if arduino.not_operational:
          prefix = "(Not Operational )"
          color = (255, 0, 0)
      arduino_cmd_dbg = f"{prefix} Last Command: {arduino.last_command}"
      if arduino.last_command is not None:
          arduino_cmd_dbg += f" sent at {arduino.statuses['command_sent'].started_time.strftime('%Y-%m-%d %H:%M:%S')}"

      now = datetime.datetime.now()

      time_str = f"Time of the day: {now.hour:>02d}:{now.minute:>02d}"
      time_str += f" - Working Hours {arduino.working_hours[0].tm_hour:>02d}:{arduino.working_hours[0].tm_min:>02d} - {arduino.working_hours[1].tm_hour:>02d}:{arduino.working_hours[1].tm_min:>02d}"
      date_str = f"Day of the week: {now.strftime('%A')} - Working Days: {arduino.working_days}"
      start_pos = self.logger.add_text_line(time_str, color, start_pos)
      start_pos = self.logger.add_text_line(date_str, color, start_pos)
      start_pos.y += self.logger.line_height*0.9
      start_pos = self.logger.add_text_line(arduino_cmd_dbg, color, start_pos)
      start_pos.y += self.logger.line_height

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
          else: arduino_status_dbg += f" Waiting: {remaining} s {s.extra}"

          start_pos = self.logger.add_text_line(arduino_status_dbg, color, start_pos)
      return