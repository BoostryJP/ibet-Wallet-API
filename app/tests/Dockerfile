FROM python:3.6-alpine3.13

# make application directory
RUN mkdir -p /app/ibet-Wallet-API/

# install packages
RUN apk update \
 && apk add --no-cache --virtual .build-deps \
      make \
      gcc \
      g++ \
      musl-dev \
      postgresql-dev \
      libffi-dev \
      autoconf \
      automake \
      inotify-tools \
      libtool \
      gmp-dev \
      zeromq \
      zeromq-dev \
      curl

# add apl user/group
# NOTE: '/bin/bash' was added when 'libtool' installed.
RUN addgroup -g 1000 apl \
 && adduser -G apl -D -s /bin/bash -u 1000 apl \
 && echo 'apl ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers \
 && chown -R apl:apl /app

# python package install 1
USER apl
COPY requirements.txt /app/requirements.txt
RUN pip install --upgrade pip setuptools \
 && pip install -r /app/requirements.txt

# python package install 2
COPY app/tests/requirements.txt /app/requirements2.txt
RUN pip install -r /app/requirements2.txt
RUN rm -f /app/requirements.txt \
 && rm -f /app/requirements2.txt \
 && echo 'export LANG=ja_JP.utf8' >> ~/.bash_profile \
 && echo 'export PATH=$PATH:$HOME/.local/bin' >> ~/.bash_profile

# deploy app
USER root
COPY . /app/ibet-Wallet-API/
RUN chown -R apl:apl /app/ibet-Wallet-API && \
    chmod 755 /app/ibet-Wallet-API
RUN unzip /app/ibet-Wallet-API/data/zip_code.zip -d /app/ibet-Wallet-API/data/

USER apl
CMD /app/ibet-Wallet-API/app/tests/qa.sh
