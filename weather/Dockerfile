FROM python:3-alpine AS weewx
RUN apk update && \
    apk add --no-cache git sqlite && \
    git clone https://github.com/weewx/weewx /root/weewx && \
    git clone https://github.com/hurricane-island/weewx-influx.git /root/weewx-influx && \
    pip install --no-cache-dir /root/weewx overrides
FROM weewx
RUN mkdir -p /root/weewx-data/bin/user && \
    cp /root/weewx-influx/bin/user/influx.py /root/weewx-data/bin/user/influx.py
COPY ./weewx.template.conf ./template.py /root/weewx-data/
COPY ./start.sh /
ENTRYPOINT [ "ash" ]
CMD [ "./start.sh" ]