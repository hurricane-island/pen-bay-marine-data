FROM python:3-alpine AS weewx
RUN pip install --no-cache-dir \
    CT3 configobj Pillow pyserial pyusb
RUN apk add --no-cache git && \
    git clone https://github.com/weewx/weewx ~/weewx
FROM weewx
RUN pip install paho-mqtt
RUN git clone https://github.com/matthewwall/weewx-mqtt ~/weewx-mqtt
COPY ./weewx.template.conf ./template.py /root/weewx-data/
COPY ./start.sh /
ENTRYPOINT [ "ash" ]
CMD [ "./start.sh" ]