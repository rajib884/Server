import threading

from infi.systray import SysTrayIcon

from manage import main as django_server

hover_text = "Moelist"
server_running = False


def start_server(sys_tray):
    global server_running
    if not server_running:
        server_running = True
        threading.Thread(target=django_server, daemon=False).start()
    else:
        print("Server is already running")


def simon_bitch(sys_tray):
    print("Hello Simon.")


def bye(sys_tray):
    print('Bye, then.')


def do_nothing(sys_tray):
    pass


menu_options = (('Start Server', "hello.ico", start_server),
                ('Do nothing', None, do_nothing),
                ('A sub-menu', "submenu.ico", (('Say Hello to Simon', "simon.ico", simon_bitch),
                                               ('Do nothing', None, do_nothing),
                                               ))
                )

stray = SysTrayIcon(
    icon=r"D:\PythonServer\MoeList\static\MoeList\icon.ico",
    hover_text=hover_text,
    menu_options=menu_options,
    on_quit=bye,
    default_menu_index=0,
    window_class_name=None
)

stray.start()

# while True:
#     sleep(1)
#     print("Second Thread")
