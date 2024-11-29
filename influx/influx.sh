curl \
  --request POST \
  --header "Authorization: Token $INFLUX_SERVICE_USER" \
  --header "Content-Encoding: identity" \
  --data-binary $'temperature value=0\nhumidity value=40' \
  "https://$INFLUX_HOST/api/v2/write?org=Research&bucket=weather&precision=ms"