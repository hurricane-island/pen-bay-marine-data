import Crypto from "crypto-js";
const {HmacSHA256, MD5, enc} = Crypto;
const {Base64} = enc;

const serviceID = process.env.XCLOUD_CLIENT_ID ?? "";
const secretKey = process.env.XCLOUD_SECRET_KEY ?? "";
const server = "https://cloud.xylem.com";
const basePath = "/xcloud/data-export";
const method = "GET";
const queryRange = [
    new Date("2024-07-14T00:00:00"),
    new Date("2024-07-16T00:00:00")
];

/**
 * Compose a valid HMAC key and output string to use as Authorization
 * header value. This only works for GET requests, which is
 * the only method supported by the partner data access API.
 */
function authHeader({
    method,
    dateHeader,
    path,
    data
}) {
    const message = [
        method, // httpMethod, 
        "", // contentType,
        dateHeader, // ISO timestamp
        path, // path
        "", // xCloud headers
        Object.keys(data).length !== 0 ? MD5(data).toString(Base64) : "", // contentMD5
        serviceID // partner API client ID
    ].join("\n");
    const hmac = HmacSHA256(message, Base64.parse(secretKey)).toString(Base64);
    return `xCloud ${btoa(serviceID)}:${hmac}`
}

/**
 * Query the production API for all sites associated with our
 * account. These contain display and location information that
 * can be used to construction queries for individual data streams.
 */
function getSites() {
    const path = `${basePath}/sites`
    const dateHeader = new Date().toISOString();
    return fetch(`${server}${path}`, { 
        method,
        headers: {
            Date: dateHeader,
            Authorization: authHeader({
                method,
                dateHeader,
                path,
                data: {}
            })
        }
    });
}

/**
 * Retrieve all datastreams associate with a single site. Note
 * that the base path is `site` instead of `sites`. Otherwise
 * returns a server error, rather than a 404 error.
 */
function getDatastreams(siteId) {
    const path = `${basePath}/site/${siteId}/datastreams`;
    const dateHeader = new Date().toISOString();
    return fetch(`${server}${path}`, { 
        method,
        headers: {
            Date: dateHeader,
            Authorization: authHeader({
                method,
                dateHeader,
                path,
                data: {}
            })
        }
    });
}

/**
 * Retrieve batch observations. Rather than using a path variable, 
 * this endpoint uses query parameters. You can get observations 
 * from multiple datastreams in a single request.
 */
function getObservations(
    datastreamIds,
    interval
) {
    const [from, until] = interval.map((each) => each.toISOString());
    const query = new URLSearchParams({
        from,
        until,
        datastreamIds
    });
    const path = `${basePath}/observations?${query.toString()}`;
    const now = new Date().toISOString();
    return fetch(`${server}${path}`, { 
        method,
        headers: {
            Date: now,
            Authorization: authHeader({
                method,
                dateHeader: now,
                path,
                data: {}
            })
        }
    });
}

console.info("Querying sites...")
const sitesResponse = await getSites();
const sites = await sitesResponse.json();
const [exampleSite] = sites;
// console.log(JSON.stringify(sites, null, 2));

console.info(`Querying datastreams at site ${exampleSite.id}...`);
const datastreamsResponse = await getDatastreams(exampleSite.id);
const datastreams = await datastreamsResponse.json();
const datastreamIds = datastreams.map((datastream) => {
    return datastream.id
});
// console.log(JSON.stringify(datastreams, null, 2));

console.info(`Querying observations...`);
const observationsResponse = await getObservations(
    datastreamIds.slice(0, 1),
    queryRange
);
const observations = await observationsResponse.json();
console.log(JSON.stringify(observations, null, 2));