import os
import threading  # Import threading module
import time

from services.servicemanager import ServiceManager
from services.servicemanagerinterface import ServiceManagerInterface
from utils.logging_manager.loggingmanager import LoggingManager
from routing.windowsmanager import WindowManager
import customtkinter as ctk

from view.homeview import HomeView
from view.windowsmanagerconfig import WindowsManagerConfig


def reminder_start( service_manager: ServiceManager):
    def run_service():
        service_manager.start_reminder_service()
    # Run the service manager in a separate thread
    threading.Thread(target=run_service).start()


def on_close():
    os._exit(0)


if __name__ == '__main__':
    try:
        LoggingManager().config()
        service_manager = ServiceManager()  # Create an instance of ServiceManager
        root_window = ctk.CTk()

        windows_manager = WindowManager(WindowsManagerConfig(root_window).get_config())
        windows_manager.go_to_window("LoginView")

        root_window.protocol("WM_DELETE_WINDOW", on_close)

        # Schedule reminder_start to run after a short delay (e.g., 100 milliseconds)
        root_window.after(100, reminder_start,  service_manager)

        root_window.mainloop()

    except Exception as e:
        print(e)
