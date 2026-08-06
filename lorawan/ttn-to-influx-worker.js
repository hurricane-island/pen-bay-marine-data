export default {
  async fetch(request, env) {
    if (request.method !== "POST") {
      return new Response("POST only", { status: 405 });
    }
    const body = await request.json();
    console.log("Received TTN message:", body);

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

    const line = `lora,device=${device} ${fields.join(",")} ${time}`;

    const influxUrl =
      "https://us-east-1-1.aws.cloud2.influxdata.com/api/v2/write?orgId=500b0cdd30526848&bucket=lorawan&precision=ms";

    return await fetch(influxUrl, {
      method: "POST",
      headers: {
        "Authorization": `Token ${env.INFLUX_WRITE}`,
        "Content-Type": "text/plain"
      },
      body: line
    });
  }
};