data/locations.csv:
	cd client && node geojons-to-csv.js

test-client:
	cd client && node index.js

template:
	cd client && node template.js

weewx:
	@ balena build weewx -f weather
.PHONY: weewx

deploy:
	@ balena deploy weather weewx
.PHONY: deploy

.PHONY: test-client template