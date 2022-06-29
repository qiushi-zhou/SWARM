# Distributed under the OSI-approved BSD 3-Clause License.  See accompanying
# file Copyright.txt or https://cmake.org/licensing for details.

cmake_minimum_required(VERSION 3.5)

file(MAKE_DIRECTORY
  "/Users/marinig/Documents/GitHub/openpose/3rdparty/caffe"
  "/Users/marinig/Documents/GitHub/openpose/build/caffe/src/openpose_lib-build"
  "/Users/marinig/Documents/GitHub/openpose/build/caffe"
  "/Users/marinig/Documents/GitHub/openpose/build/caffe/tmp"
  "/Users/marinig/Documents/GitHub/openpose/build/caffe/src/openpose_lib-stamp"
  "/Users/marinig/Documents/GitHub/openpose/build/caffe/src"
  "/Users/marinig/Documents/GitHub/openpose/build/caffe/src/openpose_lib-stamp"
)

set(configSubDirs )
foreach(subDir IN LISTS configSubDirs)
    file(MAKE_DIRECTORY "/Users/marinig/Documents/GitHub/openpose/build/caffe/src/openpose_lib-stamp/${subDir}")
endforeach()
