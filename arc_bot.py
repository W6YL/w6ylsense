import threading
import shitcord
import requests
import serial
import time
import json

class InterruptableThread:
    def __init__(self, target=None):
        self.thread = threading.Thread(target=target, daemon=True) if target else threading.Thread(target=self.run, daemon=True)
        self.stop_request = threading.Event()
    
    def run(self):
        self.thread.start()
    
    def stop(self):
        self.stop_request.set()
    
    def join(self):
        try:
            while self.thread.is_alive():
                self.thread.join(timeout=1)
        except (KeyboardInterrupt, SystemExit):
            self.stop()
            self.join()
    
    def is_stop_requested(self):
        return self.stop_request.is_set()

class SerialHandler(InterruptableThread):
    def __init__(self, port, baudrate, bot, **kwargs):
        self.serial = serial.Serial(port, baudrate)
        self.last_time_button_was_pressed = 0
        self.bot: shitcord.ShitcordBot = bot

        self.config = {
            "channel_id": None,
            "usb_retries": 5,
            "press_delay": 120,
            **kwargs
        }

        self.state = {
            "LED_state": False,
            "ignore_next_update": False,
            "USB_retries": 0
        }

        InterruptableThread.__init__(self, target=self.__run)
        
    def __check_status(self, status: requests.Response):
        return status.status_code == 200

    def __handle_press(self):
        # Stop people from spamming the button
        if time.time() - self.last_time_button_was_pressed < self.config["press_delay"]:
            time_remaining = self.config["press_delay"] - (time.time() - self.last_time_button_was_pressed)
            print(f"Button pressed too soon, there is {round(time_remaining,1)}s left")
            self.last_time_button_was_pressed = time.time()
            self.blink_error(2)
            return
        
        # Update the channel
        self.state["ignore_next_update"] = True # Prevent this from doing weird stuff
        status = self.bot.update_channel(self.config["channel_id"], "shack-closed" if self.state["LED_state"] else "shack-open") # Inverted because it is changing states
        status = self.__check_status(status)
        
        if status:
            self.set_led_state(not self.state["LED_state"]) # Invert the LED state
            print(f"Button pressed, LED state: {self.state['LED_state']}")
        else:
            self.state["ignore_next_update"] = False
            print("Failed to update channel")
            self.blink_error(5)
        
        self.last_time_button_was_pressed = time.time()
    
    def handle_channel_update(self, data):
        if self.state["ignore_next_update"]:
            self.state["ignore_next_update"] = False
            return
        
        if int(data["d"]["id"]) == self.config["channel_id"]:
            print("Got channel update")
            if data["d"]["name"] == "shack-open":
                self.set_led_state(True)
            else:
                self.set_led_state(False)

    def __handshake(self):
        print("Handshaking")
        command, = self.serial.read()
        if command != 0xFF:
            raise ValueError(f"Handshake failed ({hex(command)})")
        self.serial.write(0xFA)
        ack, = self.serial.read()
        if ack != 0x02:
            raise ValueError("Handshake failed")
        print("Handshake successful")

    def set_led_state(self, state):
        self.serial.write(b"\x01" + bytes([state]))
        self.state["LED_state"] = state
    
    def blink_error(self, times=3):
        for _ in range(times):
            self.serial.write(b"\x01\x00")
            time.sleep(0.2)
            self.serial.write(b"\x01\x01")
            time.sleep(0.2)
        self.set_led_state(self.state["LED_state"])

    def try_reconnect(self):
        while self.state["USB_retries"] < self.config["usb_retries"]:
            print(f"Attempting to reconnect to USB... (Attempt {self.state['USB_retries'] + 1}/{self.config['usb_retries']})")
            try:
                self.serial.close()
                self.serial.open()
                self.state["USB_retries"] = 0

                self.initialize_connection()
                return
            except:
                self.state["USB_retries"] += 1
                time.sleep(1)
            time.sleep(1)
        raise OSError("Failed to reconnect to USB")

    def initialize_connection(self):
        self.__handshake()

        channel = self.bot.get_channel(self.config["channel_id"])
        if not self.__check_status(channel):
            raise ValueError("Failed to get channel")
        
        if channel.json()["name"] == "shack-open":
            self.set_led_state(True)
        else:
            self.set_led_state(False)

    def __run(self):
        self.initialize_connection()

        while not self.is_stop_requested():
            try:
                if self.serial.in_waiting:
                    command, = self.serial.read()
                    if command == 0x01:
                        self.__handle_press()
                time.sleep(0.1)
            except OSError:
                self.try_reconnect()


def main():
    # Load the token from a file
    config = json.load(open("config.json"))
    arc_bot = shitcord.ShitcordBot(
        token=config["token"],
        intents=1 # Only subscribe to what I need
    )
    serial_handler = SerialHandler(config["serial_port"], config["serial_baudrate"], arc_bot,
                                   channel_id=config["channel"])

    arc_bot.subscribe_event("CHANNEL_UPDATE", serial_handler.handle_channel_update)

    serial_handler.run()
    arc_bot.run_forever()

if __name__ == "__main__":
    main()