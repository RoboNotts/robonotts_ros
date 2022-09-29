#!/usr/bin/env python3

import rospy
import json
import metrics_refbox_msgs.msg
from sensor_msgs.msg import Image
import random
from metrics_refbox_msgs.msg import Command
from metrics_refbox_msgs.msg import ObjectDetectionResult, PersonDetectionResult, ActivityRecognitionResult
from metrics_refbox_msgs.msg import GestureRecognitionResult, HandoverObjectResult, ReceiveObjectResult
from metrics_refbox_msgs.msg import ClutteredPickResult, AssessActivityStateResult, ItemDeliveryResult
from metrics_refbox_msgs.msg import BoundingBox2D
from darknet_ros_msgs.msg import BoundingBoxes
import time
import threading

class RefboxClientListener(object):
    person_box = BoundingBox2D()
    result_msg = None # The message to be sent back to the refBox
    ready_to_pub = False 
    image_saved = Image() # The currently saved Image
    object_classes = ["cup", "bowl", "bottle", "toothbrush", "book"]

    
    # Initialises the node, and subscribes to the needed topics
    def __init__(self):
        rospy.init_node('refbox_client_listener') 
        rospy.Subscriber("/metrics_refbox_client/command", metrics_refbox_msgs.msg.Command, self.handle_command) # Refbox Commands
        rospy.Subscriber("/darknet_ros/bounding_boxes", BoundingBoxes, self.update_bounding_boxes) # Bounding boxes from Darknet
        rospy.Subscriber("/locobot/camera/color/image_raw", Image, self.update_image) # Bucky's Camera
        self.publishers = {
            # Set up publishers for our results.
            "person": rospy.Publisher("metrics_refbox_client/person_detection_result", PersonDetectionResult, queue_size=10),
            "object": rospy.Publisher("metrics_refbox_client/object_detection_result", ObjectDetectionResult, queue_size=10),
            "gesture": rospy.Publisher("metrics_refbox_client/gesture_recognition_result", GestureRecognitionResult, queue_size=10)
        }
        self.requested_person = False
        self.requested_object = False
        rospy.spin() # Keeps the python node from terminating until it is closed by ROS
    
    #Updates the currently stored image.
    def update_image(self, msg):
        if self.ready_to_pub:
            self.result_msg.image = self.image_saved
            self.publishers[self.pub_type].publish(self.result_msg)
            self.ready_to_pub = False
        else:
            self.image_saved = msg
            
    def update_bounding_boxes(self, msg):
        for b in msg.bounding_boxes:
            if b.Class == "person" and b.probability >= 0.6 and self.requested_person:
                print(f"Found a person with {b.probability} certainty")
                self.result_msg = PersonDetectionResult()
                self.result_msg.message_type = self.result_msg.RESULT
                self.result_msg.person_found = True
                self.result_msg.box2d.min_x = b.xmin
                self.result_msg.box2d.min_y = b.ymin
                self.result_msg.box2d.max_x = b.xmax
                self.result_msg.box2d.max_y = b.ymax
                self.ready_to_pub = True
                self.pub_type = "person"
                self.requested_person = False
                break
            if self.requested_object and b.Class == self.search_object:
                print(f"Found a {b.Class} with {b.probability} certainty")
                self.result_msg = ObjectDetectionResult()
                self.result_msg.message_type = self.result_msg.RESULT
                self.result_msg.object_found = True
                self.result_msg.result_type = 1 # 2d bounding box
                self.result_msg.box2d.min_x = b.xmin
                self.result_msg.box2d.min_y = b.ymin
                self.result_msg.box2d.max_x = b.xmax
                self.result_msg.box2d.max_y = b.ymax
                self.ready_to_pub = True
                self.pub_type = "object"
                self.requested_object = False
                break

    def handle_command(self, msg):
        print("Handling command")
        if msg.command != 1: return

        if msg.task == Command.OBJECT_DETECTION:
            self.search_object = json.loads(msg.task_config)["Target object"].lower()
            print(f"Searching for a {self.search_object}")
            self.send_object_detection_result()
        elif msg.task == Command.PERSON_DETECTION:
            self.send_person_detection_result()
        elif msg.task == Command.GESTURE_RECOGNITION:
            self.send_gesture_recognition_result()

    def send_object_detection_result(self):
        print("Received object request")
        self.requested_object = True
        th = threading.Thread(target=self.timeout_object)
        th.start()
        th.join()

    def send_person_detection_result(self):
        print("Received person request")
        self.requested_person = True
        th = threading.Thread(target=self.timeout_person)
        th.start()
        th.join()

    def send_gesture_recognition_result(self):
        print("Received gresture request")
        self.result_msg = GestureRecognitionResult()
        self.result_msg.message_type = self.result_msg.RESULT
        self.result_msg.gestures = random.sample(["nodding", "pointing", "pull_hand_in_call_someone", "shaking_head", "stop_sign", "thumbs_down", "thumbs_up", "wave_someone_away", "waving_hand"], 2)
        time.sleep(random.uniform(0.5,5))
        self.publishers["gesture"].publish(self.result_msg)

    def timeout_person(self):
        st = time.time()
        while time.time() - st < 8:
            if not self.requested_person:
                return # person already found
        # waited >= 8 secs for person but not found
        self.result_msg = PersonDetectionResult()
        self.result_msg.message_type = self.result_msg.RESULT
        self.result_msg.person_found = False
        self.publishers["person"].publish(self.result_msg)
        self.requested_person = False

    def timeout_object(self):
        st = time.time()
        while time.time() - st < 8:
            if not self.requested_object:
                return
        self.result_msg = ObjectDetectionResult()
        self.result_msg.message_type = self.result_msg.RESULT
        self.result_msg.object_found = False
        self.publishers["object"].publish(self.result_msg)
        self.requested_object = False

if __name__ == '__main__':
    client = RefboxClientListener()


