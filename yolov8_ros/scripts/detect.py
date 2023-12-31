#! /usr/bin/env python3
from sensor_msgs.msg import Image, CameraInfo
from yolov8_ros_msgs.msg import BoundingBox, BoundingBoxes
from std_msgs.msg import Header
from ultralytics import YOLO

import rospy
import tf
import cv2
import numpy as np
from cv_bridge import CvBridge

if __name__ == "__main__":
    try:
        rospy.init_node("yolo_ros")

        model = YOLO("yolov8m.pt")
        bridge=CvBridge()

        # from ndarray
        #im2 = cv2.imread("bus.jpg")

        img_pub = rospy.Publisher("yolo_v8/detect_img", Image, queue_size=10)
        bb_pub = rospy.Publisher("yolo_v8/boudingbox", BoundingBox, queue_size=10)
        bbs_pub = rospy.Publisher("yolo_v8/boudingboxes", BoundingBoxes, queue_size=10)
        caminfo_pub = rospy.Publisher("yolo_v8/camera_info", CameraInfo, queue_size=10)

        bbs = BoundingBoxes()
        detect_img = Image()
        img_info = CameraInfo()

        camera_frame = ""

        def caminfo_callback(msg):
            global img_info, caminfo_pub
            img_info = msg
            caminfo_pub.publish(img_info)

        def img_callback(msg):
            bbs_list = []
            bb = BoundingBox()
            test = []
            if msg is None and camera_frame == "":
                rospy.loginfo("None data")

            img=bridge.imgmsg_to_cv2(msg)
            img=cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            results = model.predict(source=img, conf=0.5)  # save predictions as labels
            #print(results[0].orig_img)
            class_names=results[0].names
            for result in results:
                # Detection
                result = result.cuda()
                prop = result.boxes.conf
                result = result.cpu()
                result = result.numpy()
                result.boxes.xyxy   # box with xyxy format, (N, 4)
                #print(class_names)
                result.boxes.conf   # confidence score, (N, 1)
                result.boxes.cls    # cls, (N, 1)
                #print(result.boxes.cls)
                
                # Segmentation
                #result.masks.data      # masks, (N, H, W)
                #result.masks.xy        # x,y segments (pixels), List[segment] * N
                #result.masks.xyn       # x,y segments (normalized), List[segment] * N

                # Classification
                probs = result.probs
                #print(result.probs, result.boxes.cls )

                """
                for i in probs:
                    print(i)
                """
                    
                for i,bbox in enumerate(result.boxes.xyxy):
                    bb = BoundingBox()
                    #print(result.boxes.xyxy)
                    x1,y1,x2,y2=bbox
                    #color = list(np.random.random(size=3) * 256)
                    
                    #img=cv2.rectangle(img, (int(x1),int(y1)), (int(x2),int(y2)),color=color)

                    cls=class_names[result.boxes.cls[i]]
                    #img=cv2.putText(img,cls, (int(x1),int(y1)),cv2.FONT_HERSHEY_PLAIN,1,color=color)

                    bb.xmin = int(x1)
                    bb.ymin = int(y1)
                    bb.xmax = int(x2)
                    bb.ymax = int(y2)
                    bb.class_name = cls
                    
                    bb.id = int(result.boxes.cls[i])
                    bb.probability = prop[i]
                    bb.header.frame_id = str(bb.id)+"_"+cls
                    
                    # 検出データをパブリッシュ
                    bb_pub.publish(bb)
                    # 1 fps で検出したデータをリスト化    
                    bbs_list.append(bb)
                    # test
                    test.append(cls)
                
            # リスト化されたデータ群をパブリッシュ
            bbs.bounding_boxes = bbs_list
            bb.header.stamp.secs = int(rospy.get_time())
            bbs_pub.publish(bbs)
            
            detect_img = bridge.cv2_to_imgmsg(results[0].plot(), encoding="bgr8")
            detect_img.header.frame_id = msg.header.frame_id
            img_pub.publish(detect_img)

        #rospy.Publisher()
        rospy.loginfo("yolo_v8 start")
        rospy.Subscriber("image_topic", Image, img_callback)
        rospy.Subscriber("camera_info", CameraInfo, caminfo_callback)
        rospy.spin()

    except rospy.ROSInterruptException:
        rospy.loginfo("yolo_v8 done")
        pass
    
