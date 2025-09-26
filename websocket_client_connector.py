import queue
import threading
import websocket
import json
from pymongo import MongoClient
from dotenv import dotenv_values
import os
import time
import logging
from typing import Callable, Optional, Dict, Any

script_dir = os.path.dirname(os.path.abspath(__file__))

class WebSocketManager:
    def __init__(self):
        self.ws_instance: Optional[websocket.WebSocketApp] = None
        self.ws_thread: Optional[threading.Thread] = None
        self.command_thread: Optional[threading.Thread] = None
        self.ping_thread: Optional[threading.Thread] = None
        
        self.lock = threading.Lock()
        self.command_queue = queue.Queue()
        
        self.is_running = False
        self.ping_thread_running = False
        self.ping_interval = 420
        self.connection_attempts = 0
        self.max_connection_attempts = 5
        self.reconnect_delay = 5
        self.status_callbacks: list[Callable] = []
        
        self._load_config()
        self._setup_logging()
        
    def _load_config(self):
        try:
            env_path = os.path.join(script_dir, ".env")
            env_values = dotenv_values(env_path)

            self.MONGODB_URI = env_values.get("MONGODB_URI")
            self.device_name = "windows11"
            self.ws_url = "wss://15dcmwmsig.execute-api.ap-south-1.amazonaws.com/production"
            
            if not self.MONGODB_URI:
                raise ValueError("MONGODB_URI not found in .env file")
            
        except Exception as e:
            print(f"Configuration error: {e}")
            self.device_name = "windows11"
            self.ws_url = "wss://15dcmwmsig.execute-api.ap-south-1.amazonaws.com/production"
            
    def _setup_logging(self):
        log_path = os.path.join(script_dir, "websocket_manager.log")
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            handlers=[
                logging.FileHandler(log_path),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
    def start_manager(self) -> bool:
        with self.lock:
            if self.is_running:
                self.logger.info("WebSocketManager already running")
                return True
            
            self.is_running = True
            self.logger.info("Starting WebSocketManager")
            
        self.command_thread = threading.Thread(target=self._process_commands, daemon=True)
        self.command_thread.start()
        
        return self._connect_websocket()
    
    def stop_manager(self):
        self.logger.info("Stopping WebSocketManager")
        
        with self.lock:
            self.is_running = False
            
        self._disconnect_websocket()
        
        if self.command_thread and self.command_thread.is_alive():
            self.command_thread.join(timeout=5)
            
        if self.ws_thread and self.ws_thread.is_alive():
            self.ws_thread.join(timeout=5)
            
        self.logger.info("WebSocketManager stopped")
        
    def send_command(self, command: str, data: Any=None):
        if self.is_running:
            self.command_queue.put((command, data))
        else:
            self.logger.warning(f"Cannot send command '{command}' - manager not running")
            
    def add_status_callback(self, callback: Callable[[str, Any], None]):
        self.status_callbacks.append(callback)
        
    def remove_status_callback(self, callback: Callable[[str, Any], None]):
        if callback in self.status_callbacks:
            self.status_callbacks.remove(callback)
            
    def is_websocket_connected(self) -> bool:
        with self.lock:
            return (self.ws_instance and
                    hasattr(self.ws_instance, "sock") and
                    self.ws_instance.sock and
                    self.ws_instance.sock.connected)
            
    def get_connection_status(self) -> Dict[str, Any]:
        with self.lock:
            return {
                "connected": self.is_websocket_connected(),
                "running": self.is_running,
                "connection_attempts": self.connection_attempts,
                "device_name": self.device_name
            }
            
    def _connect_websocket(self) -> bool:
        with self.lock:
            if self.ws_instance and hasattr(self.ws_instance, "sock") and self.ws_instance.sock and self.ws_instance.sock.connected:
                self.logger.info("WebSocket already connected")
                return True
            
            try:
                self.logger.info(f"Connecting to WebSocket: {self.ws_url}")
                
                websocket.enableTrace(True)
                
                
                self.ws_instance = websocket.WebSocketApp(
                    self.ws_url,
                    on_open=self._on_open,
                    on_message=self._on_message,
                    on_error=self._on_error,
                    on_close=self._on_close,
                    on_pong=self._on_pong
                )
                
                self.ws_thread = threading.Thread(target=self.ws_instance.run_forever, daemon=True)
                self.ws_thread.start()

                self.ping_thread = threading.Thread(target=self._ping_loop, daemon=True)
                self.ping_thread.start()
                
                self.logger.info("WebSocket connection thread started")
                return True
            
            except Exception as e:
                self.logger.error(f"Failed to start WebSocket connection: {e}")
                return False

    def _disconnect_websocket(self):
        with self.lock:
            if self.ws_instance:
                self.logger.info("Disconnecting WebSocket...")
                try:
                    self.ws_instance.close()
                    self.ws_instance = None
                except Exception as e:
                    self.logger.error(f"Error closing WebSocket: {e}")
                    
            if self.ws_thread and self.ws_thread.is_alive():
                self.ws_thread.join(timeout=5)
                self.ws_thread = None
                
    def _process_commands(self):
        self.logger.info("Command processor started")
        
        while self.is_running:
            try:
                command, data = self.command_queue.get(timeout=1)
                self.logger.debug(f"Processing command: {command}")
                
                if command == "connect":
                    self._connect_websocket()
                elif command == "disconnect":
                    self._disconnect_websocket()
                elif command == "reconnect":
                    self._disconnect_websocket()
                    time.sleep(2)
                    self._connect_websocket()
                elif command == "send_message" and data:
                    self._send_websocket_message(data)
                # elif command == "ping":
                #     self._send_ping()
                    
            except queue.Empty:
                continue
            except Exception as e:
                self.logger.error(f"Command processing error: {e}")
                
    def _send_websocket_message(self, message: Dict[str, Any]):
        with self.lock:
            if self.ws_instance and hasattr(self.ws_instance, "sock") and self.ws_instance.sock and self.ws_instance.sock.connected:
                try:
                    self.ws_instance.send(json.dumps(message))
                    self.logger.debug(f"Message sent: {message}")
                except Exception as e:
                    self.logger.error(f"Error sending message: {e}")
            else:
                self.logger.warning("Cannot send message - WebSocket not connected")

    def _ping_loop(self):
        while self.is_running:
            time.sleep(self.ping_interval)
            if self.is_websocket_connected():
                self.ws_instance.ping()
                
    def _send_ping(self):
        with self.lock:
            if self.ws_instance and hasattr(self.ws_instance, "sock") and self.ws_instance.sock and self.ws_instance.sock.connected:
                try:
                    self.ws_instance.ping()
                    self.logger.debug("Ping sent")
                except Exception as e:
                    self.logger.error(f"Error sending ping: {e}")
                    
    def _notify_status_callbacks(self, status: str, data: Any=None):
        for callback in self.status_callbacks:
            try:
                callback(status, data)
            except Exception as e:
                self.logger.error(f"Error in status callback: {e}")
                
    def _on_open(self, ws):
        self.logger.info("WebSocket connection opened")
        self.connection_attempts = 0
        
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
        
        self._notify_status_callbacks("connected", None)
        
    def _on_message(self, ws, message: str):
        try:
            self.logger.debug(f"Received message: {message}")
            message_data = json.loads(message)
            self._handle_received_message(message_data)
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON message received: {e}")
        except Exception as e:
            self.logger.error(f"Error processing message: {e}")
            
    def _on_error(self, ws, error):
        self.logger.error(f"WebSocket error: {error}")
        self._notify_status_callbacks("error", error)
        
    def _on_close(self, ws, close_status_code: int, close_msg: str):
        self.logger.warning(f"WebSocket connection closed: {close_status_code} - {close_msg}")
        
        self._update_database_disconnect()
        
        self._notify_status_callbacks("disconnected", (close_status_code, close_msg))
        
        if self.is_running:
            self._schedule_reconnect()
            
    def _on_pong(self, ws, message: str):
        self.logger.debug(f"Pong received: {message}")
        
    def _handle_received_message(self, message_data: Dict[str, Any]):
        if message_data.get("message") == "Save to Database":
            connection_id = message_data.get("connection_id", "")
            self.logger.info(f"Received connection ID: {connection_id}")
            self._update_database_connection(connection_id)
        else:
            self.logger.debug(f"Unhandled message type: {message_data}")
            
    def _schedule_reconnect(self):
        if self.connection_attempts < self.max_connection_attempts:
            self.connection_attempts += 1
            delay = min(self.reconnect_delay * self.connection_attempts, 60)
            
            self.logger.info(f"Scheduling reconnect attempt {self.connection_attempts} in {delay} seconds")
            
            def delayed_reconnect():
                time.sleep(delay)
                if self.is_running:
                    self.send_command("reconnect")
            
            reconnect_thread = threading.Thread(target=delayed_reconnect, daemon=True)
            reconnect_thread.start()
        else:
            self.logger.error("Max reconnection attempts reached")
            self._notify_status_callbacks("max_reconnects_reached", self.max_connection_attempts)
            
    def _get_database_connection(self) -> Optional[MongoClient]:
        try:
            if not self.MONGODB_URI:
                self.logger.error("MongoDB URI not configured")
                return None
            
            mongo_client = MongoClient(
                self.MONGODB_URI, 
                serverSelectionTimeoutMS=5000,
                maxPoolSize=10,
                retryWrites=True
            )
            
            mongo_client.server_info()
            return mongo_client
        
        except Exception as e:
            self.logger.error(f"Database connection error: {e}")
            return None
        
    def _update_database_connection(self, connection_id: str):
        mongo_client = self._get_database_connection()
        if not mongo_client:
            return
        
        try:
            mongo_db = mongo_client["AWS_Webhook"]
            mongo_collection = mongo_db["Webhook_Details"]
            
            data = {
                "device_name": self.device_name,
                "connection_id": connection_id,
                "is_connected": bool(connection_id),
                "last_updated": time.time()
            }
            
            result = mongo_collection.update_one(
                {"_id": self.device_name}, 
                {"$set": data}, 
                upsert=True
            )
            
            self.logger.info(f"Database updated - Connection ID: {connection_id}")
            
        except Exception as e:
            self.logger.error(f"Database update error: {e}")
        finally:
            mongo_client.close()
            
    def _update_database_disconnect(self):
        mongo_client = self._get_database_connection()
        if not mongo_client:
            return
            
        try:
            mongo_db = mongo_client["AWS_Webhook"]
            mongo_collection = mongo_db["Webhook_Details"]
            
            data = {
                "device_name": self.device_name,
                "connection_id": "",
                "is_connected": False,
                "last_updated": time.time()
            }
            
            mongo_collection.update_one(
                {"_id": self.device_name}, 
                {"$set": data}, 
                upsert=True
            )
            
            self.logger.info("Database updated - Disconnected")
            
        except Exception as e:
            self.logger.error(f"Database disconnect update error: {e}")
        finally:
            mongo_client.close()


class WebSocketClient:
    def __init__(self):
        self.manager = get_websocket_manager()
        
    def connect(self) -> bool:
        return self.manager.start_manager()
    
    def disconnect(self):
        self.manager.send_command("disconnect")
        
    def reconnect(self):
        self.manager.send_command("reconnect")
        
    def send_message(self, message: Dict[str, Any]):
        self.manager.send_command("send_message", message)
        
    def is_connected(self) -> bool:
        return self.manager.is_websocket_connected()
        
    def add_status_listener(self, callback: Callable[[str, Any], None]):
        self.manager.add_status_callback(callback)
        
    def get_status(self) -> Dict[str, Any]:
        return self.manager.get_connection_status()
    
_ws_manager: Optional[WebSocketManager] = None

def get_websocket_manager() -> WebSocketManager:
    global _ws_manager
    if _ws_manager is None:
        _ws_manager = WebSocketManager()
    return _ws_manager

def websocket_run() -> bool:
    manager = get_websocket_manager()
    return manager.start_manager()

def disconnect_websocket():
    manager = get_websocket_manager()
    manager.send_command("disconnect")

def is_websocket_connected() -> bool:
    manager = get_websocket_manager()
    return manager.is_websocket_connected()

def get_websocket_status() -> Dict[str, Any]:
    manager = get_websocket_manager()
    return manager.get_connection_status()

def main():
    print("Starting robust WebSocket client...")
    
    websocket_client = WebSocketClient()
    
    def status_monitor(status: str, data: Any):
        print(f"[STATUS] {status}: {data}")
        
    websocket_client.add_status_listener(status_monitor)
    
    if websocket_client.connect():
        print("WebSocket manager started successfully")
    else:
        print("Failed to start WebSocket manager")
        return
    
    while True:
        try:
            status = websocket_client.get_status()
            if not status["connected"]:
                print("Connection lost, attempting to reconnect...")
                websocket_client.reconnect()
            
            time.sleep(30)
            
        except Exception as e:
            print(f"Error in monitoring loop: {e}")
            print("Continuing monitoring...")
            time.sleep(5)
            
if __name__ == "__main__":
    main()