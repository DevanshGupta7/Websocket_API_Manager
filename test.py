# import win32serviceutil
# import win32service
# import win32event
# import servicemanager
# import threading
# import time
# import os
# import sys
# import logging
# import pywintypes
# import ctypes
# from ctypes import wintypes

# logging.basicConfig(
#     filename=r"D:\Websocket_API_Manager\service_debug.log",
#     level=logging.DEBUG,
#     format='%(asctime)s - %(levelname)s - %(message)s'
# )

# script_dir = os.path.dirname(os.path.abspath(__file__))
# with open(r"D:\Websocket_API_Manager\text.txt", 'w') as file:
#     file.write("Hello")

# if r"D:\Websocket_API_Manager" not in sys.path:
#     sys.path.insert(0, r"D:\Websocket_API_Manager")

# from websocket_client_connector import get_websocket_manager

# class EnhancedPowerService(win32serviceutil.ServiceFramework):
#     _svc_name_ = "EnhancedPowerService"
#     _svc_display_name_ = "Enhanced Power and Shutdown Service"
#     _svc_description_ = "Handles Shutdown, sleep, restart events and auto restarts if it fails"
#     _reg_class_id_ = "{9f2ee872-2b47-4db7-8dd8-d5370e121832}"
    
#     def __init__(self, args):
#         win32serviceutil.ServiceFramework.__init__(self, args)
#         self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
#         self.is_running = True
#         self.shutdown_handled = False
#         self.power_thread = None
#         self.keep_alive_thread = None
        
#         logging.info("Running __init__")
        
#         self.ws_manager = get_websocket_manager()
#         self.ws_manager.add_status_callback(self._websocket_status_callback)
        
#     def _websocket_status_callback(self, status: str, data):
#         servicemanager.LogInfoMsg(f"WebSocket status: {status} - {data}")
#         logging.info(f"WebSocket status: {status} - {data}")
        
#     def SvcStop(self):
#         self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
#         self.is_running = False
        
#         try:
#             self.ws_manager.stop_manager()
#         except Exception as e:
#             servicemanager.LogErrorMsg(f"Error stopping WebSocket manager: {e}")
#             logging.error(f"Error stopping WebSocket manager: {e}")
        
#         if self.power_thread and self.power_thread.is_alive():
#             self.power_thread.join(timeout=5)
            
#         if self.keep_alive_thread and self.keep_alive_thread.is_alive():
#             self.keep_alive_thread.join(timeout=5)
            
#         win32event.SetEvent(self.hWaitStop)
        
#     def SvcDoRun(self):
#         servicemanager.LogInfoMsg("Enhanced Power & Shutdown service starting")
#         logging.info("Enhanced Power & Shutdown service starting")
        
#         try:
#             if self.ws_manager.start_manager():
#                 servicemanager.LogInfoMsg("WebSocket manager started successfully")
#                 logging.info("WebSocket manager started successfully")
#             else:
#                 servicemanager.LogErrorMsg("Failed to start WebSocket manager")
#                 logging.error("Failed to start WebSocket manager")
#         except Exception as e:
#             servicemanager.LogErrorMsg(f"Error starting WebSocket manager: {e}")
#             logging.error(f"Error starting WebSocket manager: {e}")
        
#         self.register_shutdown_handler()
#         self.start_power_monitoring()
#         self.start_keep_alive_monitor()
        
#         win32event.WaitForSingleObject(self.hWaitStop, win32event.INFINITE)
        
#         servicemanager.LogInfoMsg("Enhanced Power & Shutdown service stopped")
#         logging.info("Enhanced Power & Shutdown service stopped")
        
#     def register_shutdown_handler(self):
#         # self.SvcSetStatusWithData(
#         #     win32service.SERVICE_RUNNING,
#         #     win32service.SERVICE_ACCEPT_STOP |
#         #     win32service.SERVICE_ACCEPT_SHUTDOWN |
#         #     win32service.SERVICE_ACCEPT_PRESHUTDOWN |
#         #     win32service.SERVICE_ACCEPT_POWEREVENT
#         # )
        
#         self.ReportServiceStatus(
#             win32service.SERVICE_RUNNING,
#             win32service.SERVICE_ACCEPT_STOP |
#             win32service.SERVICE_ACCEPT_SHUTDOWN |
#             win32service.SERVICE_ACCEPT_PRESHUTDOWN |
#             win32service.SERVICE_ACCEPT_POWEREVENT
#         )
        
#     def SvcSetStatusWithData(self, dw_current_state, dw_controls_accepted):
#         try:
#             # status = pywintypes.SERVICE_STATUS_TYPE()
#             # status.dwServiceType = win32service.SERVICE_WIN32_OWN_PROCESS
#             # status.dwCurrentState = dw_current_state
#             # status.dwControlsAccepted = dw_controls_accepted
#             # status.dwWin32ExitCode = 0
#             # status.dwServiceSpecificExitCode = 0
#             # status.dwCheckPoint = 0
#             # status.dwWaitHint = 0
            
#             class SERVICE_STATUS(ctypes.Structure):
#                 _fields_=[
#                     ('dwServiceType', wintypes.DWORD),
#                     ('dwCurrentState', wintypes.DWORD),
#                     ('dwControlsAccepted', wintypes.DWORD),
#                     ('dwWin32ExitCode', wintypes.DWORD),
#                     ('dwServiceSpecificExitCode', wintypes.DWORD),
#                     ('dwCheckPoint', wintypes.DWORD),
#                     ('dwWaitHint', wintypes.DWORD)
#                 ]
                
#             status = SERVICE_STATUS()
#             status.dwServiceType = win32service.SERVICE_WIN32_OWN_PROCESS
#             status.dwCurrentState = dw_current_state
#             status.dwControlsAccepted = dw_controls_accepted
#             status.dwWin32ExitCode = 0
#             status.dwServiceSpecificExitCode = 0
#             status.dwCheckPoint = 0
#             status.dwWaitHint = 0
        
#             advapi32 = ctypes.windll.advapi32
#             result = advapi32.SetServiceStatus(self.sshandle, ctypes.byref(status))
            
#             if not result:
#                 error_code = ctypes.windll.kernel32.GetLastError()
#                 raise Exception(f"SetServiceStatus failed with error: {error_code}")
                
#             servicemanager.LogInfoMsg(f"Service status set to: {dw_current_state}")
#             logging.info(f"Service status set to: {dw_current_state}")
            
#         except Exception as e:
#             servicemanager.LogErrorMsg(f"Error setting service status: {e}")
#             logging.error(f"Error setting service status: {e}")
        
#     def SvcOtherEx(self, control, event_type, data):
#         if control == win32service.SERVICE_CONTROL_PRESHUTDOWN:
#             servicemanager.LogInfoMsg("PRESHUTDOWN event - running with extended time")
#             logging.info("PRESHUTDOWN event - running with extended time")
#             self.shutdown_handled = True
#             self.handle_shutdown_restart()
#             time.sleep(10)
#             win32event.SetEvent(self.hWaitStop)
            
#         elif control == win32service.SERVICE_CONTROL_SHUTDOWN:
#             if not self.shutdown_handled:
#                 servicemanager.LogInfoMsg("SHUTDOWN event - preshutdown not received")
#                 logging.info("SHUTDOWN event - preshutdown not received")
#                 self.handle_shutdown_restart()
#             else:
#                 servicemanager.LogInfoMsg("SHUTDOWN event - already handled in preshutdown")
#                 logging.info("SHUTDOWN event - already handled in preshutdown")
            
#         elif control == win32service.SERVICE_CONTROL_POWEREVENT:
#             self.handle_power_event(event_type, data)
            
#         return win32serviceutil.ServiceFramework.SvcOtherEx(self, control, event_type, data)
    
#     def GetAcceptedControls(self):
#         return(super().GetAcceptedControls() | win32service.SERVICE_ACCEPT_PRESHUTDOWN)
    
#     def handle_power_event(self, event_type, data):
#         PBT_APMSUSPEND = 0x0004
#         PBT_APMRESUMESUSPEND = 0x0007
        
#         if event_type == PBT_APMSUSPEND:
#             servicemanager.LogInfoMsg("SLEEP event detected - system going to sleep")
#             logging.info("SLEEP event detected - system going to sleep")
#             self.handle_sleep()
        
#         elif event_type == PBT_APMRESUMESUSPEND:
#             servicemanager.LogInfoMsg("RESUME event detected - system waking up")
#             logging.info("RESUME event detected - system waking up")
#             self.handle_resume()
            
#     def handle_shutdown_restart(self):
#         servicemanager.LogInfoMsg("Running Python code for shutdown/restart...")
#         logging.info("Running Python code for shutdown/restart...")
        
#         try:
#             self.ws_manager.send_command("disconnect")
#             servicemanager.LogInfoMsg("WebSocket disconnected for shutdown/restart")
#             logging.info("WebSocket disconnected for shutdown/restart")
#         except Exception as e:
#             servicemanager.LogErrorMsg(f"Error handling shutdown: {e}")
#             logging.error(f"Error handling shutdown: {e}")
            
#     def handle_sleep(self):
#         servicemanager.LogInfoMsg("Running Python code before sleep...")
#         logging.info("Running Python code before sleep...")
        
        
#         try:
#             self.ws_manager.send_command("disconnect")
#             servicemanager.LogInfoMsg("WebSocket disconnected for sleep")
#             logging.info("WebSocket disconnected for sleep")
#         except Exception as e:
#             servicemanager.LogErrorMsg(f"Error handling sleep: {e}")
#             logging.error(f"Error handling sleep: {e}")
            
#     def handle_resume(self):
#         servicemanager.LogInfoMsg("Running Python code after resume...")
#         logging.info("Running Python code after resume...")
        
#         try:
#             self.ws_manager.send_command("reconnect")
#             servicemanager.LogInfoMsg("WebSocket reconnection initiated after resume")
#             logging.info("WebSocket reconnection initiated after resume")
#         except Exception as e:
#             servicemanager.LogErrorMsg(f"Error handling resume: {e}")
#             logging.error(f"Error handling resume: {e}")
        
#     def start_power_monitoring(self):
#         if self.power_thread is None or not self.power_thread.is_alive():
#             self.power_thread = threading.Thread(target=self.power_monitor)
#             self.power_thread.daemon = True
#             self.power_thread.start()
#             servicemanager.LogInfoMsg("Power monitoring thread started")
#             logging.info("Power monitoring thread started")
            
#     def start_keep_alive_monitor(self):
#         def monitor():
#             while self.is_running:
#                 try:
#                     if self.power_thread is None or not self.power_thread.is_alive():
#                         servicemanager.LogWarningMsg("Power monitoring thread died - restarting automatically")
#                         logging.info("Power monitoring thread died - restarting automatically")
#                         self.start_power_monitoring()
                        
#                     if not self.ws_manager.is_websocket_connected():
#                         servicemanager.LogWarningMsg("WebSocket disconnected - attempting reconnect")
#                         logging.warning("WebSocket disconnected - attempting reconnect")
                        
#                         self.ws_manager.send_command("reconnect")
                        
#                     for _ in range(30):
#                         if not self.is_running:
#                             break
#                         time.sleep(1)
                        
#                 except Exception as e:
#                     servicemanager.LogErrorMsg(f"Keep-alive monitor error: {e}")
#                     logging.error(f"Keep-alive monitor error: {e}")
#                     time.sleep(10)
                    
#         self.keep_alive_thread = threading.Thread(target=monitor)
#         self.keep_alive_thread.daemon = True
#         self.keep_alive_thread.start()
#         servicemanager.LogInfoMsg("Keep-alive monitor started - will auto-restart failed components")
#         logging.info("Keep-alive monitor started - will auto-restart failed components")
        
#     def power_monitor(self):
#         try:
#             servicemanager.LogInfoMsg("Power monitor thread running")
#             logging.info("Power monitor thread running")
            
#             while self.is_running:
#                 status = self.ws_manager.get_connection_status()
#                 if not status["connected"] and status["running"]:
#                     servicemanager.LogWarningMsg("WebSocket not connected but manager running")
#                     logging.warning("WebSocket not connected but manager running")
#                 time.sleep(10)
                
#         except Exception as e:
#             servicemanager.LogErrorMsg(f"Power monitoring thread error: {e}")
#             logging.error(f"Power monitoring thread error: {e}")
            
#     @classmethod
#     def install_service(cls):
#         try:
#             win32serviceutil.InstallService(
#                 cls._reg_class_id_,
#                 cls._svc_name_,
#                 cls._svc_display_name_,
#                 startType=win32service.SERVICE_AUTO_START,
#                 description=cls._svc_description_
#             )
#             print(f"Service '{cls._svc_display_name_}' installed successfully with auto-start enabled")
            
#         except Exception as e:
#             print(f"Error installing service: {e}")
            
# if __name__ == "__main__":
#     win32serviceutil.HandleCommandLine(EnhancedPowerService)

# import zipfile
# import os

# def zip_dir(directory, zip_name):
#     with zipfile.ZipFile(zip_name, 'w', zipfile.ZIP_DEFLATED) as z:
#         for root, _, files in os.walk(directory):
#             for file in files:
#                 filepath = os.path.join(root, file)
#                 arcname = os.path.relpath(filepath, start=directory)
#                 z.write(filepath, os.path.join(os.path.basename(directory), arcname))

# zip_dir("libraries/python", "libraries.zip")

import subprocess

subprocess.run([r"C:\Users\devan\AppData\Local\Programs\Python\Python312\python.exe", r"D:\AI_Assistant\face_authentication\face_service.py"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    stdin=subprocess.DEVNULL,
                    close_fds=True)