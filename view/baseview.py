from abc import ABC, abstractmethod

import customtkinter as ctk

from routing.windowsmanagerinterface import WindowManagerInterface


class BaseView(ctk.CTkFrame, ABC):

    @abstractmethod
    def __init__(self, root_window: ctk.CTk, windows_manager: WindowManagerInterface, *args, **kwargs):
        super().__init__(root_window, *args, **kwargs)
        self.windows_manager = windows_manager
        self.root_window = root_window

    @abstractmethod
    def load_screen(self):
        pass
