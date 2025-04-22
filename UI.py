import socket           #网络通信库 TCP
import sys              #系统
import threading        #线程
import time             #时间
import cv2              #OpenCV
import csv              #数据导出
import stopThreading    #停止线程

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from DCUI.connect_moudle import tcp_moudle_ui
from DCUI.face_register import recognition_moudle_ui, register_moudle_ui
from face_reco_from_camera_ot_single_person import Face_Recognizer_single
from features_extraction_to_csv import *

def myframe_resize(frame):
    # 判断图像的宽度是否大于高度
    if frame.shape[1] > frame.shape[0]:
        # 如果宽度大于高度，计算以宽度640像素为基准的缩放比例
        resize_scale = 640 / frame.shape[1]
        # 使用OpenCV的resize函数按比例缩放图像
        frame = cv2.resize(frame, (0, 0), fx=resize_scale, fy=resize_scale)
        # (0, 0)表示自动计算输出图像尺寸，fx和fy是缩放因子
    else:
        resize_scale = 480 / frame.shape[0]
        # 如果高度大于或等于宽度，计算以高度480像素为基准的缩放比例
        frame = cv2.resize(frame, (0, 0), fx=resize_scale, fy=resize_scale)
        # 同样使用等比例缩放
    return frame
    # 返回处理后的图像帧

def show_frame(frame, show_area):
    # 1. 调整帧的大小
    frame = myframe_resize(frame)
    # 2. 将BGR颜色空间转换为RGB
    img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    # 3. 创建QImage对象
    _image = QtGui.QImage(img[:], img.shape[1], img.shape[0], img.shape[1] * 3,
                          QtGui.QImage.Format_RGB888)
    # 4. 转换为QPixmap对象
    jpg_out = QtGui.QPixmap(_image)
    # 5. 在指定区域显示图像
    show_area.setPixmap(jpg_out)

class FaceMainwindow(QMainWindow, tcp_moudle_ui):
    # 定义主窗口类，继承自QMainWindow和tcp_moudle_ui
    def __init__(self):
        # 调用父类的初始化方法
        super(FaceMainwindow, self).__init__()
        # 界面相关属性初始化
        self.stack_pages = None       # 页面堆栈管理器
        self.signal_data_msg = None   # 数据信号消息
        # 设置界面和组件
        self.SetMainUI(self)          # 初始化主界面
        self.setup_component(self)    # 设置界面组件
        # 创建并添加功能页面
        self.registerpage = register_moudle_ui()         # 注册页面实例
        self.recognitionpage = recognition_moudle_ui()   # 识别页面实例
        self.stack_pages.addWidget(self.registerpage)    # 将注册页面添加到堆栈
        self.stack_pages.addWidget(self.recognitionpage) # 将识别页面添加到堆栈
        # 绑定信号槽
        self.SlotFunction_binding()        # 绑定功能函数到界面控件
        # 线程控制相关
        self.stopEvent = threading.Event()          # 停止事件标志
        self.stopEvent.clear()                      # 清除停止标志
        self.stopEvent_control = threading.Event()  # 控制停止事件标志
        self.stopEvent_control.clear()              # 清除控制停止标志
        # 图像处理相关参数
        self.save_flag = 0                # 保存图像标志
        self.font = cv2.FONT_ITALIC       # 设置字体样式
        self.frame_time = 0               # 帧处理时间
        self.frame_start_time = 0         # 帧开始时间
        self.fps = 0                      # 帧率
        self.current_frame_faces_cnt = 0  # 当前帧中检测到的人脸数量
        # 网络通信相关
        self.link = False                 # 连接状态
        self.tcp_socket = None            # TCP套接字对象
        self.sever_th = None              # 服务器线程
        self.client_th = None             # 客户端线程
        self.send_th = None               # 发送数据线程
        self.client_socket_list = list()  # 客户端套接字列表
        self.send_name = ""               # 要发送的名称数据

    def SlotFunction_binding(self):
        # 绑定注册按钮点击事件到显示第0页（注册页面）的函数
        self.register_btn.clicked.connect(self.show_page_0)
        # 绑定识别按钮点击事件到显示第1页（识别页面）的函数
        self.recognition_btn.clicked.connect(self.show_page_1)
        # 绑定连接按钮点击事件到TCP客户端启动函数
        self.connect_btn.clicked.connect(self.tcp_client_start)
        # 绑定信号写入消息的事件到消息写入函数
        self.signal_write_msg.connect(self.write_msg)
        # 注册页面按钮绑定开始
        # 绑定打开摄像头按钮点击事件
        self.registerpage.opencam_btn.clicked.connect(self.open_cam)
        # 绑定关闭摄像头按钮点击事件
        self.registerpage.closecam_btn.clicked.connect(self.close_cam)
        # 绑定创建目录按钮点击事件
        self.registerpage.mkdir_btn.clicked.connect(self.mkdir)
        # 绑定保存图像按钮点击事件
        self.registerpage.save_btn.clicked.connect(self.start_save_image)
        # 绑定保存特征按钮点击事件
        self.registerpage.savefeature_btn.clicked.connect(self.save_features)
        # 识别页面按钮绑定开始
        # 绑定打开摄像头按钮点击事件（用于人脸识别）
        self.recognitionpage.opencam_btn.clicked.connect(self.open_cam_control)
        # 绑定关闭摄像头按钮点击事件（用于人脸识别）
        self.recognitionpage.closecam_btn.clicked.connect(self.close_cam_control)

    def write_msg(self, msg):
        # 将消息添加到数据日志列表中
        # self.data_log: 用于存储日志消息的列表
        # msg: 要添加的消息内容
        self.data_log.append(msg)

    def SetMainUI(self, MainUi):
        # 设置主窗口对象的名称
        MainUi.setObjectName("MainUi")
        # 设置窗口标题为"人脸识别智能柜"
        MainUi.setWindowTitle("人脸识别智能柜")
        # 设置窗口的固定大小为 965x605 像素，禁止调整大小
        MainUi.setFixedSize(965, 605)
        # 创建一个QStackedWidget（堆叠式窗口部件）用于管理多个页面
        self.stack_pages = QtWidgets.QStackedWidget(MainUi)
        # 设置堆叠式窗口部件的位置和大小
        # 参数分别是：左边距320像素，上边距5像素，宽度640像素，高度600像素
        self.stack_pages.setGeometry(QtCore.QRect(320, 5, 640, 600))
        # 创建字体对象
        font = QtGui.QFont()
        # 设置字体为粗体
        font.setBold(True)
        # 设置字体权重为75（粗体）
        font.setWeight(75)
        # 将创建的字体应用到堆叠式窗口部件
        self.stack_pages.setFont(font)
        # 设置堆叠式窗口部件的对象名称
        self.stack_pages.setObjectName("stack_pages")

    def open_cam(self):
        # 禁用注册页面上的打开摄像头按钮，防止重复点击
        self.registerpage.opencam_btn.setDisabled(True)
        # 创建新线程，指定目标函数为self.operate_cam
        th = threading.Thread(target=self.operate_cam)
        # 启动线程，开始执行摄像头操作
        th.start()

    def mkdir(self):
        # 从注册页面的文本输入框获取用户输入的名称
        name = self.registerpage.lineEdit_name.text()
        # 如果用户输入了名称（非空）
        if name:
            # 构造人脸图像存储目录的完整路径
            # 基础路径为 "data/data_faces_from_camera/"，后面拼接用户名
            current_face_dir = "data/data_faces_from_camera/" + name
            # 检查该目录是否已经存在
            if os.path.isdir(current_face_dir):
                # 如果目录已存在，在日志中添加提示信息
                self.data_log.append('已存在该命名的文件夹\n')
            else:
                # 如果目录不存在，创建新目录
                os.mkdir(current_face_dir)
                # 在日志中记录创建成功的信息
                self.data_log.append(
                    f"新建的人脸文件夹 / Create folders: {current_face_dir}")
        else:
            # 如果用户没有输入名称，不执行任何操作
            pass

    def start_save_image(self):
        # 定义一个启动图像保存的方法
        self.save_flag = 1
        # 设置保存标志位为1，表示开启图像保存功能
        # 这个标志位会在图像处理循环中被检查，当值为1时触发保存操作

    def update_fps(self):
        # 获取当前时间戳（以秒为单位）
        now = time.time()
        # 计算从上一帧到当前帧的时间间隔（单位：秒）
        self.frame_time = now - self.frame_start_time
        # 计算每秒的帧数（FPS）：用1秒除以每帧所需时间
        self.fps = 1.0 / self.frame_time
        # 将当前时间设置为下一次计算的起始时间
        self.frame_start_time = now

    def draw_note(self, img_rd):
        # 在图像上绘制"Face Register"文本
        # 参数说明：
        # img_rd: 要绘制的图像
        # (20, 40): 文本位置坐标（左上角）
        # self.font: 字体类型（斜体）
        # 1: 字体大小比例
        # (255, 255, 255): 颜色（白色）
        # 1: 线条粗细
        # cv2.LINE_AA: 抗锯齿类型
        cv2.putText(img_rd, "Face Register", (20, 40), self.font,
                    1, (255, 255, 255), 1, cv2.LINE_AA)
        # 在图像上绘制当前FPS（帧率）信息
        # str(self.fps.__round__(2)): 将FPS数值转换为字符串，保留2位小数
        # (20, 100): 文本位置坐标
        # 0.8: 字体大小比例
        # (0, 255, 0): 颜色（绿色）
        cv2.putText(img_rd, "FPS:   " + str(self.fps.__round__(2)), (20, 100), self.font, 0.8, (0, 255, 0), 1,
                    cv2.LINE_AA)
        # 在图像上绘制当前检测到的人脸数量
        # str(self.current_frame_faces_cnt): 将人脸数量转换为字符串
        # (20, 140): 文本位置坐标
        cv2.putText(img_rd, "Faces: " + str(self.current_frame_faces_cnt),
                    (20, 140), self.font, 0.8, (0, 255, 0), 1, cv2.LINE_AA)

    #A[开始] --> B{是否检测到人脸?}
    #B -->|否| K[更新计数和显示信息]
    #B -->|是| C[计算人脸框尺寸]

    #C --> D{人脸是否超出范围?}
    #D -->|是| E[显示OUT OF RANGE警告]
    #D -->|否| F[设置白色边框]

    #E --> G[设置红色边框]
    #E --> H{是否需要保存?}
    #F --> I[绘制人脸框]
    #G --> I

    #H -->|是| J[记录警告并关闭保存]
    #H -->|否| I

    #I --> L{是否需要保存人脸?}
    #L -->|否| K
    #L -->|是| M{是否输入姓名?}

    #M -->|否| N[显示警告对话框]
    #M -->|是| O[保存人脸图像]

    #N --> P[关闭保存标志]
    #O --> P

    #P --> K
    #K --> Q[更新FPS]
    #Q --> R[返回处理后的帧]
    def face_det(self, faces, frame):
        # 检查是否检测到人脸
        if len(faces) != 0:
            # 遍历每个检测到的人脸
            for k, d in enumerate(faces):
                # 计算人脸框的高度和宽度
                height = (d.bottom() - d.top())
                width = (d.right() - d.left())
                # 计算高度和宽度的一半，用于扩展人脸框
                hh = int(height/2)
                ww = int(width/2)
                # 检查人脸是否超出摄像头范围（640x480）
                if (d.right()+ww) > 640 or (d.bottom()+hh > 480) or (d.left()-ww < 0) or (d.top()-hh < 0):
                    # 如果超出范围，在图像上显示警告文字
                    cv2.putText(frame, "OUT OF RANGE", (20, 300),
                                cv2.FONT_ITALIC, 0.8, (0, 0, 255), 1, cv2.LINE_AA)
                    # 设置人脸框颜色为红色
                    color_rectangle = (0, 0, 255)
                    # 如果需要保存图像，记录警告信息并关闭保存标志
                    if self.save_flag:
                        self.data_log.append("人脸不在检测范围，请调整位置")
                        self.save_flag = 0
                else:
                    # 如果在范围内，设置人脸框颜色为白色
                    color_rectangle = (255, 255, 255)
                # 在图像上绘制人脸框
                cv2.rectangle(frame,
                              tuple([d.left() - ww, d.top() - hh]),
                              tuple([d.right() + ww, d.bottom() + hh]),
                              color_rectangle, 2)
                # 创建空白图像用于保存人脸
                img_blank = np.zeros(
                            (int(height*2), width*2, 3), np.uint8)
                # 如果需要保存人脸图像
                if self.save_flag:
                    # 获取用户输入的姓名
                    name = self.registerpage.lineEdit_name.text()
                    if name:
                        # 构建保存路径
                        current_face_dir = "data/data_faces_from_camera/" + name
                        if os.path.isdir(current_face_dir):
                            # 获取当前文件夹中的图像数量
                            num = len(os.listdir(current_face_dir))
                            # 复制人脸区域到空白图像
                            for ii in range(height*2):
                                for jj in range(width*2):
                                    img_blank[ii][jj] = frame[d.top(
                                    )-hh + ii][d.left()-ww + jj]
                            # 保存人脸图像
                            cv2.imwrite(current_face_dir + "/img_face_" +
                                        str(num + 1) + ".jpg", img_blank)
                            self.data_log.append(f'已存在 {name} 文件夹\n')
                    else:
                        # 如果未输入姓名，显示警告对话框
                        QMessageBox.warning(
                            self, '警告', "先输入姓名检查是否有文件夹！", QMessageBox.Yes | QMessageBox.No,
                            QMessageBox.No)
                        # 关闭保存标志
                    self.save_flag = 0
        # 更新当前帧中检测到的人脸数量
        self.current_frame_faces_cnt = len(faces)
        # 在图像上绘制注释信息（FPS等）
        self.draw_note(frame)
        # 更新FPS计数
        self.update_fps()
        # 返回处理后的帧
        return frame

    def save_features(self):
        # 清空数据日志列表，为新的记录做准备
        self.data_log.clear()
        # 获取存储人脸图像的目录中所有人员的文件夹列表
        person_list = os.listdir("data/data_faces_from_camera/")
        # 以写入模式打开CSV文件，用于保存特征数据
        # newline=""参数确保在Windows系统下不会出现多余的空行
        with open("data/features_all.csv", "w", newline="") as csvfile:
            # 创建CSV写入器对象
            writer = csv.writer(csvfile)
            # 遍历每个人的文件夹
            for person in person_list:
                # 计算当前人的人脸特征均值
                # path_images_from_camera + person 构成完整的图像文件夹路径
                features_mean_personX = return_features_mean_personX(
                    path_images_from_camera + person)
                # 将特征均值写入CSV文件
                writer.writerow(features_mean_personX)
                # 在数据日志中添加特征均值信息
                self.data_log.append(
                    f" >> 特征均值 / The mean of features:{list(features_mean_personX)}'\n'")
            # 在数据日志中添加保存完成的信息
            self.data_log.append(
                "所有录入人脸数据存入 / Save all the features of faces registered into: data/features_all.csv")

    def operate_cam(self):
        # 初始化视频捕获对象，参数0表示使用默认摄像头，cv2.CAP_DSHOW是DirectShow驱动
        cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        # 检查摄像头是否成功打开，如果没有打开则抛出异常
        if not cap.isOpened():
            raise ValueError("Video open failed.")
        # 读取第一帧图像，ret为布尔值（是否读取成功），frame为图像数据
        ret, frame = cap.read()
        # 当成功读取图像时，进入循环
        while ret:
            # 持续读取新的一帧
            ret, frame = cap.read()
            # 如果成功读取到图像
            if ret:
                # 水平翻转图像（镜像效果）
                frame = cv2.flip(frame, 1)
                # 使用人脸检测器检测图像中的人脸
                faces = detector(frame, 0)
                # 对检测到的人脸进行处理（绘制标记、保存等操作）
                frame = self.face_det(faces, frame)
                # 在GUI界面上显示处理后的图像
                show_frame(frame, self.registerpage.register_page)
            # 检查是否需要停止摄像头
            if cv2.waitKey(25) & self.stopEvent.is_set() == True:
                # 清除停止事件标志
                self.stopEvent.clear()
                # 重新启用打开摄像头按钮
                self.registerpage.opencam_btn.setEnabled(True)
                # 重置摄像头状态
                self.reset_cam()
                # 退出循环
                break

    def close_cam(self):
        # 设置停止事件标志，通知相关线程需要停止运行
        self.stopEvent.set()
        # 调用重置摄像头方法，清理和重置摄像头相关的状态
        self.reset_cam()

    def reset_cam(self):
        # 重新启用注册页面上的打开摄像头按钮
        # setEnabled(True) 使按钮变为可点击状态
        self.registerpage.opencam_btn.setEnabled(True)
        # 清空摄像头显示区域的图像
        # 通过设置空的QPixmap对象来清除之前显示的图像内容
        self.registerpage.register_page.setPixmap(QPixmap(""))
        # 在显示区域设置默认提示文本"Cam Here"
        # 这个文本用来指示这里是摄像头画面的显示位置
        self.registerpage.register_page.setText("Cam Here")

    def open_cam_control(self):
        # 禁用识别页面上的打开摄像头按钮，防止重复点击
        self.recognitionpage.opencam_btn.setDisabled(True)
        # 创建新线程来运行摄像头控制
        # target=self.control_cam 指定线程要执行的函数
        th = threading.Thread(target=self.control_cam)
        # 启动线程，开始执行摄像头控制
        th.start()

    def control_cam(self):
        # 创建人脸识别器实例
        model = Face_Recognizer_single()
        # 初始化摄像头捕获对象，使用DirectShow后端
        cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        # 检查摄像头是否成功打开
        if not cap.isOpened():
            raise ValueError("Video open failed.")
        # 读取第一帧图像
        ret, frame = cap.read()
        # 主循环：当成功读取图像时继续
        while ret:
            # 读取新的一帧
            ret, frame = cap.read()
            # 如果成功读取到图像
            if ret:
                # 水平翻转图像（镜像效果）
                frame = cv2.flip(frame, 1)
                # 使用人脸识别模型处理图像，返回处理后的图像和识别到的人名列表
                frame,name_list = model.process(frame)
                # 如果识别到人名
                if name_list:
                    # 将检测结果添加到日志
                    self.data_log.append(f"检测结果:{name_list[0]}\n" )
                    # 保存识别到的人名，用于后续发送
                    self.send_name = name_list[0]
                else:
                    # 如果没有识别到人脸，清空发送名称
                    self.send_name = ""
                    # 在日志中记录未检测到人脸
                    self.data_log.append("未检测到人脸\n" )
                # 在GUI界面上显示处理后的图像
                show_frame(frame, self.recognitionpage.recognition_page)
            # 检查是否需要停止摄像头（等待25ms并检查停止事件）
            if cv2.waitKey(25) & self.stopEvent_control.is_set() == True:
                # 清除停止事件标志
                self.stopEvent_control.clear()
                # 重新启用打开摄像头按钮
                self.recognitionpage.opencam_btn.setEnabled(True)
                # 重置摄像头状态
                self.reset_cam_control()
                # 退出循环
                break

    def close_cam_control(self):
        # 设置停止事件标志，通知相关线程需要停止运行
        self.stopEvent_control.set()
        # 调用重置方法，用于清理和重置摄像头相关的状态
        self.reset_cam_control()

    def reset_cam_control(self):
        # 重新启用识别页面上的打开摄像头按钮
        self.recognitionpage.opencam_btn.setEnabled(True)
        # 清除识别页面上的图像显示
        # 通过设置空的 QPixmap 来清空之前显示的图像
        self.recognitionpage.recognition_page.setPixmap(QPixmap(""))
        # 设置识别页面的默认文本提示为 "Face Det"
        # 表明这是人脸检测的显示区域
        self.recognitionpage.recognition_page.setText("Face Det")

    def show_page_0(self):
        # 将堆叠式页面控件切换到索引为0的页面（即注册页面）
        self.stack_pages.setCurrentIndex(0)
        # 清空数据日志显示区域中的所有内容
        self.data_log.clear()

    def show_page_1(self):
        # 切换到堆栈式窗口部件(QStackedWidget)的第二个页面
        # setCurrentIndex(1)表示切换到索引为1的页面（注意：索引从0开始）
        self.stack_pages.setCurrentIndex(1)
        # 清空数据日志显示区域的所有内容
        # data_log可能是一个QTextEdit或QListWidget等用于显示日志的组件
        self.data_log.clear()

    def tcp_client_start(self):
        # 创建一个新的TCP套接字对象
        self.tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            # 尝试获取用户输入的IP地址和端口号
            # lineEdit_ip.text()获取IP输入框的内容并转换为字符串
            # lineEdit_port.text()获取端口输入框的内容并转换为整数
            address = (str(self.lineEdit_ip.text()),
                       int(self.lineEdit_port.text()))
        except Exception:
            # 如果IP或端口格式错误，发送错误消息
            msg = '请检查目标IP，目标端口\n'
            self.signal_write_msg.emit(msg)
        else:
            try:
                # 发送正在连接的消息
                msg = '正在连接目标服务器\n'
                self.signal_write_msg.emit(msg)
                # 尝试建立TCP连接
                self.tcp_socket.connect(address)
            except Exception:
                # 如果连接失败，发送错误消息
                msg = '无法连接目标服务器\n'
                self.signal_write_msg.emit(msg)
            else:
                # 连接成功后创建并启动客户端并发处理线程
                self.client_th = threading.Thread(
                    target=self.tcp_client_concurrency, args=(address,))
                self.client_th.start()
                # 创建并启动名称发送线程
                self.send_th = threading.Thread(target=self.tcp_send_name)
                self.send_th.start()
                # 发送连接成功的消息，包含IP和端口信息
                msg = 'TCP客户端已连接IP:%s端口:%s\n' % address
                self.signal_write_msg.emit(msg)
                # 设置连接状态为True
                self.link = True

    def tcp_client_concurrency(self):
        # 创建一个无限循环，持续监听服务器消息
        while True:
            # 从TCP套接字接收最大1024字节的数据
            recv_msg = self.tcp_socket.recv(1024)
            # 如果接收到数据
            if recv_msg:
                # 将接收到的字节数据解码为UTF-8格式的字符串
                msg = recv_msg.decode('utf-8')
                # 通过信号机制发送接收到的消息
                self.signal_data_msg.emit(msg)
            # 如果没有接收到数据（连接断开）
            else:
                # 关闭TCP套接字连接
                self.tcp_socket.close()
                # 重置连接状态
                self.reset()
                # 准备断开连接的提示消息
                msg = '从服务器断开连接\n'
                # 通过信号机制发送断开连接的提示消息
                self.signal_write_msg.emit(msg)
                # 跳出循环，结束并发处理
                break

    def tcp_send(self, send_msg):
        # 检查网络连接状态
        if self.link is False:
            # 如果未连接，准备提示消息
            msg = '请选择服务，并点击连接网络\n'
            # 通过信号机制发送提示消息到界面
            self.signal_write_msg.emit(msg)
        else:
            # 如果已连接，尝试发送数据
            try:
                # 将消息编码为UTF-8格式的字节流
                send_msg = send_msg.encode('utf-8')
                # 通过TCP套接字发送数据
                self.tcp_socket.send(send_msg)
                # 准备发送成功的提示消息
                msg = 'TCP客户端已发送\n'
                # 通过信号机制发送成功提示到界面
                self.signal_write_msg.emit(msg)
            except Exception:
                # 如果发送过程出现异常
                # 准备发送失败的提示消息
                msg = '发送失败\n'
                # 通过信号机制发送失败提示到界面
                self.signal_write_msg.emit(msg)

    def tcp_close(self):
        # 第一个 try-except 块：尝试关闭 TCP 连接
        try:
            # 关闭 TCP socket 连接
            self.tcp_socket.close()
            # 如果当前处于连接状态
            if self.link is True:
                # 准备断开连接的提示消息
                msg = '已断开网络\n'
                # 通过信号机制发送断开连接的消息到界面
                self.signal_write_msg.emit(msg)
        except Exception:
            # 如果关闭过程出现异常，直接忽略
            pass
        # 第二个 try-except 块：尝试停止相关线程
        try:
            # 停止客户端线程
            stopThreading.stop_thread(self.client_th)
            # 停止发送线程
            stopThreading.stop_thread(self.send_th)
        except Exception:
            # 如果停止线程过程出现异常，直接忽略
            pass

    # 定义一个重置方法，用于重置网络连接状态
    # 参数 self 表示这是一个实例方法，可以访问类的属性
    def reset(self):
        # 将网络连接状态标志 link 设置为 False，表示连接已断开
        self.link = False

    def tcp_send_name(self):
        # 创建一个无限循环，持续检查和发送名称数据
        while True:
            # 检查是否存在网络连接
            if self.link:
                # 检查是否有需要发送的名称数据
                if self.send_name:
                    # 将要发送的数据保存到临时变量
                    send_data = self.send_name
                    # 发送数据，在数据前添加"###"作为特殊标记
                    self.tcp_send("###"+send_data)
                    # 清空发送名称变量，防止重复发送
                    self.send_name = ""
                    # 暂停1秒，控制发送频率
                    time.sleep(1)

    # 当用户尝试关闭窗口时自动触发此方法
    # self: 当前窗口实例
    # event: 关闭事件对象
    def closeEvent(self, event):
        # 显示确认对话框
        reply = QMessageBox.question(
            self, 'quit', "Are you sure?", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        # 如果用户点击"是"
        if reply == QMessageBox.Yes:
            self.close_cam()
            self.close_cam_control()
            self.close()
            event.accept()
        else:
            event.ignore()

# 程序入口点代码，确保这段代码只在直接运行该文件时执行，而不是在被导入时执行
if __name__ == "__main__":
    # 创建 QApplication 实例，这是任何 PyQt5 应用程序的基础
    # sys.argv 包含命令行参数
    app = QApplication(sys.argv)
    # 创建主窗口实例
    # FaceMainwindow 是一个自定义的窗口类，包含了人脸识别相关的功能
    main_window = FaceMainwindow()
    # 显示主窗口
    # 如果不调用 show() 方法，窗口将不会显示在屏幕上
    main_window.show()
    # 启动应用程序的事件循环并等待程序退出
    # app.exec_() 开始事件循环，处理用户的交互操作
    # sys.exit() 确保程序在退出时能够正确清理资源
    sys.exit(app.exec_())