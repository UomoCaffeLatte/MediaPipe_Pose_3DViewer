import mediapipe as mp
import numpy as np
import customWidgets as cw
from PySide6 import QtWidgets
import sys

mp_drawing = mp.solutions.drawing_utils
mp_drawing_styles = mp.solutions.drawing_styles
mp_pose = mp.solutions.pose


class MediaPipePoseDetector(QtWidgets.QWidget):

    def __init__(self) -> None:
        super().__init__()
        self.mediaPose_jointHierarchy = {
            24:[12,23,26],
            26:[28],
            28:[32,30],
            32:[30],
            23:[11,25],
            25:[27],
            27:[29,31],
            31:[29],
            12:[14,11],
            14:[16],
            16:[22,20,18],
            20:[18],
            11:[13],
            13:[15],
            15:[21,19,17],
            19:[17]
        }
        # convert joint dict to names
        converted_mediaposeHierarchy = {}
        for key ,value in self.mediaPose_jointHierarchy.items():
            value = [mp_pose.PoseLandmark(item).name for item in value]
            key = mp_pose.PoseLandmark(key).name
            converted_mediaposeHierarchy[key] = value
        self.mediaPose_jointHierarchy = converted_mediaposeHierarchy
        # create widgets
        self.cameraViewerWidget = cw.CameraViewerWidget()
        self.skeletonViewerWidget = cw.SkeletonViewerWidget("Media Pose Skeleton", jointHierarchy=self.mediaPose_jointHierarchy)
        # link signals
        self.cameraViewerWidget.ImageSignal.connect(self.CalculatePose)
        # create layout
        self.layout = QtWidgets.QHBoxLayout(self)
        self.layout.addWidget(self.cameraViewerWidget)
        self.layout.addWidget(self.skeletonViewerWidget)

    def CalculatePose(self, frame):
        pose = mp_pose.Pose(min_detection_confidence=0.5, min_tracking_confidence=0.5)
        # To improve performance, optionally mark the image as not writeable to pass by ref
        frame.flags.writeable = False
        # find pose
        results = pose.process(frame)
        #print(results.pose_landmarks.landmark[mp_pose.PoseLandmark.LEFT_SHOULDER].x)
        # refactor pose in format { "JointName":[x,y,z]}
        jointData = {}
        for joint in mp_pose.PoseLandmark:
            joint = joint.name
            # retrieve data
            if results.pose_world_landmarks.landmark[mp_pose.PoseLandmark[joint]].visibility > 0.7:
                pos = [results.pose_world_landmarks.landmark[mp_pose.PoseLandmark[joint]].x,
                    results.pose_world_landmarks.landmark[mp_pose.PoseLandmark[joint]].y*-1,
                    results.pose_world_landmarks.landmark[mp_pose.PoseLandmark[joint]].z]
                jointData[joint] = np.array(pos)*2
        #jointData = self.CenterSkeleton(jointData)
        # draw the pose annotation on the image:
        frame.flags.writeable = True
        mp_drawing.draw_landmarks(frame, results.pose_landmarks, mp_pose.POSE_CONNECTIONS, landmark_drawing_spec=mp_drawing_styles.get_default_pose_landmarks_style())
        self.cameraViewerWidget.DisplayImage(frame)
        # draw pose as 3D skeleton
        self.skeletonViewerWidget.gLWidget.Draw(jointData)

    def CenterSkeleton(self, frame:dict, centerJoint:str="LEFT_HIP") -> dict:
        # center skeleton position based on target joint
        temp = {}
        # find center joint pos vector
        origin = np.array(frame[centerJoint])
        # loop through all joint and standardise pos to new origin
        for joint, value in frame.items():
            if joint == "root": continue
            childPos = np.array(value)
            print(childPos)
            temp[joint] = childPos - origin
            print(childPos - origin)
        # convert frames to tuples
        return temp

if __name__ == "__main__":
    app = QtWidgets.QApplication([])

    widget = MediaPipePoseDetector()
    widget.show()

    sys.exit(app.exec())