FROM ubuntu:18.04
RUN apt update && \
    apt install -y make gcc wget
RUN wget https://github.com/Lora-net/sx1302_hal/archive/V2.0.1.tar.gz && \
    tar -zxvf V2.0.1.tar.gz && \
    cd sx1302_hal-2.0.1 && \
    make && \
    cd packet_forwarder && \
    cp global_conf.json.sx1250.US915.USB global_conf.json
WORKDIR /sx1302_hal-2.0.1/packet_forwarder
CMD ["./lora_pkt_fwd"]