#!/usr/bin/env python
# Copyright (c) 2013, Oregon State University
# All rights reserved.

# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of the Oregon State University nor the
#       names of its contributors may be used to endorse or promote products
#       derived from this software without specific prior written permission.

# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL OREGON STATE UNIVERSITY BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

# Author Dan Lazewatsky/lazewatd@engr.orst.edu
import roslib; roslib.load_manifest('world_intersect')
import rospy
#from tabletop_object_detector.msg import Table
from visualization_msgs.msg import Marker
from geometry_msgs.msg import Point, PointStamped, PoseStamped
from sensor_msgs.msg import PointCloud2
import numpy as np
from tf.transformations import quaternion_from_euler, euler_from_quaternion
from math import sin, cos, pi
import tf
from pr2_python.pointclouds import xyz_array_to_pointcloud2

def cast_ray(pose, plane, tfl):
    # assume the plane passes through table.pose
    # and the vector table.pose.x,table.pose.y,table.pose.z+1 is a
    # normal for the table in its frame
    
    # point
    q = np.array([
        plane.pose.position.x,
        plane.pose.position.y,
        plane.pose.position.z
    ])
    
    # normal
    m = q + [0,0,1]
    
    try:
        # pose.header.stamp = tfl.getLatestCommonTime(table.pose.header.frame_id, pose.header.frame_id)
        tfl.waitForTransform(plane.header.frame_id, pose.header.frame_id, rospy.Time(0), rospy.Duration.from_sec(5))
        pose.header.stamp = rospy.Time(0)
        pose_transformed = tfl.transformPose(plane.header.frame_id, pose)
    except tf.Exception, e:
        print 'trouble with tf lookup'
        print e.message
        return False
       
    # origin vector
    p = np.array([pose_transformed.pose.position.x, pose_transformed.pose.position.y, pose_transformed.pose.position.z])
    quat = (
        pose_transformed.pose.orientation.x,
        pose_transformed.pose.orientation.y,
        pose_transformed.pose.orientation.z,
        pose_transformed.pose.orientation.w
    )
    ax,ay,az = euler_from_quaternion(quat)
    # direction vector
    # a pose is basically spherical coordinates, so convert to cartesian
    d = np.array([
        -cos(az)*cos(ay),
        -sin(az)*cos(ay),
         sin(ay)
    ])
    # intersection
    #t = (q - p).dot(m) / d.dot(m)
    t = np.dot(q-p,m) / np.dot(d,m)
    if t < 0: # some normal must be flipped since t is normally > 0
        v = PointStamped()
        v.header = plane.header
        v.point.x, v.point.y, v.point.z = p + t*d
        return v
    return False
    
class Intersector(object):
    def __init__(self, plane_frame):
        self.plane_frame = plane_frame
        self.pose        = None
        self.table_pose  = PoseStamped()
        self.rate        = rospy.Rate(20)
        self.tfl         = tf.TransformListener()
        self.int_pub     = rospy.Publisher('intersected_points', PointCloud2)

        self.table_pose.pose.orientation.w = 1.0
        self.table_pose.header.frame_id = plane_frame

    def pose_cb(self, pose):
        self.pose = pose
        
    # def table_cb(self, table):
    #     self.table = table
        
    def run(self):
        while not rospy.is_shutdown():
            if not self.pose: continue
            intersection = cast_ray(self.pose, self.table_pose, self.tfl)
            if intersection:
                cloud = xyz_array_to_pointcloud2(np.array([[
                    intersection.point.x,
                    intersection.point.y,
                    intersection.point.z
                ]]))
                cloud.header.frame_id = self.plane_frame
                cloud.header.stamp = self.pose.header.stamp
                self.int_pub.publish(cloud)
                self.rate.sleep()
    
if __name__ == '__main__':
    rospy.init_node('intersect_plane')
    plane_frame = rospy.get_param('~plane_frame')
    print 'Plane frame = %s' % plane_frame
    intersector = Intersector(plane_frame)
    pose_sub  = rospy.Subscriber('pose',  PoseStamped, intersector.pose_cb)
    # table_sub = rospy.Subscriber('table', Table,       intersector.table_cb)
    intersector.run()

def test():
    rospy.init_node('intersect_plane_test')
    marker_pub = rospy.Publisher('table_marker', Marker)
    pose_pub = rospy.Publisher('pose', PoseStamped)
    int_pub = rospy.Publisher('intersected_points', PointCloud2)
    tfl = tf.TransformListener()
    
    # Test table
    table = Table()
    table.pose.header.frame_id = 'base_link'
    table.pose.pose.orientation.x, table.pose.pose.orientation.y, table.pose.pose.orientation.z, table.pose.pose.orientation.w = (0,0,0,1)
    table.x_min = -0.5
    table.x_max =  0.5
    table.y_min = -0.5
    table.y_max =  0.5

    # A marker for that table
    marker = Marker()
    marker.header.frame_id = table.pose.header.frame_id
    marker.id = 1
    marker.type = Marker.LINE_STRIP
    marker.action = 0
    marker.pose = table.pose.pose
    marker.scale.x, marker.scale.y, marker.scale.z = (0.005,0.005,0.005)
    marker.color.r, marker.color.g, marker.color.b, marker.color.a = (0.0,1.0,1.0,1.0) 
    marker.frame_locked = False
    marker.ns = 'table'
    marker.points = [
        Point(table.x_min,table.y_min, table.pose.pose.position.z),
        Point(table.x_min,table.y_max, table.pose.pose.position.z),
        Point(table.x_max,table.y_max, table.pose.pose.position.z),
        Point(table.x_max,table.y_min, table.pose.pose.position.z),
        Point(table.x_min,table.y_min, table.pose.pose.position.z),
    ]
    marker.colors = []
    marker.text = ''
    # marker.mesh_resource = ''
    marker.mesh_use_embedded_materials = False
    marker.header.stamp = rospy.Time.now()

    # A test pose
    pose = PoseStamped()
    pose.header = table.pose.header
    pose.pose.position.x, pose.pose.position.y, pose.pose.position.z = (0,0,0.5)
    pose.pose.orientation.x, pose.pose.orientation.y, pose.pose.orientation.z, pose.pose.orientation.w = quaternion_from_euler(0,-pi/5,pi/5)
    
    intersection = cast_ray(pose, table, tfl)
    cloud = xyz_array_to_pointcloud2(np.array([[intersection.point.x, intersection.point.y, intersection.point.z]]))
    cloud.header = pose.header
    
    while not rospy.is_shutdown():
        marker_pub.publish(marker)
        pose_pub.publish(pose)
        int_pub.publish(cloud)
        rospy.loginfo('published')
        rospy.sleep(0.1)
