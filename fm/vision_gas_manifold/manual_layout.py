"""GUI to control the gas manifold for the VISION Prime microscope"""
import sys
import socket
import traceback
import json

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout,
    QHBoxLayout, QLabel, QSlider, QPushButton,
    QStackedLayout, QStackedWidget,
    QMessageBox, QFrame,
)
from PyQt6.QtGui import QPixmap, QColor, QPalette
from PyQt6.QtCore import Qt, QSize, QTimer, QRunnable, QThreadPool, pyqtSlot, pyqtSignal, QObject, QRect
from valve import ValveIndicator

__APP_VERSION__ = '0.2'

# Constants
SIMULATE = False
if len(sys.argv) > 1:
    if sys.argv[1] == '--simulate':
        SIMULATE = True
if not SIMULATE:
    HOST = socket.gethostbyname('surfcat-fm-revpi01.fys.clients.local')
WINDOW_TITLE = "  VISION  Prime  \n   Gas Manifold  "
TITLE_SIZE = 30
SUBTITLE_SIZE = 24
NO_OF_VALVES = 13
INDICATOR_DICT = {
    1: (200, 82, 'hori', 'Valve 1'),
    2: (220, 142, 'hori', 'Valve 2'),
    3: (188, 282, 'hori', 'Valve 3'),
    4: (278, 342, 'hori', 'Valve 4'),
    5: (416, 144, 'vert', 'Valve 5'),
    6: (470, 205, 'hori', 'Valve 6'),
    7: (370, 233, 'vert', 'Valve 7'),
    8: (541, 233, 'vert', 'Valve 8'),
    9: (498, 342, 'hori', 'Valve 9'),
    10: (489, 82, 'hori', 'Valve 10'),
    11: (320, 122, 'vert', 'UHV 1'),
    12: (220, 240, 'vert', 'UHV 2'),
    13: (380, 387, 'vert', 'UHV 3'),
}
LABEL_DICT = {
    1: {
        'size': QSize(100, 24),
        'pos': (540, 88),
        'name': 'label_pressure_p1',
    },
    2: {
        'size': QSize(100, 24),
        'pos': (540, 172),
        'name': 'label_pressure_p2',
    },
    3: {
        'size': QSize(100, 24),
        'pos': (540, 308),
        'name': 'label_pressure_p3',
    },
    4: {
        'size': QSize(100, 24),
        'pos': (272, 454),
        'name': 'label_pressure_uhv',
    },
}

class WorkerSignals(QObject):
    """Signals from a running worker thread.

    error
        tuple (exctype, value, traceback.format_exc())

    result
        object data returned from processing, anything
    """

    error = pyqtSignal(tuple)
    result = pyqtSignal(object)

class Worker(QRunnable):

    def __init__(self, fn, *args, **kwargs):
        super().__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()

    @pyqtSlot()
    def run(self):
        try:
            result = self.fn(*self.args, **self.kwargs)
        except Exception:
            traceback.print_exc()
            exctype, value = sys.exc_info()[:2]
            self.signals.error.emit((exctype, value, traceback.format_exc()))
        else:
            print('Emitting result: ', result)
            self.signals.result.emit(result)

def set_color(widget, color):
    widget.setAutoFillBackground(True)
    palette = widget.palette()
    palette.setColor(QPalette.ColorRole.Window, QColor(color))
    widget.setPalette(palette)

class ContainerWidget(QWidget):
    def __init__(self, object_name="", parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True) 
        self.setObjectName(object_name)

class HoverLayoutWidget(QWidget):
    def __init__(self, parent=None, row=None):
        super().__init__(parent)
        self.__row = row
        self.__qss_enter = f"border: 2px solid #80ffff;border-radius: 15px;background-color: #ffffff;"
        """
        self.__qss_enter = "background-color: qradialgradient(cx: 0.5, cy; 0.5, radius: 15px, fx: 0.5, fy: 0.5, stop: 0 #007bff, stop: 0.98 #007bff, stop: 1.0 transparent);"
        self._qss_enter =         'border: 3px solid lightgray; \
                                   border-radius: 12px; \
                                   background: \
                                       QLinearGradient( \
                                           y1: 0, y2: 1, \
                                           stop: 0 white, \
                                           stop: 0.2 red, \
                                           stop: 0.8 blue, \
                                           stop: 1 green \
                                       );'
        """
        self.__qss_leave = f""
        self.indicators = []
    
    def add_indicator(self, indicator):
        self.indicators.append(indicator)
    
    def enterEvent(self, event):
        if self.__row and self.indicators:
            for indicator in self.indicators:
                indicator.setStyleSheet(self.__qss_enter)
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        if self.__row and self.indicators:
            for indicator in self.indicators:
                indicator.setStyleSheet(self.__qss_leave)
        super().leaveEvent(event)

QSS = """
ContainerWidget {
    border: 2px solid gray;
    border-radius: 10px;
}
HoverLayoutWidget {
    border: 1px solid grey;
}
QLabel {
    color: #EEEEEE;
}
QMessageBox {
    background-color: #333333;
}
"""

class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle(WINDOW_TITLE)
        self.setStyleSheet(QSS)

        # Create the central widget and give it a layout.
        self.central_widget = QWidget()
        set_color(self.central_widget, '#333333')
        self.setCentralWidget(self.central_widget)
        self.hbox_layout_1 = QHBoxLayout(self.central_widget)
        self.main_layout = QVBoxLayout()
        self.vbox_layout_2 = QVBoxLayout()

        # App title
        self.window_title = QLabel(WINDOW_TITLE)
        font = self.window_title.font()
        font.setPointSize(TITLE_SIZE)
        self.window_title.setFont(font)
        self.window_title.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        
        # Info labels
        self.info_container = ContainerWidget()
        self.info_layout = QVBoxLayout()
        self.label_info_title = QLabel('Info')
        # TODO: font stuff
        self.label_clients = QLabel()
        self.label_clients.setGeometry(QRect(910, 90, 271, 131))
        self.label_clients.setFrameShape(QFrame.Shape.Panel)
        self.label_clients.setFrameShadow(QFrame.Shadow.Sunken)
        self.label_clients.setText("")
        self.label_clients.setAlignment(Qt.AlignmentFlag.AlignLeading | Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self.label_clients.setWordWrap(True)
        self.label_info = QLabel()
        self.label_info.setGeometry(QRect(910, 90, 271, 131))
        self.label_info.setFrameShape(QFrame.Shape.Panel)
        self.label_info.setFrameShadow(QFrame.Shadow.Sunken)
        self.label_info.setText("")
        self.label_info.setAlignment(Qt.AlignmentFlag.AlignLeading | Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self.label_info.setWordWrap(True)
        # Add to layout
        self.info_layout.addWidget(self.label_info_title)
        self.info_layout.addWidget(self.label_info)
        self.info_layout.addWidget(self.label_clients)
        self.info_container.setLayout(self.info_layout)

        # Main window
        self.main_window = ContainerWidget("main")
        self.main_window.setFixedSize(800, 600)
        main_win_layout = QHBoxLayout()
        main_win_layout.setContentsMargins(0, 0, 0, 0)
        main_win_layout.setSpacing(0)
        self.main_window.setLayout(main_win_layout)
        self.main_background = QLabel()
        #self.main_background.setPixmap(QPixmap("images/main_background.svg"))
        self.main_background.setPixmap(QPixmap("images/main_background.png"))
        main_win_layout.addWidget(self.main_background)
        # Create pressure labels
        for key, item in LABEL_DICT.items():
            label = QLabel(f"N/A mbar", parent=self.main_window)
            label.setFixedSize(item['size'])
            label.move(*item['pos'])
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            setattr(self, item['name'], label)

        # Valve control window
        self.valve_control_widget = ContainerWidget()
        self.valve_control_layout = QVBoxLayout(self.valve_control_widget)
        self.valve_title = QLabel("Valve controls")
        font = self.valve_title.font()
        font.setPointSize(SUBTITLE_SIZE)
        self.valve_title.setFont(font)
        self.valve_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.valve_control_layout.addWidget(self.valve_title)
        #self.valve_control_layout.setContentsMargins(10,10,10,10)
        self.valve_control_layout.setSpacing(7)
        
        # Create valve button controls
        stitle = self.valve_title.sizeHint()
        maxw, maxh = stitle.width(), 0
        for i in range(1, NO_OF_VALVES + 1):
            if i in INDICATOR_DICT:
                hover_layout_widget = HoverLayoutWidget(row=i)
                row_layout = QHBoxLayout()
                self.valve_control_layout.addWidget(hover_layout_widget)
            else:
                row_layout = QHBoxLayout()
                self.valve_control_layout.addLayout(row_layout)
            row_layout.setContentsMargins(0,0,0,0)
            row_layout.setSpacing(7)
            label = QLabel(f"Valve {i}")
            vopen = QPushButton(f"Open")
            vclose = QPushButton(f"Close")
            setattr(self, f"v{i}_label", label)
            setattr(self, f"v{i}_open", vopen)
            setattr(self, f"v{i}_close", vclose)
            for _qwidget in [label, vopen, vclose]:
                _qwidget.setFixedSize(70, 24)
                row_layout.addWidget(_qwidget)
            if i in INDICATOR_DICT:
                x, y, orientation, name = INDICATOR_DICT[i]
                label.setText(name)
                indicator_stack = QStackedWidget(self.main_window)
                setattr(self, f"indicator_{i}", indicator_stack)
                for state in (False, True):
                    indicator = ValveIndicator(orientation=orientation, state=state)
                    indicator_stack.addWidget(indicator)
                    # Tie the valve indicator to the button controls
                    hover_layout_widget.add_indicator(indicator)
                # Place indicators
                dx, dy = indicator.center
                indicator_stack.move(x - dx, y - dy)
                # Change size if vertical
                if orientation.startswith('v'):
                    indicator_stack.setFixedSize(30, 40)
                # Apply function handlers
                vclose.clicked.connect(self.generate_valve_function(i, 0))
                vopen.clicked.connect(self.generate_valve_function(i, 1))
                hover_layout_widget.setLayout(row_layout)
        maxh = 31 * NO_OF_VALVES + stitle.height()
        self.valve_control_widget.setFixedSize(250, maxh)

        # Turbo control window
        self.turbo_control_widget = ContainerWidget()
        #self.turbo_control_widget.setFixedSize(250, 400)
        self.turbo_control_layout = QVBoxLayout(self.turbo_control_widget)
        self.turbo_title = QLabel("Extra controls")
        font = self.turbo_title.font()
        font.setPointSize(SUBTITLE_SIZE)
        self.turbo_title.setFont(font)
        self.turbo_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.turbo_control_layout.addWidget(self.turbo_title)
        #self.turbo_control_layout.setContentsMargins(10,10,10,10)
        self.turbo_control_layout.setSpacing(7)

        # Apply layouts
        self.window_title_h_layout = QHBoxLayout()
        self.window_title_h_layout.addWidget(self.window_title)
        self.window_title_h_layout.addWidget(self.info_container)
        #self.main_layout.addWidget(self.window_title)
        self.main_layout.addLayout(self.window_title_h_layout)
        self.main_layout.addWidget(self.main_window)
        self.hbox_layout_1.addLayout(self.main_layout)
        self.hbox_layout_1.addLayout(self.vbox_layout_2)
        self.vbox_layout_2.addWidget(self.turbo_control_widget)
        self.vbox_layout_2.addWidget(self.valve_control_widget)
        self.setStyleSheet(QSS)
        
        # Other stuff
        if not SIMULATE:
            self._connect_to_server() # blocking on purpose
        self.threadpool = QThreadPool()
        thread_count = self.threadpool.maxThreadCount()
        print(f"Multithreading with maximum {thread_count} threads")
        
    def _connect_to_server(self):
        # Register GUI
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(1)
        sock.connect(('servcinf-sql.fysik.dtu.dk', 80))
        self.ip = sock.getsockname()[0]
        sock.close()
        self.hostname = socket.gethostname()
        # Following stopped working after some time - probably blocked by IT Dep
        #self.ip = socket.gethostbyname(self.hostname + '.fys.clients.local')
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(1)
        sock.sendto(f'raw_wn#enlist:str:enlist;hostname:str:{self.hostname};ip:str:{self.ip}'.encode(), (HOST, 8500))
        try:
            ret = sock.recv(1024).decode()
        except TimeoutError:
            print('Problem connecting to server - try again')
            raise
        assert ret[:3] == 'ACK'
        # Data attributes
        self.data = None
        self.clients = None
        self.valve_inputs = None
        self.valve_outputs = None
        self.pressure_uhv = None
        self.pressure_gas1 = None
        self.pressure_gas2 = None
        self.pressure_gas3 = None
        
        # Timer to query server for data
        self.timer = QTimer()
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self.timeout)
        self.timer.start()

    def generate_valve_function(self, number, onoff):
        if SIMULATE:
            indicator = getattr(self, f"indicator_{number}")
            index = 0
            if onoff:
                index = 1
            def valve_toggle():
                indicator.setCurrentIndex(index)
                return onoff
            return valve_toggle
        def valve_worker():
            def valve_toggle():
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                sock.settimeout(1)
                command = f'raw_wn#set_valve:int:{number},{int(onoff)};ip:str:{self.ip}'
                sock.sendto(command.encode(), (HOST, 8500))
                try:
                    ret = sock.recv(1024).decode()
                    print(ret)
                except TimeoutError:
                    print('Problem connecting to server - try again')
                    raise
                assert ret[:3] == 'ACK'
                return ret
            worker = Worker(valve_toggle)
            worker.signals.error.connect(self.error_popup)
            self.threadpool.start(worker)
        return valve_worker

    def pullerror(self, error):
        self.comms = 'failing'
        self.label_info.setText(f'Connection: {self.comms}')

    def error_popup(self, error):
        for e in error:
            print(e)
        QMessageBox.warning(self, str(error[1]), f"{str(error[0])}\n{error[2]}")
        
    def timeout(self):
        worker = Worker(get_state)
        worker.signals.error.connect(self.pullerror)
        worker.signals.result.connect(self.handle_data)
        self.threadpool.start(worker)

    def handle_data(self, data):
        if data is None:
            print('Empty data in self.handle_data')
            return
        """Process the data returned by the server pull socket"""
        self.comms = 'working'
        self.label_info.setText(f'Connection: {self.comms}')
        self.data = data
        self.valve_inputs = data['inputs'][1]
        self.valve_outputs = data['outputs'][1]
        self.pressure_uhv = data['pressure_uhv'][1]
        self.pressure_gas1 = data['pressure_gas1'][1]
        self.pressure_gas2 = data['pressure_gas2'][1]
        self.pressure_gas3 = data['pressure_gas3'][1]
        self.clients = [f'{client["name"]}:{ip}\n' for ip, client in data['clients'][1].items()]
        self.clients.sort()
        # Print clients label
        self.label_clients.setText(''.join(self.clients))
        # Process input states
        for i, state in enumerate(self.valve_inputs):
            if i in INDICATOR_DICT:
                indicator = getattr(self, f"indicator_{i}")
                if state:
                    index = 1
                else:
                    index = 0
                indicator.setCurrentIndex(index)
        # Process output states
        #print('Outputs: ', self.valve_outputs)
        # TODO
        # Process pressures
        text = f"{self.pressure_uhv:.2e} mbar" if type(self.pressure_uhv) == float else self.pressure_uhv
        self.label_pressure_uhv.setText(text)
        text = f"{self.pressure_gas1:.2e} mbar" if type(self.pressure_gas1) == float else self.pressure_gas1
        self.label_pressure_p1.setText(text)
        text = f"{self.pressure_gas2:.2e} mbar" if type(self.pressure_gas2) == float else self.pressure_gas2
        self.label_pressure_p2.setText(text)
        text = f"{self.pressure_gas3:.2e} mbar" if type(self.pressure_gas3) == float else self.pressure_gas3
        self.label_pressure_p3.setText(text)

def get_state():
    if SIMULATE:
        return
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(1)
    sock.sendto('json_wn'.encode('utf-8'), (HOST, 9000))
    ret = sock.recv(1024).decode()
    data = json.loads(ret)
    for key in data:
        if data[key] == 'OLD_DATA':
            print(f'"{key}" has not been updated recently on the socket server')
    return data

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
