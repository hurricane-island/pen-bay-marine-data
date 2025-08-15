weather:
	@ balena build --fleet weather
.PHONY: weather

deploy:
	@ balena deploy weather
.PHONY: deploy

develop:
	@ balena deploy weather-dev --build --nocache
.PHONY: develop
