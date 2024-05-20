from abc import ABC, abstractmethod


class WindowManagerInterface(ABC):
    @abstractmethod
    def go_to_window(self, window_name):
        pass
