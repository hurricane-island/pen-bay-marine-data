const influxUrl =
      "https://us-east-1-1.aws.cloud2.influxdata.com/api/v2/write?orgId=500b0cdd30526848&bucket=lorawan&precision=ms";

function timingSafeEqual(a, b) {
  if (a.length !== b.length) return false;
  let result = 0;
  for (let i = 0; i < a.length; i++) {
    result |= a.charCodeAt(i) ^ b.charCodeAt(i);
  }
  return result === 0;
}

function parseTTNMessage(body) {
    const device = body.end_device_ids.device_id;
    const decoded = body.uplink_message.decoded_payload;
    const metadata = body.uplink_message.rx_metadata[0]
    const message_id = metadata.packet_broker.message_id

    const time = new Date(metadata.time).getTime(); // Convert to milliseconds
    const received_at = new Date(metadata.received_at).getTime(); // Convert to milliseconds

    delete metadata.gateway_ids
    delete metadata.packet_broker
    delete metadata.uplink_token
    delete metadata.time
    delete metadata.received_at

    const all_data = {...decoded, ...metadata, message_id, received_at}
    
    // Build Influx line protocol
    let fields = [];
    for (const [key, value] of Object.entries(all_data)) {
      if (typeof value === "number") {
        fields.push(`${key}=${value}`);
      } else if (typeof value === "boolean") {
        fields.push(`${key}=${value}`);
      } else {
        fields.push(`${key}="${String(value).replace(/"/g, '\\"')}"`);
      }
    }
    const line = `signal,device=${device} ${fields.join(",")} ${time}`;
    return line
}

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