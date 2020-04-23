FROM python:3.8-buster

SHELL ["/bin/bash", "-c"]

# Mbrola is tagged as non-free since buster?
RUN set -ex; echo "deb http://deb.debian.org/debian buster contrib non-free" > /etc/apt/sources.list.d/debian-non-free.list && \
	apt-get -qq update

RUN set -ex;\
	apt install -y --no-install-recommends \
	mbrola \
	espeak \
	git \
	sox \
	portaudio19-dev \
	build-essential && rm -rf /var/lib/apt;

RUN mkdir -p /var/www/loult-ng;

WORKDIR "/var/www/loult-ng"

ADD ./requirements.txt /var/www/loult-ng

RUN set -ex; pip3 install -r requirements.txt;

RUN set -ex; pip3 install numpy wheel;

RUN set -ex; python -m voxpopuli.voice_install fr us es de;

RUN set -ex; rm /var/www/loult-ng/requirements.txt;

RUN set -ex; \
	git clone https://github.com/loult-elte-fwere/loult-ng.git . ;

RUN set -ex; \
	echo "SALT = 'default'" >> salt.py; \
	cp config.py.default config.py

# The server binds to loopback, making it enable to communicate outside the container.
RUN set -ex; sed -r -i 's/127\.0\.0\.1/0\.0\.0\.0/g' poke.py

VOLUME ["/var/www/loult-ng"]

EXPOSE 9000

CMD ["python3.8", "/var/www/loult-ng/poke.py"]
