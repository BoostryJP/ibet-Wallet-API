FROM ghcr.io/astral-sh/uv:0.11.29@sha256:eb2843a1e56fd9e30c7276ce1a52cba86e64c7b385f5e3279a0e08e02dd058fc AS uv

FROM ubuntu:26.04@sha256:3131b4cc82a783df6c9df078f86e01819a13594b865c2cad47bd1bca2b7063bb AS builder

ENV PYTHON_VERSION=3.14.6
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
ENV UV_PROJECT_ENVIRONMENT="/home/apl/.venv"

# make application directory
RUN mkdir -p /app

# add apl user/group
RUN userdel -r ubuntu \
 && groupadd -g 1000 apl \
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
COPY --from=uv /uv /uvx /usr/local/bin/

# prepare Python install scope
ENV UV_PYTHON_INSTALL_DIR="/home/apl/.local/share/uv/python"
USER apl

# install Python
RUN uv python install $PYTHON_VERSION

# prepare venv
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
 && UV_MALWARE_CHECK=1 uv sync --frozen --no-install-project --no-dev \
 && PYTHON_BIN="$(uv python find $PYTHON_VERSION)" \
 && PYTHON_ROOT="$(dirname "$(dirname "$PYTHON_BIN")")" \
 && rm -f "$PYTHON_ROOT"/bin/pip "$PYTHON_ROOT"/bin/pip3 "$PYTHON_ROOT"/bin/pip3.* \
 && rm -rf "$PYTHON_ROOT"/lib/python*/site-packages/pip "$PYTHON_ROOT"/lib/python*/site-packages/pip-*.dist-info \
 && rm -rf /home/apl/.cache/uv \
 && rm -f /app/ibet-Wallet-API/pyproject.toml \
 && rm -f /app/ibet-Wallet-API/uv.lock \
 && rm -rf /app/ibet-Wallet-API/tests/

FROM ubuntu:26.04@sha256:3131b4cc82a783df6c9df078f86e01819a13594b865c2cad47bd1bca2b7063bb AS runner

# make application directory
RUN mkdir -p /app

# add apl user/group
RUN userdel -r ubuntu \
 && groupadd -g 1000 apl \
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
COPY --from=builder --chown=apl:apl /home/apl/.bash_profile /home/apl/.bash_profile
COPY --from=builder --chown=apl:apl /home/apl/.bashrc /home/apl/.bashrc
COPY --from=builder --chown=apl:apl /home/apl/.local/share/uv/python/ /home/apl/.local/share/uv/python/
COPY --from=builder --chown=apl:apl /home/apl/.venv/ /home/apl/.venv/
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
