from PyQt6.QtWidgets import QPushButton, QLabel
from PyQt6.QtGui import QPainter, QPolygon, QColor, QRegion
from PyQt6.QtCore import QPoint



class ValveIndicator(QLabel):

    def __init__(self, orientation=None, state=None, parent=None):
        super().__init__(parent=parent)
        if orientation is None or orientation.lower().startswith('h'):
            self.orientation = 'horizontal'
            self.w = 40
            self.h = 30
        else:
            self.orientation = 'vertical'
            self.w = 30
            self.h = 40
        self.setFixedSize(self.w, self.h)
        self.center = (self.w//2, self.h//2)
        
        # State defaults to False
        self.state = False
        if state:
            self.state = True
        
        # Color definitions
        self.off_color = QColor("#9c2007")
        #self.on_color = QColor("#adff2f")
        self.on_color = QColor("#0dd442")

    def _get_polygons(self):
        offset = 3
        if self.orientation == 'horizontal':
            # left triangle
            left_triangle = QPolygon([
                QPoint(0 + offset, self.h - offset),
                QPoint(self.w // 2, self.h // 2),
                QPoint(0 + offset, 0 + offset),
            ])
            # right triangle
            right_triangle = QPolygon([
                QPoint(self.w - offset, self.h - offset),
                QPoint(self.w - offset, 0 + offset),
                QPoint(self.w // 2, self.h // 2),
            ])
            return (left_triangle, right_triangle)
        else:
            # bottom triangle
            top_triangle = QPolygon([
                QPoint(0 + offset, 0 + offset),
                QPoint(self.w // 2, self.h // 2),
                QPoint(self.w - offset, 0 + offset),
            ])
            # top triangle
            bottom_triangle = QPolygon([
                QPoint(self.w - offset, self.h - offset),
                QPoint(self.w // 2, self.h // 2),
                QPoint(0 + offset, self.h - offset),
            ])
            return (bottom_triangle, top_triangle)
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        if self.state:
            painter.setBrush(self.on_color)
        else:
            painter.setBrush(self.off_color)
        for polygon in self._get_polygons():
            painter.drawPolygon(polygon)

        #region = QRegion(left_triangle).united(QRegion(right_triangle))
        #self.setMask(region)
        
if __name__ == '__main__':
    from PyQt6.QtCore import Qt
    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtWidgets import QVBoxLayout
    from PyQt6.QtWidgets import QWidget
    import sys
    
    class Demo(QWidget):
        def __init__(self, parent=None):
            QWidget.__init__(self, parent)
            layout = QVBoxLayout(self)
            self.v1 = ValveIndicator()
            self.v2 = ValveIndicator(orientation='vert')
            self.v3 = ValveIndicator(state=True)
            self.v4 = ValveIndicator(orientation='ve', state=2)
            layout.addWidget(self.v1)
            layout.addWidget(self.v2)
            layout.addWidget(self.v3)
            layout.addWidget(self.v4)
            self.setLayout(layout)
    
    app = QApplication(sys.argv)
    demo = Demo()
    demo.show()
    sys.exit(app.exec())
