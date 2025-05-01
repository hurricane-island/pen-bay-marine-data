template:
	cd client && node template.js
.PHONY: template

weather:
	@ balena build --fleet weather
.PHONY: weather

deploy:
	@ balena deploy weather
.PHONY: deploy

develop:
	@ balena deploy weather-dev --build --nocache
.PHONY: develop
