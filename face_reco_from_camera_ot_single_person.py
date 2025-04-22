# 利用 OT 对于单张人脸追踪, 实时人脸识别 (Real-time face detection and recognition via Object-tracking for single face)
import dlib
import numpy as np
import cv2
import os
import pandas as pd
import time
from PIL import Image, ImageDraw, ImageFont
import threading

# Dlib 正向人脸检测器 / Use frontal face detector of Dlib
detector = dlib.get_frontal_face_detector()

# Dlib 人脸 landmark 特征点检测器 / Get face landmarks
predictor = dlib.shape_predictor('data/data_dlib/shape_predictor_68_face_landmarks.dat')

# Dlib Resnet 人脸识别模型，提取 128D 的特征矢量 / Use Dlib resnet50 model to get 128D face descriptor
face_reco_model = dlib.face_recognition_model_v1("data/data_dlib/dlib_face_recognition_resnet_model_v1.dat")

class Face_Recognizer_single:
    def __init__(self):
        self.font = cv2.FONT_ITALIC

        # 统计 FPS / For FPS
        self.frame_time = 0
        self.frame_start_time = 0
        self.fps = 0

        # 统计帧数 / cnt for frame
        self.frame_cnt = 0

        # 用来存储所有录入人脸特征的数组 / Save the features of faces in the database
        self.features_known_list = []
        # 用来存储录入人脸名字 / Save the name of faces in the database
        self.name_known_list = []

        # 用来存储上一帧和当前帧 ROI 的质心坐标 / List to save centroid positions of ROI in frame N-1 and N
        self.last_frame_centroid_list = []
        self.current_frame_centroid_list = []

        # 用来存储当前帧检测出目标的名字 / List to save names of objects in current frame
        self.current_frame_name_list = []

        # 上一帧和当前帧中人脸数的计数器 / cnt for faces in frame N-1 and N
        self.last_frame_faces_cnt = 0
        self.current_frame_face_cnt = 0

        # 用来存放进行识别时候对比的欧氏距离 / Save the e-distance for faceX when recognizing
        self.current_frame_face_X_e_distance_list = []

        # 存储当前摄像头中捕获到的所有人脸的坐标名字 / Save the positions and names of current faces captured
        self.current_frame_face_position_list = []
        # 存储当前摄像头中捕获到的人脸特征 / Save the features of people in current frame
        self.current_frame_face_feature_list = []

        # 控制再识别的后续帧数 / Reclassify after 'reclassify_interval' frames
        # 如果识别出 "unknown" 的脸, 将在 reclassify_interval_cnt 计数到 reclassify_interval 后, 对于人脸进行重新识别
        self.reclassify_interval_cnt = 0
        self.reclassify_interval = 10

    # 从 "features_all.csv" 读取录入人脸特征 / Get known faces from "features_all.csv"
    def get_face_database(self):
        # 检查特征数据文件是否存在
        if os.path.exists("data/features_all.csv"):
            # 设置特征数据文件的路径
            path_features_known_csv = "data/features_all.csv"
            # 使用pandas读取CSV文件，不使用表头
            csv_rd = pd.read_csv(path_features_known_csv, header=None)
            # 遍历CSV文件的每一行（每个人脸特征）
            for i in range(csv_rd.shape[0]):
                # 创建临时数组存储单个人脸的特征
                features_someone_arr = []
                # 遍历128个特征值
                for j in range(0, 128):
                    # 如果特征值为空
                    if csv_rd.iloc[i][j] == '':
                        # 用'0'填充空值
                        features_someone_arr.append('0')
                    else:
                        # 添加原始特征值
                        features_someone_arr.append(csv_rd.iloc[i][j])
                # 将处理好的特征数组添加到已知特征列表中
                self.features_known_list.append(features_someone_arr)
                # 为该特征添加对应的人名（格式：Person_序号）
                self.name_known_list.append("Person_" + str(i + 1))
            # 成功读取返回1
            return 1
        else:
            # 文件不存在返回0
            return 0

    # 更新 FPS / Update FPS of video stream
    def update_fps(self):
        # 获取当前时间戳
        now = time.time()
        # 计算当前帧与上一帧之间的时间差（单位：秒）
        # self.frame_start_time 存储了上一帧的时间戳
        self.frame_time = now - self.frame_start_time
        # 计算FPS，用1秒除以帧间时间
        # 例如：如果帧间隔是0.033秒，则 FPS = 1/0.033 ≈ 30
        self.fps = 1.0 / self.frame_time
        # 更新frame_start_time为当前时间戳，为下一次计算做准备
        self.frame_start_time = now

    # 计算两个128D向量间的欧式距离 / Compute the e-distance between two 128D features
    @staticmethod # 静态方法装饰器，表示这个方法不需要实例化就可以调用
    def return_euclidean_distance(feature_1, feature_2):
        # 将输入的特征向量转换为numpy数组格式
        feature_1 = np.array(feature_1)
        feature_2 = np.array(feature_2)
        # 计算两个特征向量之间的欧氏距离：
        # 1. feature_1 - feature_2 计算两个向量的差
        # 2. np.square() 计算差值的平方
        # 3. np.sum() 计算所有平方值的和
        # 4. np.sqrt() 对和求平方根
        dist = np.sqrt(np.sum(np.square(feature_1 - feature_2)))
        # 返回计算得到的欧氏距离
        return dist

    # 生成的 cv2 window 上面添加说明文字 / putText on cv2 window
    def draw_note(self, img_rd):
        # 在图像上添加文字说明信息
        # 添加标题文字
        # 参数说明：
        # img_rd: 要添加文字的图像
        # "Face Recognizer with OT (one person)": 显示的文字内容
        # (20, 40): 文字左下角坐标
        # self.font: 字体类型（斜体）
        # 1: 字体大小
        # (255, 255, 255): 字体颜色（白色）
        # 1: 字体粗细
        # cv2.LINE_AA: 抗锯齿类型
        cv2.putText(img_rd, "Face Recognizer with OT (one person)", (20, 40), self.font, 1, (255, 255, 255), 1, cv2.LINE_AA)
        # 添加FPS信息
        # str(self.fps.__round__(2)): 将FPS数值转换为字符串并保留2位小数
        # (0, 255, 0): 字体颜色（绿色）
        # 0.8: 字体大小比标题小
        cv2.putText(img_rd, "FPS:   " + str(self.fps.__round__(2)), (20, 100), self.font, 0.8, (0, 255, 0), 1,
                    cv2.LINE_AA)
        # 添加退出提示信息
        # "Q: Quit": 提示用户按Q键退出程序
        # (20, 450): 文字位置在窗口下方
        cv2.putText(img_rd, "Q: Quit", (20, 450), self.font, 0.8, (255, 255, 255), 1, cv2.LINE_AA)

    def draw_name(self, img_rd):
        # 用于在人脸框下方绘制识别出的人名
        # 创建一个支持中文的字体对象
        # simsun.ttc是宋体字体文件，大小设置为30像素
        font = ImageFont.truetype("simsun.ttc", 30)
        # 将OpenCV格式的图像(BGR)转换为PIL格式的图像(RGB)
        # cv2.cvtColor进行颜色空间转换
        # Image.fromarray将numpy数组转换为PIL图像对象
        img = Image.fromarray(cv2.cvtColor(img_rd, cv2.COLOR_BGR2RGB))
        # 创建一个可以在图像上绘制的对象
        draw = ImageDraw.Draw(img)
        # 在指定位置绘制文字
        # xy参数：文字的位置坐标，从self.current_frame_face_position_list[0]获取
        # text参数：要绘制的文字内容，从self.current_frame_name_list[0]获取
        # font参数：使用上面创建的字体对象
        draw.text(xy=self.current_frame_face_position_list[0], text=self.current_frame_name_list[0], font=font)
        # 将PIL图像转回OpenCV格式
        # 先将PIL图像转为numpy数组
        # 然后将RGB颜色空间转换回BGR
        img_rd = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
        # 返回处理后的图像
        return img_rd

    def send_name_to_mcu(self):
        # 打开name.txt文件，使用写入模式('w')
        f = open("name.txt","w")
        # 将当前帧中识别到的第一个人名写入文件
        f.write(self.current_frame_name_list[0])
        # 关闭文件
        f.close()

    def starting(self):
        # 创建一个新线程，目标函数为send_name_to_mcu方法
        task1 = threading.Thread(target = self.send_name_to_mcu)
        # 启动线程
        task1.start() 

    def show_chinese_name(self):
        # 检查当前帧是否至少检测到一个人脸
        if self.current_frame_face_cnt >= 1:
            # 从指定目录读取所有已知人名（中文名字）
            self.name_known_list = os.listdir("data/data_faces_from_camera/")

    #A[开始处理视频帧] --> B{读取人脸数据库}
    #B -->|成功| C[检测当前帧人脸]
    #B -->|失败| K[返回原始图像]

    #C --> D{比较前后帧人脸数量}

    #D -->|数量相同| E{是否只有一张人脸}
    #D -->|数量改变| F[清空人脸数据列表]

    #E -->|是| G{是否需要重新分类}
    #E -->|否| K

    #G -->|是| H[提取人脸特征]
    #G -->|否| I[更新人脸框位置]

    #H --> J[计算欧氏距离]
    #J --> L{距离<0.4?}

    #L -->|是| M[更新为已知人名]
    #L -->|否| N[标记为unknown]

    #F --> O{0->1人脸?}
    #O -->|是| H
    #O -->|否| P[清空name.txt]

    #I --> Q[绘制人脸框]
    #M --> Q
    #N --> Q
    #P --> Q

    #Q --> R[更新显示信息]
    #R --> S[返回处理后图像]
    # 处理获取的视频流，进行人脸识别 / Face detection and recognition wit OT from input video stream
    def process(self, img_rd):
        # 1. 读取存放所有人脸特征的 csv / Get faces known from "features.all.csv"
        if self.get_face_database():
            # 2. 检测人脸 / Detect faces for frame X
            faces = detector(img_rd, 0)

            # 3. 更新帧中的人脸数 / Update cnt for faces in frames
            self.last_frame_faces_cnt = self.current_frame_face_cnt
            self.current_frame_face_cnt = len(faces)

            # 4.1 当前帧和上一帧相比没有发生人脸数变化 / If cnt not changes, 1->1 or 0->0
            if self.current_frame_face_cnt == self.last_frame_faces_cnt:
                # 如果存在未识别的人脸，增加重分类计数器
                if "unknown" in self.current_frame_name_list:
                    self.reclassify_interval_cnt += 1

                # 4.1.1 当前帧一张人脸 / One face in this frame
                if self.current_frame_face_cnt ==1:
                    # 判断是否需要重新分类（达到重分类间隔）
                    if self.reclassify_interval_cnt==self.reclassify_interval:
                        # 重置计数器和清空相关列表
                        self.reclassify_interval_cnt=0
                        self.current_frame_face_feature_list = []
                        self.current_frame_face_X_e_distance_list = []
                        self.current_frame_name_list = []

                        # 提取当前帧中人脸的特征
                        for i in range(len(faces)):
                            shape = predictor(img_rd, faces[i])
                            self.current_frame_face_feature_list.append(
                                face_reco_model.compute_face_descriptor(img_rd, shape))

                        # a. 遍历捕获到的图像中所有的人脸 / Traversal all the faces in the database
                        for k in range(len(faces)):
                            # 初始化为unknown
                            self.current_frame_name_list.append("unknown")

                            # b. 每个捕获人脸的名字坐标 / Positions of faces captured
                            self.current_frame_face_position_list.append(tuple(
                                [faces[k].left(),
                                    int(faces[k].bottom() + (faces[k].bottom() - faces[k].top()) / 4)]))

                            # c. 对于某张人脸，遍历所有存储的人脸特征 / For every face detected, compare it with all the faces in the database
                            for i in range(len(self.features_known_list)):
                                # 如果 person_X 数据不为空 / If the data of person_X is not empty
                                if str(self.features_known_list[i][0]) != '0.0':
                                    e_distance_tmp = self.return_euclidean_distance(
                                        self.current_frame_face_feature_list[k],
                                        self.features_known_list[i])
                                    self.current_frame_face_X_e_distance_list.append(e_distance_tmp)
                                else:
                                    # 空数据 person_X / For empty data
                                    self.current_frame_face_X_e_distance_list.append(999999999)

                            # d. 寻找出最小的欧式距离匹配 / Find the one with minimum e distance
                            similar_person_num = self.current_frame_face_X_e_distance_list.index(
                                min(self.current_frame_face_X_e_distance_list))

                            if min(self.current_frame_face_X_e_distance_list) < 0.4:
                                # 在这里更改显示的人名 / Modify name if needed
                                self.show_chinese_name()
                                self.current_frame_name_list[k] = self.name_known_list[similar_person_num]
                            else:
                                pass

                    else:
                        # 获取特征框坐标 / Get ROI positions
                        for k, d in enumerate(faces):
                            # 计算矩形框大小 / Compute the shape of ROI
                            height = (d.bottom() - d.top())
                            width = (d.right() - d.left())
                            hh = int(height / 2)
                            ww = int(width / 2)
                            # 绘制人脸框
                            cv2.rectangle(img_rd,
                                            tuple([d.left() - ww, d.top() - hh]),
                                            tuple([d.right() + ww, d.bottom() + hh]),
                                            (255, 255, 255), 2)
                            # 更新人名显示位置
                            self.current_frame_face_position_list[k] = tuple(
                                [faces[k].left(), int(faces[k].bottom() + (faces[k].bottom() - faces[k].top()) / 4)])
                            # 绘制人名并发送到MCU
                            img_rd = self.draw_name(img_rd)
                            self.send_name_to_mcu()

            # 4.2 当前帧和上一帧相比发生人脸数变化 / If face cnt changes, 1->0 or 0->1
            else:
                # 清空所有相关列表
                self.current_frame_face_position_list = []
                self.current_frame_face_X_e_distance_list = []
                self.current_frame_face_feature_list = []

                # 4.2.1 人脸数从 0->1 / Face cnt 0->1
                if self.current_frame_face_cnt == 1:

                    self.current_frame_name_list = []

                    for i in range(len(faces)):
                        shape = predictor(img_rd, faces[i])
                        self.current_frame_face_feature_list.append(
                            face_reco_model.compute_face_descriptor(img_rd, shape))

                    # a. 遍历捕获到的图像中所有的人脸 / Traversal all the faces in the database
                    for k in range(len(faces)):
                        self.current_frame_name_list.append("unknown")

                        # b. 每个捕获人脸的名字坐标 / Positions of faces captured
                        self.current_frame_face_position_list.append(tuple(
                            [faces[k].left(), int(faces[k].bottom() + (faces[k].bottom() - faces[k].top()) / 4)]))

                        # c. 对于某张人脸，遍历所有存储的人脸特征 / For every face detected, compare it with all the faces in database
                        for i in range(len(self.features_known_list)):
                            # 如果 person_X 数据不为空 / If data of person_X is not empty
                            if str(self.features_known_list[i][0]) != '0.0':
                                e_distance_tmp = self.return_euclidean_distance(
                                    self.current_frame_face_feature_list[k],
                                    self.features_known_list[i])
                                self.current_frame_face_X_e_distance_list.append(e_distance_tmp)
                            else:
                                # 空数据 person_X / Empty data for person_X
                                self.current_frame_face_X_e_distance_list.append(999999999)

                        # d. 寻找出最小的欧式距离匹配 / Find the one with minimum e distance
                        similar_person_num = self.current_frame_face_X_e_distance_list.index(min(self.current_frame_face_X_e_distance_list))

                        if min(self.current_frame_face_X_e_distance_list) < 0.4:
                            # 在这里更改显示的人名 / Modify name if needed
                            self.show_chinese_name()
                            self.current_frame_name_list[k] = self.name_known_list[similar_person_num]
                        else:
                            pass

                    if "unknown" in self.current_frame_name_list:
                        self.reclassify_interval_cnt+=1

                # 4.2.1 人脸数从 1->0 / Face cnt 1->0
                elif self.current_frame_face_cnt == 0:
                    file = open("name.txt", 'w').close()
                    self.reclassify_interval_cnt=0
                    self.current_frame_name_list = []
                    self.current_frame_face_feature_list = []

            # 5. 生成的窗口添加说明文字 / Add note on cv2 window
            self.draw_note(img_rd)
            self.update_fps()

        return img_rd,self.current_frame_name_list
