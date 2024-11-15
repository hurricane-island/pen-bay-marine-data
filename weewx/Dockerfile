FROM ubuntu:18.04
RUN apt update && apt install -y wget gpg
RUN wget -qO - https://weewx.com/keys.html | \
    gpg --dearmor --output /etc/apt/trusted.gpg.d/weewx.gpg
RUN echo "deb [arch=all] https://weewx.com/apt/python3 buster main" | \
    tee /etc/apt/sources.list.d/weewx.list
RUN apt update && apt install weewx
