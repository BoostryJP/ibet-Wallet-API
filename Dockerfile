FROM ubuntu:20.04

# make application directory
RUN mkdir -p /app

# add apl user/group
RUN groupadd -g 1000 apl \
 && useradd -g apl -s /bin/bash -u 1000 -p apl apl \
 && echo 'apl ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers \
 && chown -R apl:apl /app

# install packages
RUN apt-get update -q \
 && apt-get install -y --no-install-recommends \
 unzip \
 build-essential \
 ca-certificates \
 curl \
 libbz2-dev \
 libreadline-dev \
 libsqlite3-dev \
 libssl-dev \
 zlib1g-dev \
 libffi-dev \
 python3-dev \
 libpq-dev \
 automake \
 pkg-config \
 libtool \
 libgmp-dev \
 language-pack-ja-base \
 language-pack-ja \
 git \
 libyaml-cpp-dev

# remove unnessesory package files
RUN apt clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# install pyenv
RUN git clone https://github.com/pyenv/pyenv.git /home/apl/.pyenv
RUN chown -R apl:apl /home/apl
USER apl
RUN echo 'export PYENV_ROOT="$HOME/.pyenv"' >> ~apl/.bash_profile \
 && echo 'export PATH="$PYENV_ROOT/bin:$PATH"' >> ~apl/.bash_profile \
 && echo 'eval "$(pyenv init -)"' >> ~apl/.bash_profile \
 && echo 'export LANG=ja_JP.utf8' >> ~apl/.bash_profile

# install python
RUN . ~/.bash_profile \
 && pyenv install 3.6.13 \
 && pyenv global 3.6.13 \
 && pip install --upgrade pip

# install python packages
COPY requirements.txt /app/requirements.txt
RUN . ~/.bash_profile \
 && pip install -r /app/requirements.txt

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
