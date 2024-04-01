FROM debian:12

WORKDIR /usr/app/triac

#
# Install SSH server
#
RUN apt update && apt install -y openssh-server nano vim && apt clean

# Allow key-based login for root account
RUN sed -i 's/#PermitRootLogin prohibit-password/PermitRootLogin prohibit-password/' /etc/ssh/sshd_config
RUN sed -i 's/#PubkeyAuthentication yes/PubkeyAuthentication yes/' /etc/ssh/sshd_config

# Copy ssh key
COPY ./ssh-keys/id_rsa.pub /root/.ssh/authorized_keys

# Apply fix that prevents ssh from starting
# See: https://groups.google.com/g/linux.debian.bugs.dist/c/5XBMJN1tLLE
RUN mkdir /run/sshd 

EXPOSE 22

#
# Install python
#
RUN apt update && apt install -y python3 && apt clean

#
# Enable systemd
#
ENV container docker
ENV DEBIAN_FRONTEND noninteractive

RUN apt update && apt install -y systemd && apt clean

#docker run --cgroupns=host --privileged -p 1234:22 --volume /sys/fs/cgroup:/sys/fs/cgroup test
ENTRYPOINT ["/lib/systemd/systemd"]