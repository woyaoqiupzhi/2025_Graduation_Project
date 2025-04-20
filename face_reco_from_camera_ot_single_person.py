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
        if os.path.exists("data/features_all.csv"):
            path_features_known_csv = "data/features_all.csv"
            csv_rd = pd.read_csv(path_features_known_csv, header=None)
            for i in range(csv_rd.shape[0]):
                features_someone_arr = []
                for j in range(0, 128):
                    if csv_rd.iloc[i][j] == '':
                        features_someone_arr.append('0')
                    else:
                        features_someone_arr.append(csv_rd.iloc[i][j])
                self.features_known_list.append(features_someone_arr)
                self.name_known_list.append("Person_" + str(i + 1))
            return 1
        else:
            return 0

    # 更新 FPS / Update FPS of video stream
    def update_fps(self):
        now = time.time()
        self.frame_time = now - self.frame_start_time
        self.fps = 1.0 / self.frame_time
        self.frame_start_time = now

    # 计算两个128D向量间的欧式距离 / Compute the e-distance between two 128D features
    @staticmethod
    def return_euclidean_distance(feature_1, feature_2):
        feature_1 = np.array(feature_1)
        feature_2 = np.array(feature_2)
        dist = np.sqrt(np.sum(np.square(feature_1 - feature_2)))
        return dist

    # 生成的 cv2 window 上面添加说明文字 / putText on cv2 window
    def draw_note(self, img_rd):
        # 添加说明 (Add some statements
        cv2.putText(img_rd, "Face Recognizer with OT (one person)", (20, 40), self.font, 1, (255, 255, 255), 1, cv2.LINE_AA)
        cv2.putText(img_rd, "FPS:   " + str(self.fps.__round__(2)), (20, 100), self.font, 0.8, (0, 255, 0), 1,
                    cv2.LINE_AA)
        cv2.putText(img_rd, "Q: Quit", (20, 450), self.font, 0.8, (255, 255, 255), 1, cv2.LINE_AA)

    def draw_name(self, img_rd):
        # 在人脸框下面写人脸名字 / Write names under ROI
        font = ImageFont.truetype("simsun.ttc", 30)
        img = Image.fromarray(cv2.cvtColor(img_rd, cv2.COLOR_BGR2RGB))
        draw = ImageDraw.Draw(img)
        draw.text(xy=self.current_frame_face_position_list[0], text=self.current_frame_name_list[0], font=font)
        img_rd = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
        return img_rd

    def send_name_to_mcu(self):
        f = open("name.txt","w")
        f.write(self.current_frame_name_list[0])
        f.close()

    def starting(self):
        task1 = threading.Thread(target = self.send_name_to_mcu)
        task1.start() 

    def show_chinese_name(self):
        if self.current_frame_face_cnt >= 1:
            self.name_known_list = os.listdir("data/data_faces_from_camera/")

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
                if "unknown" in self.current_frame_name_list:
                    self.reclassify_interval_cnt += 1

                # 4.1.1 当前帧一张人脸 / One face in this frame
                if self.current_frame_face_cnt ==1:
                    if self.reclassify_interval_cnt==self.reclassify_interval:

                        self.reclassify_interval_cnt=0
                        self.current_frame_face_feature_list = []
                        self.current_frame_face_X_e_distance_list = []
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

                            cv2.rectangle(img_rd,
                                            tuple([d.left() - ww, d.top() - hh]),
                                            tuple([d.right() + ww, d.bottom() + hh]),
                                            (255, 255, 255), 2)

                            self.current_frame_face_position_list[k] = tuple(
                                [faces[k].left(), int(faces[k].bottom() + (faces[k].bottom() - faces[k].top()) / 4)])

                            img_rd = self.draw_name(img_rd)
                            self.send_name_to_mcu()

            # 4.2 当前帧和上一帧相比发生人脸数变化 / If face cnt changes, 1->0 or 0->1
            else:
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
