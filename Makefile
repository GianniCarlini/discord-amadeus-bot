.PHONY: venv install run docker-build docker-run fly-deploy logs

venv:
	python -m venv .venv

install:
	. .venv/bin/activate && pip install --upgrade pip && pip install -r requirements.txt

run:
	. .venv/bin/activate && python -m app.main

docker-build:
	docker build -t discord-amadeus-bot:latest .

docker-run:
	docker run --rm --env-file .env discord-amadeus-bot:latest

fly-deploy:
	flyctl deploy

logs:
	flyctl logs
