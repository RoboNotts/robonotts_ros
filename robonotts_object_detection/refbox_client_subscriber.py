#!/usr/bin/env python

import metrics_benchmark_mockup.metrics_benchmark_mockup
import rospy

if __name__ == '__main__':
    rospy.init_node('metrics_benc', anonymous=True)
    metrics_benchmark_mockup.metrics_benchmark_mockup.main()
