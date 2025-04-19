from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtCore import *
from PyQt5.QtGui import QFontDatabase, QFont

class CommonHelper:
    def __init__(self):
        pass

    @staticmethod
    def readQss(style):
        with open(style, 'r') as f:
            return f.read()

# 风格样式  QSS文件读取
macos_style = CommonHelper.readQss("DCUI/style/macos.qss")
label_style = CommonHelper.readQss("DCUI/style/lineEdit_mac.qss")
btn_style = CommonHelper.readQss("DCUI/style/btn_mac.qss")
     
class tcp_moudle_ui(object):
    signal_write_msg = QtCore.pyqtSignal(str)

    def setup_component(self, carrier):
        fontDb = QFontDatabase()
        fontID = fontDb.addApplicationFont("style/7211.ttf")  # 此处的路径为qrc文件中的字体路径

        label_ip = QtWidgets.QLabel(carrier)
        label_ip.setGeometry(QtCore.QRect(5, 5, 310, 40))
        label_ip.setText(" 目标IP: ")
        label_ip.setStyleSheet(label_style)

        self.lineEdit_ip = QtWidgets.QLineEdit(carrier)
        self.lineEdit_ip.setGeometry(QtCore.QRect(55, 10, 250, 30))
        self.lineEdit_ip.setStyleSheet(macos_style)
        self.lineEdit_ip.insert("192.168.4.1")

        label_port = QtWidgets.QLabel(carrier)
        label_port.setGeometry(QtCore.QRect(5, 50, 150, 40))
        label_port.setText(" 端口号: ")
        label_port.setStyleSheet(label_style)

        self.lineEdit_port = QtWidgets.QLineEdit(carrier)
        self.lineEdit_port.setGeometry(QtCore.QRect(55, 55, 90, 30))
        self.lineEdit_port.setStyleSheet(macos_style)
        self.lineEdit_port.insert("5000")

        self.connect_btn = QtWidgets.QPushButton(carrier)
        self.connect_btn.setGeometry(QtCore.QRect(160, 50, 155, 40))
        self.connect_btn.setStyleSheet(btn_style)
        self.connect_btn.setText("连接")

        self.register_btn = QtWidgets.QPushButton(carrier)
        self.register_btn.setGeometry(QtCore.QRect(5, 100, 310, 40))
        font = QtGui.QFont()
        font.setFamily("7211")
        self.register_btn.setFont(font)
        self.register_btn.setStyleSheet(btn_style)
        self.register_btn.setText("人脸录入")

        self.recognition_btn = QtWidgets.QPushButton(carrier)
        self.recognition_btn.setGeometry(QtCore.QRect(5, 150, 310, 40))
        self.recognition_btn.setStyleSheet(btn_style)
        self.recognition_btn.setText("打开人脸识别")

         # Logo
        self.label_log = QtWidgets.QLabel(carrier)
        self.label_log.setGeometry(QtCore.QRect(5, 200, 310, 390))
        font = QtGui.QFont()
        font.setFamily("YOUSHEhaoshenti")
        font.setPointSize(12)
        self.label_log.setFont(font)
        self.label_log.setText("数据日志")
        self.label_log.setObjectName("label")
        self.label_log.setStyleSheet(
            "background-color:#ffffff;color:#3d3d3d;border-radius: 15px;")
        self.label_log.setAlignment(Qt.AlignHCenter)

        self.data_log = QtWidgets.QTextEdit(carrier)
        self.data_log.setGeometry(QtCore.QRect(12, 230, 296, 340))
        self.data_log.setStyleSheet(label_style)
