data/locations.csv:
	cd client && node geojons-to-csv.js

test-client:
	cd client && node index.js

template:
	cd client && node template.js

.PHONY: test-client template