FROM ubuntu:22.04

WORKDIR /usr/app/triac


# Install SSH server
RUN apt update && apt install -y openssh-server nano vim && apt clean

# Allow password login for root account (needed for ansible)
RUN sed -i 's/#PermitRootLogin prohibit-password/PermitRootLogin yes/' /etc/ssh/sshd_config

# change password root
RUN echo "root:ansible" | chpasswd

# Apply fix that prevents ssh from starting
# See: https://groups.google.com/g/linux.debian.bugs.dist/c/5XBMJN1tLLE
RUN mkdir /run/sshd 

#  Run the ssh server
CMD ["/usr/sbin/sshd", "-D", "-e"]