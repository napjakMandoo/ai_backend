FROM python:3.12

RUN apt-get update && apt-get install -y --no-install-recommends pkg-config libcairo2-dev gobject-introspection libgirepository1.0-dev  && rm -rf /var/lib/apt/lists/*

WORKDIR /usr/src/app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src ./src
ENV PYTHONPATH="/usr/src/app:/usr/src/app/src"

ENTRYPOINT [ "python", "-u" ]
