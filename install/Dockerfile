FROM ubuntu:bionic

SHELL ["/bin/bash", "-c"]

RUN set -ex;\
apt update

RUN set -ex;\
apt install -y --no-install-recommends \
mbrola \
espeak \
git \
sox \
python3 \
python3-venv \
python3-dev \
python3-pip \
python3-setuptools \
portaudio19-dev \
build-essential && rm -rf /var/lib/apt;

RUN set -ex; \
mkdir /var/www;\
cd /var/www/; \
git clone https://github.com/loult-elte-fwere/loult-ng.git;\
cd loult-ng; \
python3 install/voices_install.py; \
pip3 install numpy wheel;\
pip3 install -r requirements.txt ;\
echo "SALT = 'default'" >> salt.py

VOLUME ["/var/www"]

EXPOSE 9000

ENTRYPOINT ["python3", "app.py"]
