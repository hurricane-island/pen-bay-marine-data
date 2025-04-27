FROM python:3-alpine AS weewx
RUN pip install --no-cache-dir \
    CT3 configobj Pillow pyserial pyusb overrides
RUN apk update && \
    apk add --no-cache git sqlite && \
    git clone https://github.com/weewx/weewx ~/weewx
FROM weewx
RUN git clone https://github.com/hurricane-island/weewx-influx.git ~/weewx-influx
COPY ./weewx.template.conf ./template.py /root/weewx-data/
COPY ./start.sh /
ENTRYPOINT [ "ash" ]
CMD [ "./start.sh" ]