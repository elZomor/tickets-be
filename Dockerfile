FROM python:3.12-alpine

RUN apk update && apk add postgresql-client

RUN mkdir -p /app

WORKDIR /app

COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

ENTRYPOINT ["/app/entrypoint.sh"]