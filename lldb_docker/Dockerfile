FROM ubuntu:22.04

# update
RUN apt-get clean
RUN apt-get update -y
RUN apt-get upgrade -y

# install
RUN apt-get install -y curl
RUN apt-get install -y lldb
#if there are troubles use this instead:
#RUN apt-get install --fix-missing -y lldb
RUN apt-get install -y python3-lldb-14
RUN ln -s /usr/lib/llvm-14/lib/python3.10/dist-packages/lldb/* /usr/lib/python3/dist-packages/lldb/
RUN apt-get install -y libusbmuxd-tools
RUN apt-get install -y python3-pip
RUN pip install frida-tools==13.0.4
RUN apt-get install -y cmake make gcc g++ libglib2.0-dev
RUN apt-get install -y openssh-client
RUN apt-get install -y socat
RUN pip install keystone-engine
RUN pip install capstone==5.0.6
RUN pip install pymobiledevice3


# workdir
WORKDIR /env

COPY ./config.cfg /env/
COPY ./lldb_docker/env /env/

RUN chmod +x /env/init
RUN chmod +x /env/scripts/generate_lldbinit