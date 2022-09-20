import time
import asyncio

class Status:
  def __init__(self, _id, name, description):
    self.id = _id
    self.name = name
    self.description = description
    self.extra = ''

class Statuses:
    NOT_INITIALIZED = Status(-1, "NOT INITIALIZED", "Socket.io created but not initialized")
    INITIALIZED = Status(0, "INITIALIZED", "Socket.io setup but not connected")
    CONNECTING = Status(1, "CONNECTING", "Socket.io is trying to connect")
    CONNECTED = Status(2, "CONNECTED", "Socket.io connected")
    WAITING = Status(3, "WAITING", "Socket.io connected")
    DISCONNECTED = Status(4, "DISCONNECTED", "Socket.io lost connection")

class WebSocketStatusManager:
  def __init__(self, ws, wait_timeout = 3):
    self.status = Statuses.NOT_INITIALIZED
    self.wait_timeout = wait_timeout
    self.ws = ws

  def is_waiting(self):
      return self.status.id == Statuses.WAITING.id

  def is_ready(self):
      return self.status.id == Statuses.CONNECTED.id

  def set_disconnected(self, info=""):
    if self.status.id != Statuses.DISCONNECTED.id:
      self.set_status(Statuses.DISCONNECTED, f"{self.ws.uri} - {info}")

  def set_connected(self, info=""):
    if self.status.id != Statuses.CONNECTED.id:
      self.set_status(Statuses.CONNECTED, f"{self.ws.uri} - {info}")

  def set_waiting(self, info=""):
    if self.status.id != Statuses.WAITING.id:
      self.set_status(Statuses.WAITING, f"{self.ws.uri} - {info}")

  def get_status_info(self):
    synced = "(SYNCD) " if self.ws.sync_with_server else ""
    return f"{synced}{self.status.name}: {self.status.description}"

  async def attempt_connect(self):
    try:
      self.set_status(Statuses.CONNECTING, self.ws.uri)
      await self.ws.sio.connect(self.ws.url, namespaces=[self.ws.namespace], wait_timeout=self.wait_timeout)
      await asyncio.sleep(self.wait_timeout)
    except Exception as e:
      print(f"Exception trying to connect to {self.ws.url}{self.ws.namespace}: {e}")
      self.set_status(Statuses.DISCONNECTED)
      await asyncio.sleep(3)

  def set_status(self, new_status, extra="", debug=True):
    if debug:
      print(f"{self.ws.tag} {self.status.name} -> {new_status.name}, {extra}")
    self.status = new_status
    self.status.extra = extra

  async def update_status(self):
    if self.ws.sio.connected:
        self.set_connected()
        return
    else:
      if self.status.id in [Statuses.DISCONNECTED.id, Statuses.NOT_INITIALIZED.id]:
        # self.set_disconnected()
        try:
          await self.attempt_connect()
        except Exception as e:
          print(f"Connect loop is already running: {e}")
