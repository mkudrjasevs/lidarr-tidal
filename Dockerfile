FROM python:3.10-alpine

WORKDIR /app
RUN apk add --no-cache libffi libffi-dev curl rust cargo build-base openssl-dev bsd-compat-headers bash
COPY src/requirements.txt ./src/requirements.txt
RUN python -m pip install -r src/requirements.txt
COPY . .
EXPOSE 8081
CMD ["/app/run.sh"]
