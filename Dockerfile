FROM debian

RUN apt-get update -y \
 && apt install -y curl \
 && rm -rf /var/lib/apt/lists/*

RUN curl -sSf https://rye-up.com/get | RYE_INSTALL_OPTION="--yes" bash

COPY . /app
WORKDIR /app

RUN /root/.rye/shims/rye sync

CMD ["/root/.rye/shims/rye", "run", "dmserv", "bot"]
