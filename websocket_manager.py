import websocket
import threading
import json
import logging
import os

script_dir = os.path.dirname(os.path.abspath(__file__))

class WebSocketManager:
    def __init__(self):
        self.lock = threading.Lock()
        self.is_running = False
        self.ws_instance = None
        self.ws_thread = None
        self.device_name = "windows11"
        self.ws_url = "wss://15dcmwmsig.execute-api.ap-south-1.amazonaws.com/production/"
        
        self.setup_logging()
        
    def setup_logging(self):
        log_path = os.path.join(script_dir, "websocket_manager.log")
        
        logging.basicConfig(
            level=logging.DEBUG,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            handlers=[
                logging.FileHandler(log_path),
                logging.StreamHandler()
            ]
        )
        
        self.logger = logging.getLogger(__name__)
        
    def start_websocket(self):
        with self.lock:
            if self.is_running:
                self.logger.info("WebSocketManager already running")
                return True
            
            self.is_running = True
            self.logger.info("Starting WebSocketManager")
            
        return self.connect_websocket()
    
    def stop_websocket(self):
        self.logger.info("Stopping WebSocketManager")
        
        self.is_running = False
        
        self.ws_instance.keep_running = False
            
        self.disconnect_websocket()
        
        if self.ws_thread and self.ws_thread.is_alive():
            self.ws_thread.join(timeout=5)
            self.logger.info("WebSocket thread stopped")

        self.logger.info("WebSocketManager stopped")
            
    def connect_websocket(self):
        with self.lock:
            if self.ws_instance:
                self.logger.info("WebSocket already connected")
                return True
            
            try:
                self.logger.info(f"Connecting to WebSocket: {self.ws_url}")
                
                websocket.enableTrace(True)
                
                self.ws_instance = websocket.WebSocketApp(
                    self.ws_url,
                    on_open=self.on_open,
                    on_message=self.on_message,
                    on_error=self.on_error,
                    on_close=self.on_close
                )
                
                self.ws_thread = threading.Thread(target=lambda: self.ws_instance.run_forever(ping_interval=80, ping_timeout=10), daemon=True)
                self.ws_thread.start()
                
                self.logger.info("WebSocket connection thread started")
                return True
            
            except Exception as e:
                self.logger.error(f"Failed to start WebSocket connection: {e}")
                return False
            
    def disconnect_websocket(self):
        self.logger.info("Starting disconnect_websocket()")
        if self.ws_instance and hasattr(self.ws_instance, "sock") and self.ws_instance.sock and self.ws_instance.sock.connected:
            self.logger.info("Sending unregister message before disconnecting WebSocket...")
            
            unregister_msg = {
                "action": "unregister_device",
                "message": "Disconnect Connection",
                "device_name": self.device_name
            }
            
            try:
                self.ws_instance.send(json.dumps(unregister_msg))
                self.logger.info(f"Unregistration message send to server for: {self.device_name}")
            except Exception as e:
                self.logger.error(f"Error sending Unregistration message: {e}")
        
        if self.ws_instance:
            self.logger.info("Disconnecting WebSocket...")
            
            try:
                self.ws_instance.close()
                self.logger.info("Websocket Disconnected")
                self.ws_instance = None
            except Exception as e:
                self.logger.error(f"Error closing WebSocket: {e}")

    def ping_pong(self):
        if self.ws_instance and hasattr(self.ws_instance, "sock") and self.ws_instance.sock and self.ws_instance.sock.connected:
            pass
                    
    def is_websocket_connected(self) -> bool:
        with self.lock:
            return (self.ws_instance and
                    hasattr(self.ws_instance, "sock") and
                    self.ws_instance.sock and
                    self.ws_instance.sock.connected)
            
    def get_connection_status(self):
        with self.lock:
            return {
                "connected": self.is_websocket_connected(),
                "running": self.is_running,
                "device_name": self.device_name
            }
                    
    def handle_received_message(self, message_data):
        if message_data.get("message") == "Save to Database":
            connection_id = message_data.get("connection_id", "")
            self.logger.info(f"Received connection ID: {connection_id}")
        else:
            self.logger.debug(f"Unhandled message type: {message_data}")
                    
    def on_open(self, ws):
        self.logger.info("WebSocket connection opened")
        
        registration_msg = {
            "action": "register_device",
            "message": "Connection Established",
            "device_name": self.device_name
        }
        
        try:
            ws.send(json.dumps(registration_msg))
            self.logger.info(f"Device registration sent for: {self.device_name}")
        except Exception as e:
            self.logger.error(f"Error sending registration message: {e}")
            
    def on_message(self, ws, message):
        try:
            self.logger.debug(f"Received message: {message}")
            message_data = json.loads(message)
            self.handle_received_message(message_data)
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON message received: {e}")
        except Exception as e:
            self.logger.error(f"Error processing message: {e}")
            
    def on_error(self, ws, error):
        self.logger.error(f"WebSocket error: {error}")
        
    def on_close(self, ws, close_status_code: int, close_msg: str):
        self.logger.info(f"Websocket connection closed: {close_status_code} - {close_msg}")