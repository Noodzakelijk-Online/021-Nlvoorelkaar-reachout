def center_window(root_window):
    width = root_window.winfo_width()
    height = root_window.winfo_height()
    x = (root_window.winfo_screenwidth() // 2) - (width // 2)
    y = (root_window.winfo_screenheight() // 2) - (height // 2)
    root_window.geometry('{}x{}+{}+{}'.format(width, height, x, y))
