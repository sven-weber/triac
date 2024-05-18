FROM postgres:16-bookworm

#
# Install SSH server
#
RUN apt update && apt install -y openssh-server nano vim pkg-config libsystemd-dev && apt clean

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
RUN pip install --break-system-packages -r requirements.txt
COPY ./requirements/image.txt image.txt
RUN pip install --break-system-packages -r image.txt

#
# Enable systemd
#
RUN apt update && apt install -y systemd && apt clean
ENV container docker

RUN systemctl mask getty@tty1.service
RUN systemctl mask getty@tty2.service
RUN systemctl mask getty@tty3.service
RUN systemctl mask getty@tty4.service
RUN systemctl mask getty@tty5.service
RUN systemctl mask getty@tty6.service

#
# Postgres specific configurations
#
ENV POSTGRES_PASSWORD postgres
ENV POSTGRES_USER postgres
ENV POSTGRES_DB postgres

# Copy the example database
COPY ./triac/lib/docker/images/debian-12-postgres-16/postgres-sakila-schema.sql docker-entrypoint-initdb.d

# Create systemd service, copy start script and enable the postgres service on startup
COPY ./triac/lib/docker/images/debian-12-postgres-16/postgres.service /etc/systemd/system/
COPY ./triac/lib/docker/images/debian-12-postgres-16/start-postgres.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/start-postgres.sh && systemctl enable postgres


ENTRYPOINT ["/lib/systemd/systemd"]
