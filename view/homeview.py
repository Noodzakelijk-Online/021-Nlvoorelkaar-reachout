import math
import random
import threading
import time
import webbrowser
from typing import Optional
from routing.windowsmanagerinterface import WindowManagerInterface
from services.servicemanagerinterface import ServiceManagerInterface
from view.baseview import BaseView
import customtkinter as ctk

class HomeView(BaseView):
    def __init__(self, root_window: ctk.CTk, windows_manager: WindowManagerInterface,
                 service_manager: ServiceManagerInterface, specific_title: Optional[str] = None,
                 generic_title: Optional[str] = None, width: Optional[int] = None, height: Optional[int] = None):
        super().__init__(root_window, windows_manager)
        self.service_manager = service_manager
        self.service_manager.subscribe(self)
        self.generic_title = "NL Voor Elkaar Manager" if generic_title is None else generic_title
        self.specific_title = "Home" if specific_title is None else specific_title
        self.width = 1300 if width is None else width
        self.height = 700 if height is None else height
        self.widgets = []
        self.tab_view = ctk.CTkTabview(self.root_window)
        self.tab_names = ["Send Messages", "Reminders", "Logs", "Blacklist"]
        self.checkbox_vars = {}
        self.location = None
        self.location_options = []
        self.distance = None
        self.text_distance = None
        self.distance_entry = None
        self.total_volunteers = None
        self.message = None
        self.phone = None
        self.send_button = None
        self.percent_var = None
        self.loading_frame = None
        self.progress_bar = None
        self.option_menu = None
        self.location_ids_types = {}

    def configure_tab_view(self) -> None:
        self.tab_view.pack(fill="both", expand=True)
        self.tab_view.add("Send Messages")
        self.tab_view.add("Reminders")
        self.tab_view.add("Logs")
        self.tab_view.add("Blacklist")
        self.tab_view.tab("Logs").grid_columnconfigure(0, weight=1)
        self.tab_view.tab("Send Messages").focus_set()
        self.tab_view.tab("Send Messages").grid_columnconfigure(0, weight=1)
        self.tab_view.tab("Reminders").grid_rowconfigure(0, weight=1)
        self.tab_view.tab("Reminders").grid_columnconfigure(0, weight=1)
        self.tab_view.tab("Blacklist").grid_columnconfigure(0, weight=1)

    def configure_window_style(self) -> None:
        self.root_window.geometry(f'{self.width}x{self.height}')
        self.root_window.title(f'{self.generic_title} - {self.specific_title}')
        self.root_window.resizable(False, False)

    def load_screen(self):

        self.configure_window_style()
        self.configure_tab_view()
        self.create_reminder_tab()
        self.create_categories_filter()
        self.create_theme_filter()
        self.create_location_filter()
        self.create_box_get_volunteers()
        self.create_message_frame()
        self.create_logs_tab()
        self.create_blacklist_tab()
        x = (self.root_window.winfo_screenwidth() // 2) - (self.width // 2)
        y = (self.root_window.winfo_screenheight() // 2) - (self.height // 2)
        self.root_window.geometry('{}x{}+{}+{}'.format(self.width, self.height, x, y))

    def create_categories_filter(self):
        category_frame = ctk.CTkFrame(self.tab_view.tab(self.tab_names[0]))
        category_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        category_frame.grid_columnconfigure(0, weight=1)
        self.widgets.append(category_frame)

        category_label = ctk.CTkLabel(category_frame, text="Category")
        category_label.grid(row=0, column=0, sticky="w", pady=(0, 5))
        self.widgets.append(category_label)

        categories_options = [
            {"id": "categories_11", "text": "Maatje, buddy & gezelschap", "value": "11"},
            {"id": "categories_10", "text": "Activiteiten\xadbegeleiding", "value": "10"},
            {"id": "categories_19", "text": "Klussen buiten & tuin", "value": "19"},
            {"id": "categories_32", "text": "Taal & lezen", "value": "32"},
            {"id": "categories_5", "text": "Administratie & receptie", "value": "5"},
            {"id": "categories_25", "text": "Begeleiding & coaching", "value": "25"},
            {"id": "categories_17", "text": "Bestuur & organisatie", "value": "17"},
            {"id": "categories_8", "text": "Boodschappen", "value": "8"},
            {"id": "categories_39", "text": "Collecte & inzamelacties", "value": "39"},
            {"id": "categories_4", "text": "Computerhulp & ICT", "value": "4"},
            {"id": "categories_31", "text": "Creativiteit & muziek", "value": "31"},
            {"id": "categories_29", "text": "Dierenverzorging", "value": "29"},
            {"id": "categories_49", "text": "Financiën & fondsenwerving", "value": "49"},
            {"id": "categories_9", "text": "Gastvrijheid & horeca", "value": "9"},
            {"id": "categories_50", "text": "Hulp bij armoede", "value": "50"},
            {"id": "categories_51", "text": "In een winkel", "value": "51"},
            {"id": "categories_38", "text": "Juridisch", "value": "38"},
            {"id": "categories_48", "text": "Klussen binnen", "value": "48"},
            {"id": "categories_2", "text": "Koken & maaltijden", "value": "2"},
            {"id": "categories_14", "text": "Marketing & communicatie", "value": "14"},
            {"id": "categories_46", "text": "Media & design", "value": "46"},
            {"id": "categories_18", "text": "Projectcoördinatie", "value": "18"},
            {"id": "categories_7", "text": "Schoonmaak", "value": "7"},
            {"id": "categories_3", "text": "Techniek & reparatie", "value": "3"},
            {"id": "categories_47", "text": "Training & scholing", "value": "47"},
            {"id": "categories_1", "text": "Vervoer & transport", "value": "1"}
        ]
        self.set_categories(categories_options, category_frame)

    def create_theme_filter(self):
        theme_frame = ctk.CTkFrame(self.tab_view.tab(self.tab_names[0]))
        theme_frame.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        theme_frame.grid_columnconfigure(1, weight=1)
        self.widgets.append(theme_frame)

        theme_label = ctk.CTkLabel(theme_frame, text="Theme")
        theme_label.grid(row=0, column=0, sticky="w", pady=(0, 5))
        self.widgets.append(theme_label)

        theme_options = [
            {"id": "themes_12", "text": "Zorg", "value": "12"},
            {"id": "themes_9", "text": "Sociaal & welzijn", "value": "9"},
            {"id": "themes_8", "text": "Sport & beweging", "value": "8"},
            {"id": "themes_11", "text": "Tuin, dieren & natuur", "value": "11"},
            {"id": "themes_1", "text": "Belangenbehartiging & goede doelen", "value": "1"},
            {"id": "themes_2", "text": "Duurzaamheid & milieu", "value": "2"},
            {"id": "themes_3", "text": "Evenementen & festivals", "value": "3"},
            {"id": "themes_4", "text": "Kunst & cultuur", "value": "4"},
            {"id": "themes_5", "text": "Noodhulp", "value": "5"},
            {"id": "themes_6", "text": "Onderwijs & educatie", "value": "6"},
            {"id": "themes_7", "text": "Politiek", "value": "7"},
            {"id": "themes_10", "text": "Religie & zingeving", "value": "10"}
        ]
        self.set_categories(theme_options, theme_frame)

    def set_categories(self, categories, categories_frame):
        rows_per_column = 13

        for i, category in enumerate(categories):
            column, row = divmod(i, rows_per_column)

            var = ctk.StringVar()
            checkbox = ctk.CTkCheckBox(categories_frame, text=category["text"], variable=var, onvalue=category["value"],
                                       offvalue="", command=lambda: self.on_filter_change())
            checkbox.grid(row=row + 1, column=column, sticky="w", ipady=3, padx=(0, 38))
            self.widgets.append(checkbox)

            self.checkbox_vars[category["id"]] = var

    def create_location_filter(self):
        location_frame = ctk.CTkFrame(self.tab_view.tab(self.tab_names[0]))
        location_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        location_frame.grid_columnconfigure(0, weight=1)
        location_frame.grid_columnconfigure(1, weight=1)
        self.widgets.append(location_frame)

        location_label = ctk.CTkLabel(location_frame, text="Location")
        location_label.grid(row=0, column=0, sticky="w", pady=(0, 5), padx=5)
        self.widgets.append(location_label)

        self.location = ctk.StringVar()
        location_label = ctk.CTkLabel(location_frame, text="find the city or postal code")
        location_label.grid(row=1, column=0, sticky="w", pady=(0, 3), padx=5)
        self.widgets.append(location_label)

        location_entry = ctk.CTkEntry(location_frame, textvariable=self.location)
        location_entry.bind("<Return>", lambda event: self.on_location_change())
        location_entry.bind("<KeyRelease>", lambda event: self.on_location_change())
        location_entry.grid(row=2, column=0, sticky="nsew", padx=5)
        self.widgets.append(location_entry)

        optionmenu_label = ctk.CTkLabel(location_frame, text="Select the City or Postal Code")
        optionmenu_label.grid(row=1, column=1, sticky="w", pady=(0, 3), padx=5)
        self.widgets.append(optionmenu_label)

        option_menu = ctk.CTkOptionMenu(location_frame, values=self.location_options,
                                        command=lambda event: self.on_location_option_change(event))
        option_menu.set("No results found")
        option_menu.grid(row=2, column=1, sticky="nsew", pady=(0, 3), padx=(10, 5))
        self.option_menu = option_menu
        self.widgets.append(self.option_menu)

        self.create_distance_slider(location_frame)

    def create_distance_slider(self, location_frame):
        start_value = 2
        self.distance = ctk.IntVar(value=start_value)

        self.text_distance = ctk.StringVar()
        self.text_distance.set(f"Current Distance: {start_value} km")
        self.distance.trace_add("write", lambda name, index, mode: self.text_distance.set(
            f"Current Distance: {str(self.distance.get())} km"))

        current_value_label = ctk.CTkLabel(location_frame, textvariable=self.text_distance)
        current_value_label.grid(row=5, column=0, sticky="w", pady=(3, 0), padx=5)
        self.widgets.append(current_value_label)

        distance_label = ctk.CTkLabel(location_frame, text="Distance (km)")
        distance_label.grid(row=3, column=0, sticky="w", pady=(15, 3), padx=5)
        self.widgets.append(distance_label)

        slider_frame = ctk.CTkFrame(location_frame)
        slider_frame.grid(row=4, column=0, sticky="nsew", padx=5)
        self.widgets.append(slider_frame)

        start_label = ctk.CTkLabel(slider_frame, text="1 km ")
        start_label.pack(side="left")
        self.widgets.append(start_label)

        distance_entry = ctk.CTkSlider(slider_frame, from_=1, to=50, variable=self.distance)
        distance_entry.bind("<ButtonRelease-1>", lambda event: self.on_distance_change())
        distance_entry.pack(side="left", ipady=3, expand=True, fill="x")
        distance_entry.configure(state="disabled")
        self.distance_entry = distance_entry
        self.widgets.append(distance_entry)

        end_label = ctk.CTkLabel(slider_frame, text="50 km")
        end_label.pack(side="left")
        self.widgets.append(end_label)

    def create_box_get_volunteers(self):
        total_volunteers_frame = ctk.CTkFrame(self.tab_view.tab(self.tab_names[0]))
        total_volunteers_frame.grid(row=1, column=1, sticky="nsew", padx=10, pady=10)
        self.widgets.append(total_volunteers_frame)

        total_volunteers_label = ctk.CTkLabel(total_volunteers_frame, text="Total Volunteers")
        total_volunteers_label.grid(row=0, column=0, sticky="nsew", pady=10, padx=10)
        self.widgets.append(total_volunteers_label)

        self.total_volunteers = ctk.StringVar()

        total_volunteers_count = self.service_manager.get_amount_of_volunteer(self.checkbox_vars,
                                                                              self.location_ids_types,
                                                                              self.location.get(),
                                                                              self.distance.get())
        self.total_volunteers.set(total_volunteers_count)
        total_volunteers_label = ctk.CTkLabel(total_volunteers_frame, font=("Arial", 30),
                                              textvariable=self.total_volunteers)
        total_volunteers_label.place(relx=0.5, rely=0.5, anchor="center")
        self.widgets.append(total_volunteers_label)

    def create_message_frame(self):
        message_frame = ctk.CTkFrame(self.tab_view.tab(self.tab_names[0]))
        message_frame.grid(row=0, column=2, sticky="nsew", rowspan=2, padx=10, pady=10)
        message_frame.grid_columnconfigure(2, weight=4)
        self.widgets.append(message_frame)

        message_label = ctk.CTkLabel(message_frame, text="Message")
        message_label.grid(row=0, column=0, sticky="w", pady=(0, 5), padx=(5, 0))
        self.widgets.append(message_label)

        message_entry = ctk.CTkTextbox(message_frame, width=380, height=450)
        message_entry.grid(row=1, column=0, sticky="nsew", ipady=3, padx=10)
        message_entry.bind("<KeyRelease>", lambda event: self.on_message_change())
        self.message = message_entry
        self.widgets.append(message_entry)

        phone_label = ctk.CTkLabel(message_frame, text="Phone Number")
        phone_label.grid(row=2, column=0, sticky="w", pady=(15, 3))
        self.widgets.append(phone_label)

        self.phone = ctk.StringVar()
        phone_entry = ctk.CTkEntry(message_frame, textvariable=self.phone)
        phone_entry.grid(row=3, column=0, sticky="nsew", ipady=3, padx=10)
        self.widgets.append(phone_entry)

        send_button = ctk.CTkButton(message_frame, text="Send", command=lambda: self.pre_send_message())
        send_button.grid(row=4, column=0, sticky="nsew", pady=(15, 0), padx=10)
        send_button.configure(state="enabled" if len(self.message.get("1.0", "end-1c")) > 3 else "disabled")
        self.send_button = send_button
        self.widgets.append(self.send_button)

    def show_loading_screen(self, tab_view_index: int, randon: bool = True, service: Optional[str] = None):
        loading_frame = ctk.CTkFrame(self.tab_view.tab(self.tab_names[tab_view_index]))
        loading_frame.grid(row=0, column=0, columnspan=3, rowspan=2, sticky="nsew")
        loading_frame.grid_rowconfigure(0, weight=1)
        loading_frame.grid_columnconfigure(0, weight=1)
        self.loading_frame = loading_frame

        inner_frame = ctk.CTkFrame(loading_frame)
        inner_frame.grid(row=0, column=0, columnspan=3, rowspan=2, sticky="nsew", padx=0, pady=0)
        inner_frame.grid_columnconfigure(0, weight=1)
        inner_frame.grid_rowconfigure(0, weight=2)
        inner_frame.grid_rowconfigure(3, weight=2)

        dummy_row = ctk.CTkLabel(inner_frame, text='')
        dummy_row.grid(row=0, column=0, sticky="nsew")
        dummy_row1 = ctk.CTkLabel(inner_frame, text='')
        dummy_row1.grid(row=3, column=0, sticky="nsew")

        progress_bar = ctk.CTkProgressBar(inner_frame, width=400)
        progress_bar.grid(row=1, column=0)
        self.progress_bar = progress_bar

        percent_var = ctk.StringVar()
        percent_label = ctk.CTkLabel(inner_frame, textvariable=percent_var, )
        percent_label.grid(row=2, column=0, sticky="nsew", pady=(5, 0))
        self.percent_var = percent_var

        if randon and service is None:
            self.progress_bar.start()
            self.percent_var.set("Loading...")
        elif randon and service == "reminder":
            self.progress_bar.start()
            self.percent_var.set("Sending reminders...")

    def clean_loading_frame(self):
        self.progress_bar = None
        self.percent_var = None
        if self.loading_frame is not None:
            self.loading_frame.grid_forget()

    def destroy(self):
        for widget in self.widgets:
            if widget.winfo_exists():
                widget.destroy()
        self.tab_view.grid_forget()
        self.service_manager.unsubscribe(self)

    def on_filter_change(self):
        self.service_manager.get_amount_of_volunteer(self.checkbox_vars, self.location_ids_types, self.location.get(),
                                                     self.distance.get())
        self.show_loading_screen(0)

    def on_location_change(self):
        if len(self.location.get()) >= 3:
            self.service_manager.get_location_data(self.location.get())

    def on_location_option_change(self, event):
        self.location.set(event)
        if self.location_ids_types[event][0] is not None and self.location_ids_types[event][1] is not None:
            self.distance_entry.configure(state="disabled")
        else:
            self.distance_entry.configure(state="normal")
        self.on_filter_change()

    def on_distance_change(self):
        if self.distance_entry.cget('state') != "disabled":
            self.on_filter_change()

    def notify(self, service_id, data):
        if service_id == 'notify_location_auto_complete':
            self.update_option_menu(data)
        elif service_id == 'notify_amount_of_volunteer':
            self.update_amount_of_volunteer(data)
        elif service_id == 'notify_starting_messaging':
            self.update_message_starting(data)
        elif service_id == 'notify_get_volunteers':
            self.send_message(data)
        elif service_id == 'notify_progresse_get_volunteers':
            self.update_progress_bar_to_get_volunteers(data)
        elif service_id == 'notify_message_sent':
            self.update_message_sent()
        elif service_id == 'notify_progress_message_sending':
            self.update_progress_bar_to_message_sending(data)

    def update_option_menu(self, data):
        if len(data) == 0:
            self.option_menu.configure(values=[])
            self.option_menu.set("No results found")
            self.location_ids_types = {}
        else:
            data.sort(key=lambda item: item['score'], reverse=True)
            self.location_options = data

            locales = {
                f"{item['name']} ({item['subtitle']})" if item['subtitle'] and item['subtitle'] != 'Postcode' else
                item[
                    'name']: item for item in data}
            self.option_menu.configure(values=list(locales.keys()))
            self.option_menu.set(list(locales.keys())[0])
            self.location_ids_types = {
                f"{item['name']} ({item['subtitle']})" if item['subtitle'] and item['subtitle'] != 'Postcode' else
                item[
                    'name']: (item['id'], item['type'], item['subtitle']) for item in data
            }

    def update_amount_of_volunteer(self, data):
        self.total_volunteers.set(data)
        self.clean_loading_frame()

    def update_message_starting(self, total_seconds):
        step = 1
        for i in range(int(total_seconds), 0, -1):
            time.sleep(1)
            remaining_seconds = i - 1
            step += 1
            self.percent_var.set(f"Messaging will start in {remaining_seconds} seconds.")
            self.update_progress_bar_to_count_seconds(total_seconds, step)
        self.percent_var.set("Messaging started...")

    def pre_send_message(self):
        self.show_loading_screen(0, False)
        self.service_manager.get_volunteers(self.checkbox_vars, self.location_ids_types, self.location.get(),
                                            self.distance.get())

    def send_message(self, data):
        self.clean_loading_frame()
        self.show_loading_screen(0, False)
        self.service_manager.send_messages(self.root_window.username, self.root_window.password,
                                           self.message.get("1.0", "end-1c"), self.phone.get(), data)

    def update_progress_bar_to_get_volunteers(self, current_page: int):
        total_volunteers = int(self.total_volunteers.get().replace('.', ''))
        num_pages = 1 if total_volunteers == 0 else math.ceil(total_volunteers / 23)
        progress = current_page / num_pages
        self.percent_var.set(f"Getting volunteers... {progress * 100:.1f}%")
        self.progress_bar.set(progress)

    def update_message_sent(self):
        self.clean_loading_frame()
        self.clear_message_fields()

    def update_progress_bar_to_count_seconds(self, total_seconds: int, current_sum_of_seconds: int):
        self.progress_bar.set(current_sum_of_seconds / total_seconds)

    def update_progress_bar_to_message_sending(self, data):
        total_volunteers = int(self.total_volunteers.get().replace('.', ''))
        self.percent_var.set(f"Messages Sent: {data} out of {self.total_volunteers.get()}.")
        self.progress_bar.set(data / total_volunteers)

    def clear_message_fields(self):
        self.message.delete("1.0", "end-1c")
        self.phone.set("")

    def on_message_change(self):
        total_characters = len(self.message.get("1.0", "end-1c"))
        if total_characters > 3:
            self.send_button.configure(state="normal")
        else:
            self.send_button.configure(state="disabled")

    def start_reminder_service(self, reminder_frequency: Optional[int] = None,
                               custom_reminder_message: Optional[str] = None):

        self.service_manager.start_reminder_service(reminder_frequency, custom_reminder_message)

    def create_reminder_tab(self):

        reminder_frame = ctk.CTkFrame(self.tab_view.tab(self.tab_names[1]))
        reminder_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self.widgets.append(reminder_frame)

        # Reminder Frequency Frame
        reminder_frequency_frame = ctk.CTkFrame(reminder_frame)
        reminder_frequency_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

        reminder_frequency_label = ctk.CTkLabel(reminder_frequency_frame, text="Reminder Frequency (in days)")
        reminder_frequency_label.grid(row=0, column=0, sticky="w", pady=(0, 5))
        self.widgets.append(reminder_frequency_label)

        reminder_frequency = ctk.StringVar()
        reminder_frequency_entry = ctk.CTkEntry(reminder_frequency_frame, textvariable=reminder_frequency)
        reminder_frequency_entry.grid(row=1, column=0, sticky="nsew", padx=5)
        self.widgets.append(reminder_frequency_entry)

        reminder_message_frame = ctk.CTkFrame(reminder_frame)
        reminder_message_frame.grid(row=0, column=2, sticky="nsew", padx=5, pady=5)

        reminder_message_label = ctk.CTkLabel(reminder_message_frame, text="Reminder Message")
        reminder_message_label.grid(row=0, column=0, sticky="w", pady=(0, 5))
        self.widgets.append(reminder_message_label)
        message_entry = ctk.CTkTextbox(reminder_message_frame, width=380, height=450)
        message_entry.grid(row=1, column=0, sticky="nsew", ipady=3, padx=10)
        message_entry.bind("<KeyRelease>")

        reminder_frequency_frame.place(relx=0.3, rely=0.1, anchor="center")
        reminder_message_frame.place(relx=0.6, rely=0.4, anchor="center")

        def set_reminder_frequency():
            frequency = reminder_frequency.get() or 1
            if type(reminder_frequency.get()) != str and int(reminder_frequency.get()) < 1:
                frequency = 1
                print("Reminder frequency cannot be less than 1 day")

            print(f"Reminder frequency set to {frequency} days")

            return frequency

        def set_custom_reminder_message():
            reminder_message = message_entry.get("1.0", "end-1c")
            return reminder_message

        #    Add a button to start the reminder service
        start_reminder_service_button = ctk.CTkButton(reminder_frame, text="Start reminder service",
                                                      command=lambda: self.start_reminder_service(
                                                          set_reminder_frequency(), set_custom_reminder_message()
                                                      ))

        start_reminder_service_button.grid(row=3, column=0, sticky="nsew", pady=(10, 0))

        start_reminder_service_button.place(relx=0.3, rely=0.2, anchor="center")

        self.widgets.append(start_reminder_service_button)

        stop_reminder_service_button = ctk.CTkButton(reminder_frame, text="Stop reminder service",
                                                     command=lambda: threading.Thread(
                                                         target=self.stop_reminder_service).start()
                                                     )
        stop_reminder_service_button.grid(row=3, column=2, sticky="nsew", pady=(10, 0))
        self.widgets.append(stop_reminder_service_button)

        stop_reminder_service_button.place(relx=0.3, rely=0.3, anchor="center")

    def stop_reminder_service(self):
        print("Stopping reminder service")
        self.service_manager.stop_reminder_service()

    def create_logs_tab(self):
        # Create the main logs frame to take entire height
        logs_frame = ctk.CTkFrame(self.tab_view.tab(self.tab_names[2]), border_width=1, border_color="black")
        logs_frame.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)
        self.widgets.append(logs_frame)

        # Add HEADING label LOGS on top center
        heading_label = ctk.CTkLabel(logs_frame, text="LOGS", font=("Arial", 20))
        heading_label.pack(pady=10, padx=10)  # Use pack for top center alignment

        # Create container frame for info/error and refresh button
        container_frame = ctk.CTkFrame(logs_frame)
        container_frame.pack(fill="both", expand=True)  # Fill remaining space # Fill remaining space

        # Create frames for INFO and ERROR logs with equal width
        container_frame.grid_columnconfigure(0, weight=1)  # Make the first column half the width
        container_frame.grid_columnconfigure(1, weight=1)  # Make the second column half the width

        # Create frames for INFO and ERROR logs
        info_logs_frame = ctk.CTkScrollableFrame(container_frame, border_width=1, border_color="black", height=500)
        info_logs_frame.grid(row=0, column=0, padx=0, pady=0, sticky="nsew")

        error_logs_frame = ctk.CTkScrollableFrame(container_frame, border_width=1, border_color="black", height=500)
        error_logs_frame.grid(row=0, column=1, padx=0, pady=0, sticky="nsew")  # Specify `sticky` for proper resizing

        # Add text labels directly to the scrollable frames
        info_logs_label = ctk.CTkLabel(info_logs_frame, text="INFO", width=80)
        info_logs_label.grid(row=0, column=0, pady=10, padx=10)

        error_logs_label = ctk.CTkLabel(error_logs_frame, text="ERROR", width=80)
        error_logs_label.grid(row=0, column=0, pady=10, padx=10)
        self.widgets.append(info_logs_label)

        self.widgets.append(error_logs_label)

        self.widgets.append(logs_frame)
        self.widgets.append(info_logs_frame)
        self.widgets.append(error_logs_frame)

        # Add Refresh button left aligned
        refresh_button = ctk.CTkButton(container_frame, text="Refresh",
                                       command=lambda: self.clear_and_fetch_logs(error_logs_frame, info_logs_frame))
        refresh_button.grid(row=1, column=0, sticky="w", padx=10, pady=10)  # Left alignment with padding
        self.widgets.append(refresh_button)

        self.fetch_logs(error_logs_frame, info_logs_frame)

    def fetch_logs(self, error_logs_frame, info_logs_frame):
        # Read logs/error.log file and display the logs in the GUI
        with open('logs/error.log', 'r') as file:
            error_logs = file.readlines()
            for i, log in enumerate(error_logs):
                log_label = ctk.CTkLabel(error_logs_frame, text=log, width=80)
                log_label.grid(row=i + 1, column=0, pady=10, padx=10)
                self.widgets.append(log_label)

        with open('logs/info.log', 'r') as file:
            info_logs = file.readlines()
            for i, log in enumerate(info_logs):
                log_label = ctk.CTkLabel(info_logs_frame, text=log, width=80)
                log_label.grid(row=i + 1, column=0, pady=10, padx=10)
                self.widgets.append(log_label)

    def clear_and_fetch_logs(self, error_logs_frame, info_logs_frame):
        #     clear only labels within the frames
        for widget in error_logs_frame.winfo_children()[1:]:
            widget.destroy()

        for widget in info_logs_frame.winfo_children()[1:]:
            widget.destroy()

        self.fetch_logs(error_logs_frame, info_logs_frame)

    def create_blacklist_tab(self):
        # Create a frame for the Blacklist tab
        blacklist_frame = ctk.CTkFrame(self.tab_view.tab("Blacklist"))
        blacklist_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        blacklist_frame.grid_rowconfigure(0, weight=1)
        blacklist_frame.grid_columnconfigure(0, weight=1)
        self.widgets.append(blacklist_frame)

        # Create a sub-frame to hold the input and list in a single column
        center_frame = ctk.CTkFrame(blacklist_frame)
        center_frame.grid(row=0, column=0, sticky="nsew", pady=10)
        center_frame.grid_rowconfigure(3, weight=1)
        center_frame.grid_columnconfigure(0, weight=1)
        self.widgets.append(center_frame)

        # Create a label and entry for inputting a user to blacklist
        blacklist_label = ctk.CTkLabel(center_frame, text="Profile id to Blacklist")
        blacklist_label.grid(row=0, column=0, sticky="w", pady=(0, 5), padx=(20, 0))  # Left padding added
        self.widgets.append(blacklist_label)

        blacklist_entry_var = ctk.StringVar()
        blacklist_entry = ctk.CTkEntry(center_frame, textvariable=blacklist_entry_var)
        blacklist_entry.grid(row=1, column=0, sticky="ew", padx=(20, 0))  # Left padding added
        self.widgets.append(blacklist_entry)

        # Create a button to add the user to the blacklist, smaller and on the left
        add_blacklist_button = ctk.CTkButton(center_frame, text="Add", width=80,  # Set the width to make it smaller
                                             command=lambda: self.add_to_blacklist(blacklist_entry_var.get()))
        add_blacklist_button.grid(row=2, column=0, sticky="w", pady=(10, 0), padx=(20, 5))  # Left padding added
        self.widgets.append(add_blacklist_button)

        # Create a scrollable frame for displaying blacklisted users
        blacklisted_users_frame = ctk.CTkFrame(center_frame,  height=500)
        blacklisted_users_frame.grid(row=4, column=0, sticky="nsew", pady=10, padx=(20, 5))
        self.widgets.append(blacklisted_users_frame)

        # Create a scrollable canvas
        blacklisted_users_canvas = ctk.CTkCanvas(blacklisted_users_frame)
        blacklisted_users_canvas.pack(side="left", fill="both", expand=True)

        # Add a scrollbar
        scrollbar = ctk.CTkScrollbar(blacklisted_users_frame, command=blacklisted_users_canvas.yview)
        scrollbar.pack(side="right", fill="y")
        blacklisted_users_canvas.configure(yscrollcommand=scrollbar.set)

        # Create a frame inside the canvas to hold the blacklisted users list
        blacklisted_users_list_frame = ctk.CTkFrame(blacklisted_users_canvas)
        blacklisted_users_canvas.create_window((0, 0), window=blacklisted_users_list_frame, anchor="nw")

        # Update the canvas to resize based on content
        blacklisted_users_list_frame.bind("<Configure>", lambda e: blacklisted_users_canvas.configure(
            scrollregion=blacklisted_users_canvas.bbox("all")))

        blacklisted_users_frame.configure(height=300)  # Adjust the height as needed

        # Save references for later use
        self.blacklisted_users_canvas = blacklisted_users_canvas
        self.blacklisted_users_list_frame = blacklisted_users_list_frame

        self.display_blacklisted_users()

        # Create a label and entry for removing a user from blacklist
        remove_label = ctk.CTkLabel(center_frame, text="Profile id to Remove")
        remove_label.grid(row=8, column=0, sticky="w", pady=(10, 5), padx=(20, 0))

        remove_entry_var = ctk.StringVar()
        remove_entry = ctk.CTkEntry(center_frame, textvariable=remove_entry_var)
        remove_entry.grid(row=10, column=0, sticky="ew", padx=(20, 0))

        # Create a button to remove user, smaller and on the left
        remove_blacklist_button = ctk.CTkButton(center_frame, text="Remove", width=80,
                                                command=lambda: self.remove_from_blacklist(remove_entry_var.get()))
        remove_blacklist_button.grid(row=12, column=0, sticky="w", pady=(10, 0), padx=(20, 5))


    def display_blacklisted_users(self):
        # Clear current list
        for widget in self.blacklisted_users_list_frame.winfo_children():
            widget.destroy()

        # Get the list of blacklisted users from the service manager
        blacklisted_users = self.service_manager.get_blacklisted_users()

        # Create and place a label for each blacklisted user
        for user_id in blacklisted_users:
            label = ctk.CTkLabel(self.blacklisted_users_list_frame, text=user_id)
            label.pack(anchor="w", padx=5, pady=2)
            self.widgets.append(label)

    def refresh_blacklisted_users(self):
        self.display_blacklisted_users()

    def add_to_blacklist(self, user_id: str) -> None:
        if user_id:
            self.service_manager.add_to_blacklist(user_id)
            self.refresh_blacklisted_users()  # Refresh the list after adding
        else:
            print("No user entered to blacklist")

    def remove_from_blacklist(self, profile_id: str) -> None:
        if profile_id:
            self.service_manager.remove_from_blacklist(profile_id)  # Call service manager function
            self.refresh_blacklisted_users()  # Refresh the list after removal
        else:
            print("No user entered to remove from blacklist")
