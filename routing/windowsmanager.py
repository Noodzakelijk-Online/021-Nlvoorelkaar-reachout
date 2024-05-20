from routing.windowsmanagerinterface import WindowManagerInterface


class WindowManager(WindowManagerInterface):
    def __init__(self, config):
        self.current_window = None
        self.config = config
        for view_args in self.config.values():
            view_args[2]["windows_manager"] = self

    def go_to_window(self, window_name):
        if self.current_window is not None:
            self.current_window.destroy()
        window_class, args, kwargs = self.config[window_name]
        self.current_window = window_class(*args, **kwargs)
        self.current_window.load_screen()
