from .Utils import utils
import os

local_config_folder = "./Config"
online_config_folder = "./Online_Config"

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
      self.current_config_folder = None
      self.update_config_data_callback = update_config_data_callback if update_config_data_callback is not None else self.update_config_data

   def init(self):
      pass

   def update_config(self):
      pass

   def get_config_file(self, app_logger, filename):
      if not os.path.exists(self.current_config_folder):
         app_logger.info(f"Creating new config folder file {self.current_config_folder}")
         os.makedirs(self.current_config_folder)
      file_path = f"{self.current_config_folder}/{filename}"
      if os.path.exists(file_path):
         return file_path
      return None


   def update_config_from_file(self, app_logger, tag, filename, last_modified_time):
      if self.current_config_folder is None:
         self.current_config_folder = online_config_folder
         file_path = self.get_config_file(app_logger, filename)
         if file_path is None:
            self.current_config_folder = local_config_folder
         app_logger.critical(f"Reading config file {filename}, from folder {self.current_config_folder}")
      file_path = self.get_config_file(app_logger, filename)
      utils.update_config_from_file(app_logger, tag, file_path, last_modified_time, self.update_config_data_callback)

   def update_config_data(self, config_data, last_modified_time):
      print(f"Warning! No update_config_data set for {self.tag}")
      pass

   def update(self):
      pass

   def draw(self):
      pass
