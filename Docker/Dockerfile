FROM ros:indigo-ros-base-trusty

ARG OVERLAY_WS=/opt/ros/overlay_ws

WORKDIR $OVERLAY_WS

RUN apt-get update && \
    apt-get install -y python-pip wget libpyside-dev python-kdtree && \
    rm -rf /var/lib/apt/lists/*

#RUN cd /tmp && \
#    wget https://files.pythonhosted.org/packages/6a/00/dbc3ba68410ebea7aacf23600641c17197fc06a9fbbd8681d41d1c81e7c8/kdtree-0.10-py2-none-any.whl && \
#    pip install kdtree-0.10-py2-none-any.whl

RUN mkdir src && cd  src && \
    git clone https://github.com/ROS-Legacy/ros-3d-interaction.git --branch indigo-devel && \
    git clone https://github.com/ROS-Legacy/pr2-python-minimal.git --branch hydro-devel

RUN . /opt/ros/$ROS_DISTRO/setup.sh && \
    apt-get update && rosdep install \
      --from-paths src \
      --ignore-src \
      -r -y && \
    rm -rf /var/lib/apt/lists/*

RUN . /opt/ros/$ROS_DISTRO/setup.sh && \
    catkin_make
    
