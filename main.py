import os

from utils.logging_manager.loggingmanager import LoggingManager
from routing.windowsmanager import WindowManager
import customtkinter as ctk
from view.windowsmanagerconfig import WindowsManagerConfig


def on_close():
    os._exit(0)


if __name__ == '__main__':
    try:
        LoggingManager().config()

        root_window = ctk.CTk()

        windows_manager = WindowManager(WindowsManagerConfig(root_window).get_config())
        windows_manager.go_to_window("LoginView")

        root_window.protocol("WM_DELETE_WINDOW", on_close)
        root_window.mainloop()
    except Exception as e:
        print(e)
