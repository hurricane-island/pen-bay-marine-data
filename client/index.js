import Crypto from "crypto-js";
const {HmacSHA256, MD5, enc} = Crypto;
const {Base64} = enc;

const serviceID = process.env.XCLOUD_CLIENT_ID ?? "";
const secretKey = process.env.XCLOUD_SECRET_KEY ?? "";
const dateHeader = new Date().toISOString()
const data = {};

const message = [
    "GET", // httpMethod, 
    "", // contentType,
    dateHeader, // ISO Datetime
    "/sites", // path
    "", // xCloud headers
    Object.keys(data).length !== 0 ? MD5(data).toString(Base64) : "", // contentMD5
    serviceID // client ID
].join("\n");

const hmac = HmacSHA256(message, Base64.parse(secretKey)).toString(Base64);
const headers = {
    Date: dateHeader,
    Authorization: `xCloud ${btoa(serviceID)}:${hmac}`
}
let response = await fetch(`https://cloud.xylem.com/v0.1-beta/sites/`, { headers })
let result = await response.json()

console.log({headers, result})