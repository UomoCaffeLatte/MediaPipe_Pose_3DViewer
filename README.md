# Dependencies
- pyside6
- numpy
- pyopengl
- pyopencv
- mediapipe

# Quickstart
Ensure a webcam is connected and run the poseDetection.py script. Select a camera from the dropdown box to load images and start processing.
A 3D skeleton will be reconstructed using visible joints (visibility > 0.7), you can rotate around the y axis using the left and right buttons under the 3D view.

# NOTE
This  is a very quick mock up to test out the media pipe pose detector. Hence, it is not optimised for performance (yet).