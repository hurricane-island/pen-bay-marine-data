FROM grafana/alloy:latest AS alloy
COPY ./config.alloy /etc/alloy/config.alloy
CMD ["run", "--server.http.listen-addr=0.0.0.0:12345", "/etc/alloy/config.alloy"]