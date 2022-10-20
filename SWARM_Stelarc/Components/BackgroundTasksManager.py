# -*- coding: utf-8 -*-
import asyncio

from .SwarmComponentMeta import SwarmComponentMeta
import threading


class BackgroundTask:
    def __init__(self, name, init_fun, loop_fun, cleanup_fun, read_lock=None):
        self.init_fun = init_fun
        self.loop_fun = loop_fun
        self.cleanup_fun = cleanup_fun
        self.thread_started = False
        self.name = name
        self.read_lock = threading.Lock() if read_lock is None else read_lock
        self._stop = threading.Event()

    def is_running(self):
        return self.thread_started

    def start(self):
        if self.init_fun is not None:
            self.init_fun()
        if self.thread_started:
            print(f'[!] Threaded {self.name} has already been started.')
            return self
        if self.loop_fun is None:
            print(f'[!] Threaded {self.name} has no background function!')
            return self
        self.thread = threading.Thread(target=self.loop, args=[])
        self.thread_started = True
        self.thread.start()
        return self

    def loop(self):
        running = True
        while self.thread_started and running:
            if self._stop.isSet():
                return
            running = self.loop_fun(self)
            if not running:
                break
        self.stop()

    def stop(self):
        self._stop.set()
        self.thread_started = False
        if self.cleanup_fun is not None:
            self.cleanup_fun()
    def __str__(self):
        return self.name
    def __repr__(self):
        return self.name

class BackgroundTasksManager(SwarmComponentMeta):
    def __init__(self, app_logger, ui_drawer):
        super(BackgroundTasksManager, self).__init__(ui_drawer, self, "BackgroundTasksManager")
        self.tasks = []
        self.app_logger = app_logger

    def add_task(self, name, init_fun, loop_fun, cleanup_fun, read_lock=None):
        task, index = self.get_task(name)
        if index >= 0:
            print(f"Task {name} already added!")
            return task
        task = BackgroundTask(name, init_fun, loop_fun, cleanup_fun, read_lock)
        self.app_logger.debug(f"Adding task {name}")
        self.tasks.append(task)
        return task

    def get_task(self, name):
        for i in range(0, len(self.tasks)):
            task = self.tasks[i]
            if task.name == name:
                return task, i
        return None, -1

    def remove_task(self, name):
        task, i = self.get_task(name)
        if i >= 0:
            self.tasks.pop(i)
            return True
        return False

    def start_task(self, name):
        task, i = self.get_task(name)
        if i >= 0:
            task.start()
            return True
        return False

    def stop_task(self, name):
        task, i = self.get_task(name)
        if i >= 0:
            task.stop()
            return True
        return False

    def stop_all(self):
        for i in range(0, len(self.tasks)):
            task = self.tasks[i]
            task.stop()

    def get_running_tasks(self):
        running_tasks = []
        for i in range(0, len(self.tasks)):
            task = self.tasks[i]
            if task.is_running():
                running_tasks.append(task)
        return running_tasks

    def update_config(self):
        pass

    def update_config_data(self, data, last_modified_time):
        pass

    def update(self, debug=False):
        if debug:
            print(f"Updating BackgroundTasks Manager!")
        pass

    def draw(self, start_pos, debug=True, surfaces=None):
        if debug:
            print(f"Drawing BackgroundTasks Manager!")
        running_tasks = self.get_running_tasks()
        start_pos = self.ui_drawer.add_text_line(f"Tasks: {running_tasks}", (255,0,0), start_pos, surfaces)
        pass
