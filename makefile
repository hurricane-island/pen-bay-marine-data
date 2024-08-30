data/locations.csv:
	cd client && node geojons-to-csv.js

test-client:
	cd client && node index.js

.PHONY: test-client