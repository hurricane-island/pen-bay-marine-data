test-client:
	cd client && node index.js
.PHONY: test-client

template:
	cd client && node template.js
.PHONY: template

weather:
	@ balena build weather-stations --fleet weather --noparent-check
.PHONY: weather

deploy:
	@ balena deploy weather weather-stations
.PHONY: deploy
