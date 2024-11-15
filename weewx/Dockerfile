FROM python:3-alpine
RUN pip install --no-cache-dir CT3 configobj Pillow pyserial pyusb && \
    apk add --no-cache git && \
    git clone https://github.com/weewx/weewx ~/weewx
COPY ./weewx.conf /root/weewx-data/
ENTRYPOINT [ "python3" ]
CMD [ "/root/weewx/src/weewxd.py" ]