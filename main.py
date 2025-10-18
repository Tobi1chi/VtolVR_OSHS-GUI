import sys
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QPushButton, QTextEdit,
    QHBoxLayout, QVBoxLayout, QSplitter, QComboBox, QCheckBox,
    QLabel, QStackedWidget
)
from PyQt6.QtCore import Qt, pyqtSignal, QObject
from PyQt6.QtGui import QFont
from GUI.MainPage import MainPage
from GUI.NewPage import StateMachineEditorPage
# ========== Page 2: 全新页面 ==========

# ========== 主窗口 ==========
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("VTOL VR-Server GUI")
        self.resize(1200, 700)

        # Stack for pages
        self.stacked_widget = QStackedWidget()
        self.setCentralWidget(self.stacked_widget)

        # Create pages
        self.main_page = MainPage(switch_callback=self.switch_to_new_page)
        self.new_page =StateMachineEditorPage(back_callback=self.switch_to_main_page)

        # Add to stack
        self.stacked_widget.addWidget(self.main_page)      # index 0
        self.stacked_widget.addWidget(self.new_page)       # index 1

    def switch_to_new_page(self):
        self.stacked_widget.setCurrentIndex(1)

    def switch_to_main_page(self):
        self.stacked_widget.setCurrentIndex(0)


# ========== 启动 ==========
def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()