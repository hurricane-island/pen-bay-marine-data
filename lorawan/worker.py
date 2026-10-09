from secrets import compare_digest
from datetime import datetime
from typing import Optional

INFLUX_URL = "https://us-east-1-1.aws.cloud2.influxdata.com/api/v2/write?orgId=500b0cdd30526848&bucket=lorawan&precision=ms";


def parse_ttn_message(body: dict):
    device: str = body["end_device_ids"]["device_id"]
    decoded: dict = body["uplink_message"]["decoded_payload"]
    metadata: dict = body["uplink_message"]["rx_metadata"][0]
    broker: Optional[dict] = metadata.get("packet_broker", None)
    message_id = None if broker is None else broker.message_id

    _time = metadata.time
    time = new Date(metadata.time).getTime(); // Convert to milliseconds
    received_at = new Date(metadata.received_at).getTime(); // Convert to milliseconds

    del metadata["gateway_ids"]
    del metadata["packet_broker"]
    del metadata["uplink_token"]
    del metadata["time"]
    del metadata["received_at"]

    all_data = {
        **decoded,
        **metadata,
        "message_id": received_at, 
        "received_at": received_at
    }
    
    
    fields = []
    for key, value in all_data.items():
      if (isinstance(value, float)):
        fields.append(f"{key}={value}")
      elif isinstance(value, bool):
        fields.push(f"{key}={value}")
      else:
        fields.push(f"{key}='{String(value).replace(/"/g, '\\"')}'"`)
    
    line = f"signal,device={device} {",".join(fields)} {time}"
    return line


export default {
  async fetch(request, env) {
    if (request.method !== "POST") {
      return new Response("POST only", { status: 405 });
    }
    const ttnAuthHeader = request.headers.get("X-TTN-Secret");
    if (!ttnAuthHeader || !timingSafeEqual(ttnAuthHeader, env.WEBHOOK_SECRET)) {
      return new Response("Unauthorized", { status: 401 });
    }
    try {
      const body = await request.json();
      const line = parseTTNMessage(body);
      return await fetch(influxUrl, {
      method: "POST",
      headers: {
        "Authorization": `Token ${env.INFLUX_WRITE}`,
        "Content-Type": "text/plain"
      },
      body: line
    });
    } catch (err) {
      return new Response("Bad Request", { status: 400 });
    }
  }
};
