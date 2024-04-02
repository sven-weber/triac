FROM ubuntu:22.04

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
RUN apt update && apt install -y python3 python3-pip && apt clean

# Install packages
COPY ./requirements/prod.txt requirements.txt
RUN pip install -r requirements.txt

#
# Enable systemd
#
RUN apt update && apt install -y systemd && apt clean
ENTRYPOINT ["/lib/systemd/systemd"]