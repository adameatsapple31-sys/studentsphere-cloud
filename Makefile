.PHONY: dev test build stop logs

dev:
	docker compose up --build

test:
	cd backend && pytest -q

build:
	cd frontend && npm install && npm run build

stop:
	docker compose down

logs:
	docker compose logs -f api web

