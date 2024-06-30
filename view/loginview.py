import logging
from typing import Optional

import customtkinter as ctk

from controllers.logindatacontrollerinterface import LoginDataControllerInterface
from controllers.logincontrollerinterface import LoginControllerInterface
from controllers.logindatacontroller import LoginDataController
from routing.windowsmanagerinterface import WindowManagerInterface
from view.baseview import BaseView
from view.utilsgui import center_window


class LoginView(BaseView):

    def __init__(self, root_window: ctk.CTk, login_controller: LoginControllerInterface, next_window: str,
                 windows_manager: WindowManagerInterface, generic_title: Optional[str] = None,
                 login_data_controller: LoginDataControllerInterface = None, specific_title: Optional[str] = None,
                 width: Optional[int] = None, height: Optional[int] = None):
        super().__init__(root_window, windows_manager)
        self.login_controller = login_controller
        self.next_window = next_window
        self.login_data_controller = LoginDataController() if login_data_controller is None else login_data_controller
        self.widgets = []
        self.saved_username, self.saved_password = self.login_data_controller.load_login_data()
        self.username = self.saved_username if self.saved_username is not None else None
        self.password = self.saved_password if self.saved_password is not None else None
        self.error_label = None
        self.login_button = None
        self.remember_me = None
        self.remember_me_checkbox = None
        self.width = 400 if width is None else width
        self.height = 300 if height is None else height
        self.generic_title = "NL Voor Elkaar Manager" if generic_title is None else generic_title
        self.specific_title = "Login" if specific_title is None else specific_title
        self.main_frame = ctk.CTkFrame(root_window)
        self.width_field = 250
        self.padx_standard = 20
        self.pady_standard = 4

    def create_username_label(self) -> ctk.CTkLabel:
        username_label = ctk.CTkLabel(self.main_frame, text="E-mail")
        username_label.grid(row=0, column=0, sticky="ew", padx=self.padx_standard, pady=self.pady_standard)
        self.widgets.append(username_label)
        return username_label

    def create_username_field(self) -> ctk.CTkEntry:
        self.username = ctk.StringVar()
        self.username.trace('w', self.check_input)
        username_entry = ctk.CTkEntry(self.main_frame, textvariable=self.username, width=self.width_field)
        username_entry.grid(row=1, column=0, sticky="nsew", padx=self.padx_standard, pady=self.pady_standard)
        self.widgets.append(username_entry)
        return username_entry

    def create_password_label(self) -> ctk.CTkLabel:
        password_label = ctk.CTkLabel(self.main_frame, text="Password")
        password_label.grid(row=2, column=0, sticky="ew", padx=self.padx_standard, pady=self.pady_standard)
        self.widgets.append(password_label)
        return password_label

    def create_password_field(self) -> ctk.CTkEntry:
        self.password = ctk.StringVar()
        self.password.trace('w', self.check_input)
        password_entry = ctk.CTkEntry(self.main_frame, show="*", textvariable=self.password, width=self.width_field)
        password_entry.grid(row=3, column=0, sticky="nsew", padx=self.padx_standard, pady=self.pady_standard)
        self.widgets.append(password_entry)
        return password_entry

    def create_remember_me_checkbox(self) -> ctk.CTkCheckBox:
        self.remember_me = ctk.IntVar()
        remember_me_checkbox = ctk.CTkCheckBox(self.main_frame, text="Remember me", variable=self.remember_me)
        remember_me_checkbox.grid(row=4, column=0, sticky="ew", padx=self.padx_standard, pady=self.pady_standard + 5)
        self.widgets.append(remember_me_checkbox)
        return remember_me_checkbox

    def create_error_label(self) -> ctk.CTkLabel:
        error_label = ctk.CTkLabel(self.main_frame, text="", text_color="red")
        error_label.grid(row=5, column=0, sticky="ew", padx=self.padx_standard, pady=self.pady_standard)
        error_label.grid_remove()
        self.widgets.append(error_label)
        return error_label

    def create_login_button(self) -> ctk.CTkButton:
        login_button = ctk.CTkButton(self.main_frame, text="Login", command=lambda: self.login(), state='disabled')
        login_button.grid(row=6, column=0, sticky="ew", padx=self.padx_standard, pady=(30, 20))
        self.widgets.append(login_button)
        return login_button

    def check_input(self, *args) -> None:
        username = self.password.get()
        password = self.password.get()
        if len(username) >= 3 and len(password) >= 3:
            self.login_button.configure(state="normal")
        else:
            self.login_button.configure(state="disabled")

    def destroy(self):
        for widget in self.widgets:
            if widget.winfo_exists():
                widget.destroy()
        self.main_frame.grid_forget()

    def configure_window_style(self) -> None:
        self.root_window.geometry(f'{self.width}x{self.height}')
        self.root_window.title(f'{self.generic_title} - {self.specific_title}')
        self.root_window.resizable(False, False)
        self.main_frame.place(relx=0.5, rely=0.5, anchor="center")

    def load_screen(self) -> None:
        self.configure_window_style()
        self.create_username_label()
        self.create_username_field()
        self.create_password_label()
        self.create_password_field()
        self.remember_me_checkbox = self.create_remember_me_checkbox()
        self.error_label = self.create_error_label()
        self.login_button = self.create_login_button()

        if self.saved_username is not None and self.saved_password is not None:
            self.username.set(self.saved_username)
            self.password.set(self.saved_password)
            self.remember_me_checkbox.select()
            self.login()

        center_window(self.root_window)

    def login(self) -> None:
        try:
            success = self.login_controller.login(self.username.get(), self.password.get())
        except Exception as e:
            logging.error(e)
            self.error_label.configure(text="Connection problems, please try again.")
            return
        if success:
            if self.remember_me.get() == 1:
                self.login_data_controller.save_login_data(self.username.get(), self.password.get())
            else:
                self.login_data_controller.erase_login_data()
            self.root_window.username = self.username.get()
            self.root_window.password = self.password.get()
            self.error_label.grid_remove()
            self.windows_manager.go_to_window(self.next_window)


        else:
            self.error_label.configure(text="Login failed, please try again.")
            self.error_label.grid()
            logging.info(f"Failed login attempt with username: {self.username.get()}")
