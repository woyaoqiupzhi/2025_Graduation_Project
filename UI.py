import socket
import sys
import threading
import time
import cv2
import csv
import stopThreading

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from DCUI.connect_moudle import tcp_moudle_ui
from DCUI.face_register import recognition_moudle_ui, register_moudle_ui
from face_reco_from_camera_ot_single_person import Face_Recognizer_single
from features_extraction_to_csv import *

def myframe_resize(frame):
    if frame.shape[1] > frame.shape[0]:
        resize_scale = 640 / frame.shape[1]
        frame = cv2.resize(frame, (0, 0), fx=resize_scale, fy=resize_scale)
    else:
        resize_scale = 480 / frame.shape[0]
        frame = cv2.resize(frame, (0, 0), fx=resize_scale, fy=resize_scale)
    return frame

def show_frame(frame, show_area):
    frame = myframe_resize(frame)          # opencv读取的bgr格式图片转换成rgb格式
    img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    _image = QtGui.QImage(img[:], img.shape[1], img.shape[0], img.shape[1] * 3,
                          QtGui.QImage.Format_RGB888)  # pyqt5转换成自己能放的图片格式
    jpg_out = QtGui.QPixmap(_image)  # 转换成QPixmap
    show_area.setPixmap(jpg_out)  # 设置图片显示

class FaceMainwindow(QMainWindow, tcp_moudle_ui):
    def __init__(self):
        super(FaceMainwindow, self).__init__()
        self.stack_pages = None
        self.signal_data_msg = None
        self.SetMainUI(self)
        self.setup_component(self)
        self.registerpage = register_moudle_ui()
        self.recognitionpage = recognition_moudle_ui()
        self.stack_pages.addWidget(self.registerpage)
        self.stack_pages.addWidget(self.recognitionpage)
        self.SlotFunction_binding()
        self.stopEvent = threading.Event()
        self.stopEvent.clear()
        self.stopEvent_control = threading.Event()
        self.stopEvent_control.clear()
        self.save_flag = 0
        self.font = cv2.FONT_ITALIC
        # FPS
        self.frame_time = 0
        self.frame_start_time = 0
        self.fps = 0
        # 录入人脸计数器 / cnt for counting faces in current frame
        self.current_frame_faces_cnt = 0
        # TCP连接
        self.link = False  # 用于标记是否开启了连接
        self.tcp_socket = None
        self.sever_th = None
        self.client_th = None
        self.send_th = None
        self.client_socket_list = list()
        self.send_name = ""

    def SlotFunction_binding(self):
        self.register_btn.clicked.connect(self.show_page_0)
        self.recognition_btn.clicked.connect(self.show_page_1)
        self.connect_btn.clicked.connect(self.tcp_client_start)
        self.signal_write_msg.connect(self.write_msg)
        self.registerpage.opencam_btn.clicked.connect(self.open_cam)
        self.registerpage.closecam_btn.clicked.connect(self.close_cam)
        self.registerpage.mkdir_btn.clicked.connect(self.mkdir)
        self.registerpage.save_btn.clicked.connect(self.start_save_image)
        self.registerpage.savefeature_btn.clicked.connect(self.save_features)
        self.recognitionpage.opencam_btn.clicked.connect(self.open_cam_control)
        self.recognitionpage.closecam_btn.clicked.connect(self.close_cam_control)

    def write_msg(self, msg):
        # signal_write_msg信号会触发这个函数
        """
        功能函数，向接收区写入数据的方法
        信号-槽触发
        tip：PyQt程序的子线程中，直接向主线程的界面传输字符是不符合安全原则的
        :return: None
        """
        self.data_log.append(msg)

    def SetMainUI(self, MainUi):
        MainUi.setObjectName("MainUi")
        MainUi.setWindowTitle("人脸识别智能柜")
        MainUi.setFixedSize(965, 605)

        # 页面堆栈
        self.stack_pages = QtWidgets.QStackedWidget(MainUi)
        self.stack_pages.setGeometry(QtCore.QRect(320, 5, 640, 600))
        font = QtGui.QFont()
        font.setBold(True)
        font.setWeight(75)
        self.stack_pages.setFont(font)
        self.stack_pages.setObjectName("stack_pages")

    def open_cam(self):
        self.registerpage.opencam_btn.setDisabled(True)
        th = threading.Thread(target=self.operate_cam)
        th.start()

    def mkdir(self):
        name = self.registerpage.lineEdit_name.text()
        if name:
            current_face_dir = "data/data_faces_from_camera/" + name
            if os.path.isdir(current_face_dir):
                self.data_log.append('已存在该命名的文件夹\n')
            else:
                os.mkdir(current_face_dir)
                self.data_log.append(
                    f"新建的人脸文件夹 / Create folders: {current_face_dir}")
        else:
            pass

    def start_save_image(self):
        self.save_flag = 1

    def update_fps(self):
        now = time.time()
        self.frame_time = now - self.frame_start_time
        self.fps = 1.0 / self.frame_time
        self.frame_start_time = now

    def draw_note(self, img_rd):
        # 添加说明 / Add some notes
        cv2.putText(img_rd, "Face Register", (20, 40), self.font,
                    1, (255, 255, 255), 1, cv2.LINE_AA)
        cv2.putText(img_rd, "FPS:   " + str(self.fps.__round__(2)), (20, 100), self.font, 0.8, (0, 255, 0), 1,
                    cv2.LINE_AA)
        cv2.putText(img_rd, "Faces: " + str(self.current_frame_faces_cnt),
                    (20, 140), self.font, 0.8, (0, 255, 0), 1, cv2.LINE_AA)

    def face_det(self, faces, frame):
        if len(faces) != 0:
            for k, d in enumerate(faces):
                # 计算矩形框大小 / Compute the size of rectangle box
                height = (d.bottom() - d.top())
                width = (d.right() - d.left())
                hh = int(height/2)
                ww = int(width/2)

                # 6. 判断人脸矩形框是否超出 480x640 / If the size of ROI > 480x640
                if (d.right()+ww) > 640 or (d.bottom()+hh > 480) or (d.left()-ww < 0) or (d.top()-hh < 0):
                    cv2.putText(frame, "OUT OF RANGE", (20, 300),
                                cv2.FONT_ITALIC, 0.8, (0, 0, 255), 1, cv2.LINE_AA)
                    color_rectangle = (0, 0, 255)
                    if self.save_flag:
                        self.data_log.append("人脸不在检测范围，请调整位置")
                        self.save_flag = 0
                else:
                    color_rectangle = (255, 255, 255)

                cv2.rectangle(frame,
                              tuple([d.left() - ww, d.top() - hh]),
                              tuple([d.right() + ww, d.bottom() + hh]),
                              color_rectangle, 2)
                # 7. 根据人脸大小生成空的图像 / Create blank image according to the size of face detected
                img_blank = np.zeros(
                            (int(height*2), width*2, 3), np.uint8)
                if self.save_flag:
                    name = self.registerpage.lineEdit_name.text()
                    if name:
                        current_face_dir = "data/data_faces_from_camera/" + name
                        if os.path.isdir(current_face_dir):
                            num = len(os.listdir(current_face_dir))
                            for ii in range(height*2):
                                for jj in range(width*2):
                                    img_blank[ii][jj] = frame[d.top(
                                    )-hh + ii][d.left()-ww + jj]
                            cv2.imwrite(current_face_dir + "/img_face_" +
                                        str(num + 1) + ".jpg", img_blank)
                            self.data_log.append(f'已存在 {name} 文件夹\n')
                    else:
                        QMessageBox.warning(
                            self, '警告', "先输入姓名检查是否有文件夹！", QMessageBox.Yes | QMessageBox.No,
                            QMessageBox.No)

                    self.save_flag = 0
        self.current_frame_faces_cnt = len(faces)

        # 9. 生成的窗口添加说明文字 / Add note on cv2 window
        self.draw_note(frame)
        self.update_fps()
        return frame

    def save_features(self):
        self.data_log.clear()
        # 获取已录入的最后一个人脸序号 / Get the order of latest person
        person_list = os.listdir("data/data_faces_from_camera/")

        with open("data/features_all.csv", "w", newline="") as csvfile:
            writer = csv.writer(csvfile)
            for person in person_list:
                features_mean_personX = return_features_mean_personX(
                    path_images_from_camera + person)
                writer.writerow(features_mean_personX)
                self.data_log.append(
                    f" >> 特征均值 / The mean of features:{list(features_mean_personX)}'\n'")
            self.data_log.append(
                "所有录入人脸数据存入 / Save all the features of faces registered into: data/features_all.csv")

    def operate_cam(self):
        cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        if not cap.isOpened():
            raise ValueError("Video open failed.")
        ret, frame = cap.read()

        while ret:
            ret, frame = cap.read()
            if ret:
                frame = cv2.flip(frame, 1)
                faces = detector(frame, 0)         # Use Dlib face detector
                frame = self.face_det(faces, frame)
                show_frame(frame, self.registerpage.register_page)

            if cv2.waitKey(25) & self.stopEvent.is_set() == True:
                self.stopEvent.clear()
                self.registerpage.opencam_btn.setEnabled(True)
                self.reset_cam()
                break

    def close_cam(self):
        self.stopEvent.set()
        self.reset_cam()

    def reset_cam(self):
        self.registerpage.opencam_btn.setEnabled(True)
        self.registerpage.register_page.setPixmap(QPixmap(""))
        self.registerpage.register_page.setText("Cam Here")

    def open_cam_control(self):
        self.recognitionpage.opencam_btn.setDisabled(True)
        th = threading.Thread(target=self.control_cam)
        th.start()

    def control_cam(self):
        model = Face_Recognizer_single()
        cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        if not cap.isOpened():
            raise ValueError("Video open failed.")
        ret, frame = cap.read()

        while ret:
            ret, frame = cap.read()
            if ret:
                frame = cv2.flip(frame, 1)
                frame,name_list = model.process(frame)
                if name_list:
                    self.data_log.append(f"检测结果:{name_list[0]}\n" )
                    self.send_name = name_list[0]
                else:
                    self.send_name = ""
                    self.data_log.append("未检测到人脸\n" )

                show_frame(frame, self.recognitionpage.recognition_page)

            if cv2.waitKey(25) & self.stopEvent_control.is_set() == True:
                self.stopEvent_control.clear()
                self.recognitionpage.opencam_btn.setEnabled(True)
                self.reset_cam_control()
                break

    def close_cam_control(self):
        self.stopEvent_control.set()
        self.reset_cam_control()

    def reset_cam_control(self):
        self.recognitionpage.opencam_btn.setEnabled(True)
        self.recognitionpage.recognition_page.setPixmap(QPixmap(""))
        self.recognitionpage.recognition_page.setText("Face Det")

    def show_page_0(self):
        self.stack_pages.setCurrentIndex(0)
        self.data_log.clear()

    def show_page_1(self):
        self.stack_pages.setCurrentIndex(1)
        self.data_log.clear()

    def tcp_client_start(self):
        """
        功能函数，TCP客户端连接其他服务端的方法
        :return:
        """
        self.tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            address = (str(self.lineEdit_ip.text()),
                       int(self.lineEdit_port.text()))
        except Exception:
            msg = '请检查目标IP，目标端口\n'
            self.signal_write_msg.emit(msg)
        else:
            try:
                msg = '正在连接目标服务器\n'
                self.signal_write_msg.emit(msg)
                self.tcp_socket.connect(address)
            except Exception:
                msg = '无法连接目标服务器\n'
                self.signal_write_msg.emit(msg)
            else:
                self.client_th = threading.Thread(
                    target=self.tcp_client_concurrency, args=(address,))
                self.client_th.start()
                
                self.send_th = threading.Thread(target=self.tcp_send_name)
                self.send_th.start()
                msg = 'TCP客户端已连接IP:%s端口:%s\n' % address
                self.signal_write_msg.emit(msg)
                self.link = True

    def tcp_client_concurrency(self):
        """
        功能函数，用于TCP客户端创建子线程的方法，阻塞式接收
        :return:
        """
        while True:
            recv_msg = self.tcp_socket.recv(1024)
            if recv_msg:
                msg = recv_msg.decode('utf-8')
                self.signal_data_msg.emit(msg)
            else:
                self.tcp_socket.close()
                self.reset()
                msg = '从服务器断开连接\n'
                self.signal_write_msg.emit(msg)
                break

    def tcp_send(self, send_msg):
        """
        功能函数，用于TCP服务端和TCP客户端发送消息
        :return: None
        """
        if self.link is False:
            msg = '请选择服务，并点击连接网络\n'
            self.signal_write_msg.emit(msg)
        else:
            try:
                send_msg = send_msg.encode('utf-8')
                self.tcp_socket.send(send_msg)
                msg = 'TCP客户端已发送\n'
                self.signal_write_msg.emit(msg)
            except Exception:
                msg = '发送失败\n'
                self.signal_write_msg.emit(msg)

    def tcp_close(self):
        """
        功能函数，关闭网络连接的方法
        :return:
        """
        try:
            self.tcp_socket.close()
            if self.link is True:
                msg = '已断开网络\n'
                self.signal_write_msg.emit(msg)
        except Exception:
            pass
        try:
            stopThreading.stop_thread(self.client_th)
            stopThreading.stop_thread(self.send_th)

        except Exception:
            pass

    def reset(self):
        """
        功能函数，将按钮重置为初始状态
        :return:None
        """
        self.link = False

    def tcp_send_name(self):
        while True:
            if self.link:
                if self.send_name:
                    send_data = self.send_name
                    self.tcp_send("###"+send_data)
                    self.send_name = ""
                    time.sleep(1)

    def closeEvent(self, event):
        reply = QMessageBox.question(
            self, 'quit', "Are you sure?", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.close_cam()
            self.close_cam_control()
            self.close()
            event.accept()
        else:
            event.ignore()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    main_window = FaceMainwindow()
    main_window.show()
    sys.exit(app.exec_())