FROM ubuntu:22.04 AS builder

ENV PYTHON_VERSION=3.12.2
ENV UV_VERSION=0.5.5
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
ENV UV_INSTALL_DIR="/usr/local/bin"
ENV UV_PROJECT_ENVIRONMENT="/home/apl/.venv"

# make application directory
RUN mkdir -p /app

# add apl user/group
RUN groupadd -g 1000 apl \
 && useradd -g apl -s /bin/bash -u 1000 -p apl apl \
 && echo 'apl ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers \
 && chown -R apl:apl /app \
 && mkdir /home/apl \
 && chown -R apl:apl /home/apl

# install packages
RUN apt-get update -q \
 && apt-get upgrade -qy \
 && apt-get install -y --no-install-recommends \
 build-essential \
 ca-certificates \
 curl \
 libffi-dev \
 libpq-dev \
 libc-bin \
 clang \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# install uv
ADD https://astral.sh/uv/$UV_VERSION/install.sh /uv-installer.sh
RUN INSTALLER_NO_MODIFY_PATH=1 sh /uv-installer.sh && rm /uv-installer.sh

# install Python
RUN uv python install $PYTHON_VERSION

# prepare venv
USER apl
RUN mkdir /home/apl/.venv

# setup shell setting
#   .bash_profile
RUN echo 'if [ -f ~/.bashrc ]; then' >> ~/.bash_profile && \
    echo '    . ~/.bashrc' >> ~/.bash_profile && \
    echo 'fi' >> ~/.bash_profile
#   .bashrc
RUN echo '. $HOME/.venv/bin/activate' >> ~apl/.bashrc

# install python packages
COPY --chown=apl:apl . /app/ibet-Wallet-API
RUN cd /app/ibet-Wallet-API \
 && uv venv $UV_PROJECT_ENVIRONMENT \
 && uv sync --frozen --no-dev --no-install-project \
 && rm -f /app/ibet-Wallet-API/pyproject.toml \
 && rm -f /app/ibet-Wallet-API/uv.lock \
 && rm -rf /app/ibet-Wallet-API/tests/

FROM ubuntu:22.04 AS runner

# make application directory
RUN mkdir -p /app

# add apl user/group
RUN groupadd -g 1000 apl \
 && useradd -g apl -s /bin/bash -u 1000 -p apl apl \
 && echo 'apl ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers \
 && chown -R apl:apl /app \
 && mkdir /home/apl \
 && chown -R apl:apl /home/apl

# install packages
RUN apt-get update -q \
  && apt-get upgrade -qy \
  && apt-get install -y --no-install-recommends \
  ca-certificates \
  curl \
  libssl-dev \
  libpq-dev \
  language-pack-ja-base \
  language-pack-ja \
  jq \
  && apt-get clean \
  && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# copy python, dependencies and uv from builder stage
USER apl
COPY --from=builder --chown=apl:apl /home/apl/ /home/apl/
COPY --from=builder --chown=apl:apl /app/ibet-Wallet-API/ /app/ibet-Wallet-API/
COPY --from=builder --chown=apl:apl /usr/local/bin/uv /usr/local/bin/uv
COPY --from=builder --chown=apl:apl /usr/local/bin/uvx /usr/local/bin/uvx

ENV LANG=ja_JP.utf8
ENV UV_PROJECT_ENVIRONMENT="/home/apl/.venv"
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/ibet-Wallet-API

COPY run.sh healthcheck.sh /app/

EXPOSE 5000

CMD ["/app/run.sh"]
HEALTHCHECK --interval=10s CMD ["/app/healthcheck.sh"]
