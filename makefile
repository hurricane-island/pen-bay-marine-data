test-client:
	cd client && node index.js

template:
	cd client && node template.js

weather:
	@ balena build weather-stations --fleet weather --noparent-check
.PHONY: weather

deploy:
	@ balena deploy weather weather-stations
.PHONY: deploy

.PHONY: test-client template