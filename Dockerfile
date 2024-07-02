FROM python:3.12.1-slim AS build

RUN apt-get update -y \
 && apt-get install -y curl \
 && rm -rf /var/lib/apt/lists/*

RUN curl -sSLf https://rye-up.com/get | RYE_INSTALL_OPTION="--yes" bash

COPY . /app
WORKDIR /app

RUN /root/.rye/shims/rye build --wheel --clean

FROM python:3.12.1-slim

COPY --from=build /app/dist/*.whl /tmp/
RUN PYTHONDONTWRITEBYTECODE=1 pip install --no-cache-dir /tmp/*.whl

CMD ["dmserv", "bot"]
