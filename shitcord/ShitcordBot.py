import websocket
import threading
import requests
import random
import time
import json
import rel

class ShitcordBot:
    def __init__(self, **kwargs):
        self.config = {
            "token": None,
            "intents": 1,
            "debug": False,
            "api_version": 10,
            **kwargs
        }
        self.__check_required()

        self.subscribed_events = {}
        self.subscribed_ops = {}

        self.connection_state = {
            "sequence": None,
            "connected": False,
            "heartbeat_interval": None,
            "authenticated": False
        }

        self.__setup_websocket()
        
        self._subscribe_op(10, self.__on_gateway_hello)
        self._subscribe_op(0, self.__on_gateway_event)

        self.subscribe_event("READY", self.__on_gateway_ready)
    
    def __print_debug(self, *message):
        if self.config["debug"]:
            print(*message)

    def __check_required(self):
        if not self.config["token"]:
            raise ValueError("Token is required")
    
    def __setup_websocket(self):
        self.ws = websocket.WebSocketApp(f"wss://gateway.discord.gg/?v={self.config['api_version']}&encoding=json",
            on_open=self.__ws_on_open,
            on_message=self.__ws_on_message,
            on_error=self.__ws_on_error,
            on_close=self.__ws_on_close)
    
    def __heartbeat(self):
        time.sleep(self.connection_state["heartbeat_interval"] * random.random())

        while self.connection_state["connected"]:
            self.ws.send(json.dumps({
                "op": 1,
                "d": self.connection_state["sequence"]
            }))
            time.sleep(self.connection_state["heartbeat_interval"])
    
    def __on_gateway_hello(self, data):
        self.connection_state["heartbeat_interval"] = data["d"]["heartbeat_interval"]
        threading.Thread(
            target=self.__heartbeat,
            daemon=True
        ).start()
        self.ws.send(json.dumps({
            "op": 2,
            "d": {
                "token": self.config["token"],
                "intents": self.config["intents"],
                "properties": {
                    "$os": "linux",
                }
            }
        }))

    def __on_gateway_ready(self, data):
        self.connection_state["authenticated"] = True
        self.__print_debug("Authenticated as", data["d"]["user"]["username"])

    def __on_gateway_event(self, data):
        if data["t"] in self.subscribed_events:
            for callback in self.subscribed_events[data["t"]]:
                callback(data)
        else:
            self.__print_debug("Unhandled event", data["t"])

        if "s" in data:
            self.connection_state["sequence"] = data["s"]

    def __send_restful(self, method, endpoint, data=None):
        api_url = f"https://discord.com/api/v{self.config['api_version']}{endpoint}"
        headers = {
            "Authorization": f"Bot {self.config['token']}"
        }
        response = requests.request(method, api_url, headers=headers, json=data)
        return response

    def __ws_on_message(self, ws, message):
        data = json.loads(message)
        opcode = data["op"]

        if opcode in self.subscribed_ops:
            self.subscribed_ops[opcode](data)
        
    def __ws_on_error(self, ws, error):
        print(error)

    def __ws_on_open(self, ws):
        self.connection_state["connected"] = True
        self.__print_debug("Connected")
    
    def __ws_on_close(self, ws, close_status_code, close_msg):
        self.connection_state["connected"] = False
        self.__print_debug("Disconnected")

    def _subscribe_op(self, opcode, callback):
        self.subscribed_ops[opcode] = callback
    
    def subscribe_event(self, event, callback):
        if event not in self.subscribed_events:
            self.subscribed_events[event] = []
        self.subscribed_events[event].append(callback)

    def run_forever(self):
        self.ws.run_forever(dispatcher=rel, reconnect=5)
        rel.signal(2, rel.abort)
        rel.dispatch()

    def update_channel(self, channel_id, name) -> requests.Response:
        return self.__send_restful("PATCH", f"/channels/{channel_id}", {
            "name": name
        })
    
    def get_channel(self, channel_id) -> requests.Response:
        return self.__send_restful("GET", f"/channels/{channel_id}")