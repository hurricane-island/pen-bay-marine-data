FROM python:3-alpine AS weewx
WORKDIR /root
RUN apk update && \
    apk add --no-cache git sqlite && \
    git clone https://github.com/weewx/weewx weewx/ && \
    git clone https://github.com/hurricane-island/weewx-influx.git weewx-influx/ && \
    pip install --no-cache-dir weewx/ overrides influxdb3-python
FROM weewx
WORKDIR /root
RUN mkdir -p weewx-data/bin/user && \
    cp weewx-influx/bin/user/influx.py weewx-data/bin/user/influx.py
COPY ./weewx.template.conf ./template.py weewx-data/
COPY ./start.sh ./
ENTRYPOINT [ "ash" ]
CMD [ "./start.sh" ]