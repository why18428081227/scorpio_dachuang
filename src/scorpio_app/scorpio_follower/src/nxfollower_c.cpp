/*
  * Copyright (c) 2016, SHENZHEN NXROBO Co.,LTD.
  * All rights reserved.
  *
  * 优化说明：增加YOLO目标订阅和分层状态机控制
  * 实现：远距离视觉转向 → 中距离转向+前进 → 近距离深度接管
  */
#ifndef SPARK_APP_SPARK_FOLLOWER_SRC_NXFOLLOWER_HPP_
#define SPARK_APP_SPARK_FOLLOWER_SRC_NXFOLLOWER_HPP_

#include <ros/ros.h>
#include <geometry_msgs/Twist.h>
#include <geometry_msgs/Point.h>  // 【新增】接收YOLO目标消息
#include <pcl_ros/point_cloud.h>
#include <pcl/point_types.h>
#include <cmath>

#define MAX_LINEAR_X 0.3
#define DEPTH_TAKEOVER_DISTANCE 1.5  // 与Python节点一致

namespace nxfollower
{
typedef pcl::PointCloud<pcl::PointXYZ> PointCloud;

class NxFollowerNode
{
private:
  ros::NodeHandle nhandle;
  ros::Publisher cmdvel_pub;
  ros::Subscriber cloud_sub;
  ros::Subscriber yolo_sub;  // 【新增】YOLO目标订阅者

  // 深度算法参数
  double min_y_, max_y_, min_x_, max_x_, max_z_;
  double goal_depth_, z_scale_, x_scale_;
  double depth_thre, y_thre;

  // 【新增】YOLO目标数据
  float target_x_offset;   // 左右偏移（-1.0 ~ 1.0）
  float target_distance;   // 目标距离（米）
  bool target_detected;    // 是否检测到目标

public:
  NxFollowerNode(ros::NodeHandle nh)
  {
    nhandle = nh;

    // 深度算法参数（仿真优化版）
    min_x_ = -0.4;
    max_x_ = 0.4;
    min_y_ = -0.2;
    max_y_ = 0.6;
    max_z_ = 2.5;
    goal_depth_ = 1.0;  // 深度跟随目标距离
    z_scale_ = 1.0;
    x_scale_ = 3.0;
    depth_thre = 0.1;
    y_thre = 0.087222222;

    // 【新增】初始化YOLO数据
    target_x_offset = 0.0;
    target_distance = 99.0;
    target_detected = false;

    ROS_INFO("==============================================================");
    ROS_INFO("🚀 Scorpio 决策+深度跟随节点启动成功！");
    ROS_INFO("📡 订阅YOLO话题: /yolo/target_offset");
    ROS_INFO("📡 订阅深度话题: /camera/depth/points");
    ROS_INFO("🎯 深度接管距离: %.1fm", DEPTH_TAKEOVER_DISTANCE);
    ROS_INFO("==============================================================");

    // 发布控制命令
    cmdvel_pub = nhandle.advertise<geometry_msgs::Twist>("/cmd_vel", 1);
    // 订阅深度点云
    cloud_sub = nhandle.subscribe<PointCloud>("/camera/depth/points", 1, &NxFollowerNode::pointCloudCb, this);
    // 【新增】订阅YOLO目标
    yolo_sub = nhandle.subscribe<geometry_msgs::Point>("/yolo/target_offset", 1, &NxFollowerNode::yoloCb, this);
  }

  virtual ~NxFollowerNode() {}

  // 【新增】YOLO目标回调函数
  void yoloCb(const geometry_msgs::Point::ConstPtr& msg)
  {
    target_x_offset = msg->x;
    target_distance = msg->z;
    target_detected = (target_distance < 10.0);  // 距离<10m表示检测到
  }

  // 深度点云回调函数
  void pointCloudCb(const PointCloud::ConstPtr &cloud)
  {
    float x = 0.0, z = 0.0;
    unsigned int n = 0;
    pcl::PointXYZ pt;

    for (int kk = 0; kk < cloud->points.size()/2; kk++)
    {
      pt = cloud->points[kk];
      if (!std::isnan(pt.x) && !std::isnan(pt.y) && !std::isnan(pt.z) &&
          !std::isinf(pt.x) && !std::isinf(pt.y) && !std::isinf(pt.z))
      {
        if (-pt.y > min_y_ && -pt.y < max_y_ && pt.x < max_x_ && pt.x > min_x_ && pt.z < max_z_)
        {
          x += pt.x;
          z += pt.z;
          n++;
        }
      }
    }

    ROS_INFO("深度点云数量: %d", n);

    // 调用决策控制函数
    pubCmd(-x/n, z/n, n);
  }

  // 【核心修改】分层决策控制函数
  void pubCmd(const float &depth_x, const float &depth_z, const int &point_count)
  {
    geometry_msgs::TwistPtr cmd(new geometry_msgs::Twist());

    // ==================== 状态机决策逻辑 ====================
    // 状态1：未检测到目标 → 停车
    if (!target_detected)
    {
      ROS_INFO_THROTTLE(1, "状态: 未检测到目标 → 停车");
      cmdvel_pub.publish(cmd);
      return;
    }

    // 状态2：远距离（>1.5m）→ 只转向，不前进
    if (target_distance > DEPTH_TAKEOVER_DISTANCE)
    {
      ROS_INFO_THROTTLE(1, "状态: 远距离(%.2fm) → 视觉转向", target_distance);
      cmd->angular.z = target_x_offset * 2.0;  // 用YOLO偏移量转向
      cmd->linear.x = 0.0;
    }
    // 状态3：中距离（1.0m ~ 1.5m）→ 转向 + 缓慢前进
    else if (target_distance > goal_depth_ && target_distance <= DEPTH_TAKEOVER_DISTANCE)
    {
      ROS_INFO_THROTTLE(1, "状态: 中距离(%.2fm) → 转向+前进", target_distance);
      cmd->angular.z = target_x_offset * 2.0;  // 用YOLO偏移量转向
      cmd->linear.x = 0.15;  // 缓慢前进
    }
    // 状态4：近距离（<1.0m）→ 深度算法完全接管
    else
    {
      ROS_INFO_THROTTLE(1, "状态: 近距离(%.2fm) → 深度接管", target_distance);
      
      // 只有点云数量足够时才用深度控制
      if (point_count > 800)
      {
        double curr_dist = sqrt(depth_x * depth_x + depth_z * depth_z);
        if (curr_dist == 0)
        {
          cmdvel_pub.publish(cmd);
          return;
        }

        float x_linear = (depth_z - goal_depth_) * z_scale_;
        float z_angular = asin(depth_x / curr_dist) * x_scale_;

        if (depth_thre > fabs(depth_z - goal_depth_))
          x_linear = 0;
        if (y_thre > depth_x && depth_x > -y_thre)
          z_angular = 0;

        if (x_linear > MAX_LINEAR_X)
          x_linear = MAX_LINEAR_X;
        else if (x_linear < -MAX_LINEAR_X)
          x_linear = -MAX_LINEAR_X;

        cmd->linear.x = x_linear;
        cmd->angular.z = z_angular;
      }
      else
      {
        // 点云不足时，继续用YOLO转向
        cmd->angular.z = target_x_offset * 2.0;
        cmd->linear.x = 0.0;
      }
    }
    // ============================================================

    ROS_INFO("最终控制: 线速度=%.3f, 角速度=%.3f", cmd->linear.x, cmd->angular.z);
    cmdvel_pub.publish(cmd);
  }

  void spin()
  {
    ros::spin();
  }
};
}

/*main*/
int main(int argc, char **argv)
{
  ros::init(argc, argv, "s_spark_follower_node");
  ros::NodeHandle n;

  nxfollower::NxFollowerNode nxfollower(n);
  nxfollower.spin();

  return 0;
}

#endif
