
import asyncio
import socketio
import base64
import io

class WebSocket:
    def __init__(self, url, namespace, enabled=False):
        # self.sio = socketio.Client(logger=True, engineio_logger=True)
        self.sio = socketio.Client()
        self.url = url
        self.namespace = namespace
        self.uri = url +"/" + namespace
        self.ws_connected = False
        self.ws_enabled = enabled

    def setup(self):
        if self.ws_enabled:
            self.call_backs()
            print(f"Connecting to WebSocket on: {self.uri}")
            self.sio.connect(self.url, namespaces=[self.namespace], wait_timeout=2)
            # self.sio.wait()

    def encode_image_data(self, image_data):
        img_str = base64.b64encode(image_data.getvalue())
        return "data:image/jpeg;base64," + img_str.decode()

    def send_data(self, pygame, screen, image_data):
        if self.ws_enabled and self.sio.connected:
            try:
                pygame.image.save(self.scene.screen, image_data, "JPEG")
                img_data_str = self.encode_image_data(image_data)
                t = datetime.datetime.now()
                # self.sio.start_background_task(self.sio.emit, 'op_frame', {'frame_data': img_data_str, 'time':datetime.datetime().now().ctime()})
                # self.sio.emit(event='op_frame', data={'frame_data': img_data_str, 'time_ms': time.mktime(t.timetuple()), "datetime": t.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}, namespace=self.namespace)
                self.sio.emit(event='op_frame', data={'frame_data': img_data_str}, namespace=self.namespace)
                # self.sio.emit(event='op_frame', data={"WHAT":"what"}, namespace=self.namespace)
                # self.sio.emit('op_frame', {'frame_data': '', 'time_ms': time.mktime(t.timetuple()), "datetime": t.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}, namespace=self.namespace)
                # self.sio.wait()
            except Exception as e:
                print(f"Error sending data to socket {e}")
        else:
            pass
            # print(f"WS NOT CONNECTED!")

    def call_backs(self):
        @self.sio.event
        def connect():
            print(f"Connected to to WebSocket on: {self.uri}")

        @self.sio.on("docs")
        def raw_data(data):
            print(f"Data Received!")
            # print(f"Data Received {data}")


        @self.sio.event
        def auth(data):
            print(f"Data Received")
            # print(f"Data Received {data}")

        @self.sio.event
        def disconnect():
            pass

    def draw_debug(self, logger, start_pos, debug=False):
        dbg_str = "WebSocket "
        if not self.ws_enabled:
            dbg_str += "Disabled"
        else:
            dbg_str += "Connected " if self.ws_connected else "NOT Connected"
        start_pos = logger.add_text_line(dbg_str, (255, 50, 0), start_pos)

