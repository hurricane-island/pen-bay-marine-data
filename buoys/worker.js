const influxUrl =
      "https://us-east-1-1.aws.cloud2.influxdata.com/api/v2/write?orgId=500b0cdd30526848&bucket=buoys&precision=ms";

function timingSafeEqual(a, b) {
  if (a.length !== b.length) return false;
  let result = 0;
  for (let i = 0; i < a.length; i++) {
    result |= a.charCodeAt(i) ^ b.charCodeAt(i);
  }
  return result === 0;
}

function parseRecord(record, fields) {
  const time = new Date(record.time).getTime(); // Convert to milliseconds
  parts = record.vals.map((val, index) => {
    const fieldName = fields[index];
    return `${fieldName}=${val}`;
  });
  return `${parts.join(",")} ${time}`;
}

function parseCRMessage(body) {
    const startMarker = "application/octet-stream\r\n\r\n";
    const endMarker = "\r\n----CSIBoundary----";
    const startIndex = body.indexOf(startMarker);
    const endIndex = body.indexOf(endMarker, startIndex);
    
    if (startIndex === -1 || endIndex === -1) {
      const message = "Invalid format: CSI payload not found.";
      console.log(message);
      throw new Error(message);
    }
    
    const jsonString = body.substring(startIndex + startMarker.length, endIndex);
    const csiData = JSON.parse(jsonString);

    console.log('Data received:', csiData);
    const environment = csiData.head.environment;
    const station_name = environment.station_name.toLowerCase();
    const measurement = environment.table_name.toLowerCase();
    const fields = csiData.head.fields.map(field => field.name);
    const lines = csiData.data.map(record => `${measurement},device=${station_name} ` + parseRecord(record, fields)).join("\n");
    console.log('Parsed lines:', lines);
    return lines;
}

export default {
  async fetch(request, env) {
    if (request.method !== "POST") {
      return new Response("POST only", { status: 405 });
    }
    // const ttnAuthHeader = request.headers.get("X-TTN-Secret");
    // if (!ttnAuthHeader || !timingSafeEqual(ttnAuthHeader, env.WEBHOOK_SECRET)) {
    //   return new Response("Unauthorized", { status: 401 });
    // }
    try {
      const body = await request.text();
      const line = parseCRMessage(body);
      // return await fetch(influxUrl, {
      //   method: "POST",
      //   headers: {
      //     "Authorization": `Token ${env.INFLUX_WRITE}`,
      //     "Content-Type": "text/plain"
      //   },
      //   body: line
      // });
      return new Response("Ok", { status: 200 });
    } catch (err) {
      return new Response("Bad Request", { status: 400 });
    }
  }
};
