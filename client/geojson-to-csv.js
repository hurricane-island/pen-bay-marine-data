import {readFileSync, writeFileSync} from "fs";

const geojsonFile = "../data/locations.geojson";
const csvFile = "../data/locations.csv";
const text = readFileSync(geojsonFile, "utf8");
const data = JSON.parse(text);
const points = data.features.filter((feature) => {
    return feature.geometry.type === "Point"
});

const lines = points.map((point) => {
    const name = point.properties.title;
    const longitude = point.geometry.coordinates[1];
    const latitude = point.geometry.coordinates[0]
    return `${name},${longitude},${latitude}`
})
const output = lines.join("\n");
writeFileSync(csvFile, output, "utf8");

