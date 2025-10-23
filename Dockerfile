FROM python:3.11-slim

WORKDIR /usr/src/app

COPY . .

EXPOSE 8080

CMD ["/bin/bash"]