# 从人脸图像文件中提取人脸特征存入 "features_all.csv" / Extract features from images and save into "features_all.csv"
import os
import dlib
from skimage import io
import numpy as np

# 要读取人脸图像文件的路径 / Path of cropped faces
path_images_from_camera = "data/data_faces_from_camera/"

# Dlib 正向人脸检测器 / Use frontal face detector of Dlib
detector = dlib.get_frontal_face_detector()

# Dlib 人脸 landmark 特征点检测器 / Get face landmarks
predictor = dlib.shape_predictor('data/data_dlib/shape_predictor_68_face_landmarks.dat')

# Dlib Resnet 人脸识别模型，提取 128D 的特征矢量 / Use Dlib resnet50 model to get 128D face descriptor
face_reco_model = dlib.face_recognition_model_v1("data/data_dlib/dlib_face_recognition_resnet_model_v1.dat")

#* 功能：从单张图像中提取128维人脸特征向量
#* 输入：图像文件路径（str字符串类型）
#* 处理流程：
#  - 读取图像
#  - 使用detector检测人脸
#  - 如果检测到人脸：
#    - 使用predictor获取人脸关键点
#    - 使用face_reco_model计算128维特征向量
#  - 如果未检测到人脸：
#    - 返回0
#* 输出：人脸特征向量（dlib.vector类型）或0（未检测到人脸时）
def return_128d_features(path_img):
    img_rd = io.imread(path_img)
    faces = detector(img_rd, 1)

    print("%-40s %-20s" % (" >> 检测到人脸的图像 / Image with faces detected:", path_img), '\n')

    # 因为有可能截下来的人脸再去检测，检测不出来人脸了, 所以要确保是 检测到人脸的人脸图像拿去算特征
    # For photos of faces saved, we need to make sure that we can detect faces from the cropped images
    if len(faces) != 0:
        shape = predictor(img_rd, faces[0])
        face_descriptor = face_reco_model.compute_face_descriptor(img_rd, shape)
    else:
        face_descriptor = 0
        print("no face")
    return face_descriptor

#* 功能：计算某个人多张人脸图像的128维特征均值
#* 输入：包含某人多张人脸图像的文件夹路径
#* 处理流程：
#  - 获取文件夹中所有图像
#  - 对每张图像：
#    - 调用return_128d_features()提取特征
#    - 如果成功提取特征，将特征添加到列表中
#  - 如果成功提取了特征：
#    - 计算所有特征的均值向量
#  - 如果没有提取到任何特征：
#    - 返回128维的零向量
#* 输出：128维特征均值向量（numpy.ndarray类型）
def return_features_mean_personX(path_faces_personX):
    features_list_personX = []
    photos_list = os.listdir(path_faces_personX)
    if photos_list:
        for i in range(len(photos_list)):
            # 调用 return_128d_features() 得到 128D 特征 / Get 128D features for single image of personX
            print("%-40s %-20s" % (" >> 正在读的人脸图像 / Reading image:", path_faces_personX + "/" + photos_list[i]))
            features_128d = return_128d_features(path_faces_personX + "/" + photos_list[i])
            # 遇到没有检测出人脸的图片跳过 / Jump if no face detected from image
            if features_128d == 0:
                i += 1
            else:
                features_list_personX.append(features_128d)
    else:
        print(" >> 文件夹内图像文件为空 / Warning: No images in " + path_faces_personX + '/', '\n')

    # 计算 128D 特征的均值 / Compute the mean
    # personX 的 N 张图像 x 128D -> 1 x 128D
    if features_list_personX:
        features_mean_personX = np.array(features_list_personX).mean(axis=0)
    else:
        features_mean_personX = np.zeros(128, dtype=int, order='C')
    return features_mean_personX
