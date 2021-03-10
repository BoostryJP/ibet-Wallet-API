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

# install python packages
USER apl
COPY requirements.txt /app/requirements.txt
RUN pip install --upgrade pip setuptools \
 && pip install -r /app/requirements.txt \
 && rm -f /app/requirements.txt \
 && echo 'export LANG=ja_JP.utf8' >> ~/.bash_profile \
 && echo 'export PATH=$PATH:$HOME/.local/bin' >> ~/.bash_profile

# deploy app
USER root
COPY . /app/ibet-Wallet-API
RUN chown -R apl:apl /app/ibet-Wallet-API && \
    chmod 755 /app/ibet-Wallet-API
RUN unzip /app/ibet-Wallet-API/data/zip_code.zip -d /app/ibet-Wallet-API/data/
RUN unzip /app/ibet-Wallet-API/data/zip_code_jigyosyo.zip -d /app/ibet-Wallet-API/data/
USER apl
COPY run.sh healthcheck.sh /app/

EXPOSE 5000

CMD /app/run.sh
HEALTHCHECK --interval=10s CMD /app/healthcheck.sh
