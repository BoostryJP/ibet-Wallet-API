FROM python:3.6-slim-buster

# make application directory
RUN mkdir -p /app/ibet-Wallet-API/

# add apl user/group
RUN groupadd -g 1000 apl \
 && useradd -g apl -s /bin/bash -u 1000 -p apl apl \
 && echo 'apl ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers \
 && chown -R apl:apl /app \
 && mkdir -p /home/apl \
 && chown -R apl:apl /home/apl

# install packages
RUN apt-get update -q \
 && apt-get install -y --no-install-recommends \
 unzip \
 curl \
 build-essential \
 libssl-dev

# remove unnessesory package files
RUN apt clean \
 && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

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
