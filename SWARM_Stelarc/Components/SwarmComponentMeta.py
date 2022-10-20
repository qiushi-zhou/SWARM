from .Utils import utils


class SwarmComponentMeta:
   def __init__(self, ui_drawer=None, tasks_manager=None, tag="SwarmComponent", config_filename=None,
                update_config_data_callback=None):
      self.ui_drawer = ui_drawer
      self.tasks_manager = tasks_manager
      self.tag = tag
      self.enabled = True
      self.config_filename = config_filename
      self.config_data = None
      self.last_modified_time = -1
      self.update_config_data_callback = update_config_data_callback if update_config_data_callback is not None else self.update_config_data

   def init(self):
      pass

   def update_config(self):
      pass

   def update_config_from_file(self, app_logger, tag, file_path, last_modified_time):
      utils.update_config_from_file(app_logger, tag, file_path, last_modified_time, self.update_config_data_callback)

   def update_config_data(self, config_data, last_modified_time):
      print(f"Warning! No update_config_data set for {self.tag}")
      pass

   def update(self):
      pass

   def draw(self):
      pass
