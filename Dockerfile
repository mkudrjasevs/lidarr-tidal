FROM python:alpine

WORKDIR /app
RUN apk add --no-cache curl build-base openssl-dev bsd-compat-headers bash
COPY python/requirements.txt ./python/requirements.txt
RUN python -m pip install -r python/requirements.txt
COPY . .
EXPOSE 8080
CMD ["/app/run.sh"]
