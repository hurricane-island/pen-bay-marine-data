data/locations.csv:
	cd client && node geojons-to-csv.js

test-client:
	cd client && node index.js

template:
	cd client && node template.js

weewx:
	@ docker-compose build weewx
.PHONY: weewx

.PHONY: test-client template