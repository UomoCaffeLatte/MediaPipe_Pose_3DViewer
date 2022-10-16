from PySide6 import QtCore, QtWidgets, QtGui, QtOpenGLWidgets
from PySide6 import QtMultimedia as qm
from OpenGL.GL import *
from OpenGL.GLU import *
from typing import Callable
import sys
import numpy as np
import cv2

default_nuitrack_joint_hierarchy = {
        "Neck":["Head"],
        "LeftCollar":["Neck","LeftShoulder", "RightShoulder"],
        "Torso":["LeftCollar"],
        "Waist":["Torso", "LeftHip", "RightHip"],
        "LeftShoulder":["LeftElbow"],
        "RightShoulder":["RightElbow"],
        "LeftElbow":["LeftWrist"],
        "RightElbow":["RightWrist"],
        "LeftWrist":["LeftHand"],
        "RightWrist":["RightHand"],
        "LeftHip":["LeftKnee"],
        "RightHip":["RightKnee"],
        "LeftKnee":["LeftAnkle"],
        "RightKnee":["RightAnkle"]
    }

class WidgetCreationHelper():
    def CreatePushButton(self, name:str, slot:Callable=None, autoRepeat:bool=False):
        button = QtWidgets.QPushButton(name)
        button.clicked.connect(slot)
        button.setAutoRepeat(autoRepeat)
        return button

    def CreateLabel(self, string:str, textColor:str="black", backgroundColor:str="", align:QtCore.Qt.Alignment= QtCore.Qt.AlignTop):
        label = QtWidgets.QLabel(string, alignment=align)
        label.setStyleSheet(f"color:{textColor}; background-color:{backgroundColor};")
        return label

    def CreateComboBox(self, slot:Callable=None, *args):
        combobox = QtWidgets.QComboBox()
        for arg in args: combobox.addItem(arg)
        if slot != None: combobox.activated.connect(slot)
        return combobox

    def CreateFloatTextInput(self, name:str, min:float=0.0, max:float=100000.0,decimal:int=2):
        textBox = QtWidgets.QLineEdit()
        textBox.setValidator(QtGui.QDoubleValidator(min, max, decimal))
        label = self.CreateLabel(name)
        return textBox, label

class SkeletonViewerWidget(QtWidgets.QWidget, WidgetCreationHelper):
    def __init__(self, headerTitle:str, jointHierarchy=default_nuitrack_joint_hierarchy) -> None:
        super().__init__()
        # create widgets
        self.gLWidget = GLWidget(jointHierarchy)
        self.cameraControlWidget = CameraControlWidget()
        # create labels
        self.headerLbl = self.CreateLabel(headerTitle, align=QtCore.Qt.AlignCenter)
        # add slot to camera rot signals
        self.cameraControlWidget.rotRightSignal.connect(self.gLWidget.RotateRightCallback)
        self.cameraControlWidget.rotLeftSignal.connect(self.gLWidget.RotateLeftCallback)
        # Layout
        self.layout = QtWidgets.QVBoxLayout(self)
        self.layout.addWidget(self.headerLbl)
        self.layout.addWidget(self.gLWidget)
        self.layout.addWidget(self.cameraControlWidget)

class CameraViewerWidget(QtWidgets.QWidget, WidgetCreationHelper):
    ImageSignal = QtCore.Signal(np.ndarray)

    def __init__(self) -> None:
        super().__init__()
        # cv2 camera feed
        self.cv2VideoStream = None
        # find camera devices and create selection widget
        availableCams:list[qm.QCameraDevice] = qm.QMediaDevices.videoInputs()
        self.availableCamNames = []
        for cams in availableCams: self.availableCamNames.append(cams.description())
        self.camListDropDownBoxWidget = self.CreateComboBox(self.SelectCamera, *self.availableCamNames)
        # image widget
        self.videoSize = QtCore.QSize(500, 500)
        self.imageWidget = QtWidgets.QLabel()
        self.imageWidget.setFixedSize(self.videoSize)
        # layout
        self.layout = QtWidgets.QVBoxLayout(self)
        self.layout.addWidget(self.imageWidget)
        self.layout.addWidget(self.camListDropDownBoxWidget)

        #self.ImageSignal.connect(self.DisplayImage)
        # manually connect when required

        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.getVideoStream)
        self.timer.start(30)

    def SelectCamera(self, value) -> None:
        self.cv2VideoStream = cv2.VideoCapture(value)
        if not self.cv2VideoStream.isOpened():
            self.cv2VideoStream = None
            print("ERROR! Unable to open camera")
            return
        print("Camera open and ready!")

    def getVideoStream(self):
        """Read frame from camera and repaint QLabel widget.
        """
        if self.cv2VideoStream != None:
            _, frame = self.cv2VideoStream.read()
            frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            frame = cv2.flip(frame, 1)
            self.ImageSignal.emit(frame)

    def DisplayImage(self, frame):
        frameDisplay = cv2.resize(frame, self.videoSize.toTuple(), interpolation = cv2.INTER_AREA)
        frameDisplay = QtGui.QImage(frameDisplay, frameDisplay.shape[1], frameDisplay.shape[0], 
                        frameDisplay.strides[0], QtGui.QImage.Format_RGB888)
        self.imageWidget.setPixmap(QtGui.QPixmap.fromImage(frameDisplay))


class GLWidget(QtOpenGLWidgets.QOpenGLWidget, QtGui.QOpenGLFunctions, WidgetCreationHelper):
    def __init__(self, jointHierarchy) -> None:
        super().__init__()
        # variable init
        self.aspectRatio = self.size().width() / self.size().height()
        self.jointHierarchy = jointHierarchy
        self.rotCameraDeg = 0
        self.frameData = None
        # create layout
        self.layout = QtWidgets.QVBoxLayout(self)

    def minimumSizeHint(self):
        # set minimum widget size
        return QtCore.QSize(300,400)
    
    def resizeEvent(self, e: QtGui.QResizeEvent) -> None:
        # update aspect ration for openGl
        self.aspectRatio = self.size().width() / self.size().height()
        return super().resizeEvent(e)

    def initializeGL(self):
        # override init openGl
        # enable transparency
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        # camera settings
        gluPerspective(45, self.aspectRatio , 0.0, 100.0)
        glTranslate(0,0,-4)
        glRotate(0,0,0,0)

    def Draw(self, frameData):
        if frameData != None:
            self.frameData = frameData
            self.update()

    def Point(self, points:list, colour:tuple=(0,1,0)) -> None:
        # GL Points
        glPointSize(5.5)
        glBegin(GL_POINTS)
        glColor3fv(colour) # green
        for point in points:
            glVertex3f(*point)
        glEnd()

    def Line(self, points:dict, jointsHierarchy:dict, colour:tuple=(1,0,0)) -> None:
        # GL Lines from skeletal data
        glLineWidth(2.5)
        glBegin(GL_LINES)
        glColor3fv(colour) # red
        for parent, children in jointsHierarchy.items():
            if parent in points:
                # get parent co-ords
                pVec = points[parent]
                for child in children:
                    if child in points:
                        cVec = points[child]
                        glVertex3f(*pVec) # start of line
                        glVertex(*cVec) # end of line
        glEnd()

    def ClearGL(self) -> None:
        self.data = None
        self.playbackInfoLbl.setText("--/--")
        self.update()

    # slots
    def paintGL(self) -> None:
        # main override for opengl draw func
        glClear(GL_COLOR_BUFFER_BIT|GL_DEPTH_BUFFER_BIT)
        # rotate camera
        glRotate(self.rotCameraDeg,0,1,0)
        self.rotCameraDeg = 0
        # draw skeleton
        if self.frameData != None:
            self.Line(self.frameData, self.jointHierarchy)
            self.Point(list(self.frameData.values()))

    def RotateLeftCallback(self):
        self.rotCameraDeg = -4
        self.update()

    def RotateRightCallback(self):
        self.rotCameraDeg = +4
        self.update()

class CameraControlWidget(QtWidgets.QWidget, WidgetCreationHelper):
    rotRightSignal = QtCore.Signal()
    rotLeftSignal = QtCore.Signal()

    def __init__(self) -> None:
        super().__init__()

        # create buttons
        self.rotRightBtn = self.CreatePushButton("Rotate >", self.RotateRightCallback, True)
        self.rotLeftBtn = self.CreatePushButton("< Rotate", self.RotateLeftCallback, True)
        # arrange widgets
        self.layout = QtWidgets.QHBoxLayout(self)
        self.layout.addWidget(self.rotLeftBtn)
        self.layout.addWidget(self.rotRightBtn)
    
    # Callbacks
    def RotateRightCallback(self): self.rotRightSignal.emit()
    def RotateLeftCallback(self): self.rotLeftSignal.emit()

class PlayerControlWidget(QtWidgets.QWidget, WidgetCreationHelper):
    playpauseSignal = QtCore.Signal()
    backwardSignal = QtCore.Signal()
    forwardSignal = QtCore.Signal()
    resetSignal = QtCore.Signal()

    def __init__(self) -> None:
        super().__init__()

        # create buttons
        self.playpauseBtn = self.CreatePushButton("Play/Stop", self.PlayPauseCallback)
        self.resetBtn = self.CreatePushButton("Reset", self.ResetCallback)
        self.forwardBtn = self.CreatePushButton(">> 1 Frame", self.ForwardCallback, True)
        self.backwardBtn = self.CreatePushButton("1 frame <<", self.BackwardCallback, True)
        # arrange widgets
        self.layout = QtWidgets.QHBoxLayout(self)
        self.layout.addWidget(self.backwardBtn)
        self.layout.addWidget(self.playpauseBtn)
        self.layout.addWidget(self.resetBtn)
        self.layout.addWidget(self.forwardBtn)
        
    # Callbacks
    def PlayPauseCallback(self): self.playpauseSignal.emit()
    def ResetCallback(self): self.resetSignal.emit()
    def ForwardCallback(self): self.forwardSignal.emit()
    def BackwardCallback(self): self.backwardSignal.emit()


if __name__ == "__main__":
    app = QtWidgets.QApplication([])

    widget = CameraViewerWidget()
    #widget.LoadData(data, data, path)
    #widget.resize(800, 600)
    widget.show()

    sys.exit(app.exec())