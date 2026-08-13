const EXAMPLE_CSI_PAYLOAD = `
message: Received body: ----CSIBoundary--
Content-Disposition: form-data; name="NULL";filename=Diagnostics3.dat
Content-Type: application/octet-stream

{"head": {"transaction": 0,"signature": 30374,"environment":  {"station_name":  "bench_test","table_name":  "Diagnostics","model":  "CR300","serial_no":  "36592","os_version":  "CR300-CELL210.11.3.0","prog_name":  "CPU:wynken.3b650ccf572b3cea8b6c3e238ea7078c.dld"},"fields":  [{"name":  "BatteryVoltage","type":  "xsd:float","units":  "Volts","process":  "Smp","settable":  false},{"name":  "RSSI","type":  "xsd:float","process":  "Smp","settable":  false}]},"data": [{"time":  "2026-08-13T16:31:00","vals": [13.48,"NAN"]}]}
----CSIBoundary----
`

const influxUrl =
      "https://us-east-1-1.aws.cloud2.influxdata.com/api/v2/write?orgId=500b0cdd30526848&bucket=test&precision=ms";

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
  const parts = record.vals.filter(val => val !== "NAN").map((val, index) => {
    return `${fields[index]}=${val}`;
  });
  return `${parts.join(",")} ${time}`;
}

function parseCRMessage(body) {
    const startMarker = "application/octet-stream";
    const endMarker = "----CSIBoundary----";
    const startIndex = body.indexOf(startMarker);
    const endIndex = body.indexOf(endMarker, startIndex);
    
    if (startIndex === -1 || endIndex === -1) {
      const message = "Invalid format: CSI payload not found.";
      throw new Error(message);
    }
    
    const jsonString = body.substring(startIndex + startMarker.length, endIndex).trim();
    const csiData = JSON.parse(jsonString);
    const environment = csiData.head.environment;
    const station_name = environment.station_name.toLowerCase();
    const measurement = environment.table_name.toLowerCase();
    const fields = csiData.head.fields.map(field => field.name);
    const lines = csiData.data.map(record => `${measurement},device=${station_name} ` + parseRecord(record, fields)).join("\n");
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
      const result = await fetch(influxUrl, {
        method: "POST",
        headers: {
          "Authorization": `Token ${env.INFLUX_WRITE}`,
          "Content-Type": "text/plain"
        },
        body: line
      });
      return new Response("Ok", { status: 200 });
    } catch (err) {
      console.error("Error processing request:", err);
      return new Response("Bad Request", { status: 400 });
    }
  }
};

// parseCRMessage(EXAMPLE_CSI_PAYLOAD);
