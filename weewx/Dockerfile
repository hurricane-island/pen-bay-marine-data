FROM python:3-alpine
RUN pip install --no-cache-dir \
    CT3 configobj Pillow pyserial pyusb paho-mqtt
RUN apk add --no-cache git && \
    git clone https://github.com/weewx/weewx ~/weewx && \
    git clone https://github.com/matthewwall/weewx-mqtt ~/weewx-mqtt
COPY ./weewx.conf /root/weewx-data/
# RUN python3 /root/weewx/src/weectl.py extension install -y /root/weewx-mqtt
ENTRYPOINT [ "ash" ]
# ENTRYPOINT [ "python3" ]
# CMD [ "/root/weewx/src/weewxd.py" ]