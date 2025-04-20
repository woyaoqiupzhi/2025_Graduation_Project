from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *

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

class register_moudle_ui(QWidget):
    def __init__(self):
        super(register_moudle_ui, self).__init__()
        self.setup_component(self)

    def setup_component(self, carrier):
        self.register_page = QtWidgets.QLabel(carrier)
        self.register_page.setGeometry(QtCore.QRect(0, 0, 640, 480))

        font = QtGui.QFont()
        font.setFamily("Arial")
        font.setPointSize(36)

        self.register_page.setFont(font)
        self.register_page.setText("Cam Here")
        self.register_page.setObjectName("label")
        self.register_page.setStyleSheet(
            "background:#fff ;border: 2px dashed #000;color:#000;border-radius: 15px;")
        self.register_page.setAlignment(Qt.AlignCenter)

        label_name = QtWidgets.QLabel(carrier)
        label_name.setGeometry(QtCore.QRect(5, 490, 180, 40))
        label_name.setText(" 输入姓名: ")
        label_name.setStyleSheet(label_style)

        self.lineEdit_name = QtWidgets.QLineEdit(carrier)
        self.lineEdit_name.setGeometry(QtCore.QRect(75, 495, 100, 30))
        self.lineEdit_name.setStyleSheet(macos_style)
        self.lineEdit_name.insert("Mike")

        self.mkdir_btn = QtWidgets.QPushButton(carrier)
        self.mkdir_btn.setGeometry(QtCore.QRect(195, 490, 180, 40))
        self.mkdir_btn.setStyleSheet(btn_style)
        self.mkdir_btn.setText("创建人脸文件夹")

        self.save_btn = QtWidgets.QPushButton(carrier)
        self.save_btn.setGeometry(QtCore.QRect(5, 540, 180, 40))
        self.save_btn.setStyleSheet(btn_style)
        self.save_btn.setText("保存人脸图像")

        self.savefeature_btn = QtWidgets.QPushButton(carrier)
        self.savefeature_btn.setGeometry(QtCore.QRect(195, 540, 180, 40))
        self.savefeature_btn.setStyleSheet(btn_style)
        self.savefeature_btn.setText("保存人脸特征")

        self.opencam_btn = QtWidgets.QPushButton(carrier)
        self.opencam_btn.setGeometry(QtCore.QRect(490, 490, 150, 40))
        self.opencam_btn.setStyleSheet(btn_style)
        self.opencam_btn.setText("打开摄像头")

        self.closecam_btn = QtWidgets.QPushButton(carrier)
        self.closecam_btn.setGeometry(QtCore.QRect(490, 540, 150, 40))
        self.closecam_btn.setStyleSheet(btn_style)
        self.closecam_btn.setText("关闭摄像头")

class recognition_moudle_ui(QWidget):
    def __init__(self):
        super(recognition_moudle_ui, self).__init__()
        self.setup_component(self)

    def setup_component(self, carrier):
        self.recognition_page = QtWidgets.QLabel(carrier)
        self.recognition_page.setGeometry(QtCore.QRect(0, 0, 640, 480))

        font = QtGui.QFont()
        font.setFamily("SimSun")
        font.setPointSize(36)

        self.recognition_page.setFont(font)
        self.recognition_page.setText("Face Det")
        self.recognition_page.setObjectName("label")
        self.recognition_page.setStyleSheet(
            "background:#fff ;border: 2px dashed #000;color:#000;border-radius: 15px;")
        self.recognition_page.setAlignment(Qt.AlignCenter)

        self.opencam_btn = QtWidgets.QPushButton(carrier)
        self.opencam_btn.setGeometry(QtCore.QRect(5, 510, 200, 50))
        self.opencam_btn.setStyleSheet(btn_style)
        self.opencam_btn.setText("打开摄像头")

        self.closecam_btn = QtWidgets.QPushButton(carrier)
        self.closecam_btn.setGeometry(QtCore.QRect(435, 510, 200, 50))
        self.closecam_btn.setStyleSheet(btn_style)
        self.closecam_btn.setText("关闭摄像头")
