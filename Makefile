.PHONY: up down setup logs clean dev watch

up:
	docker-compose up -d
	chmod +x scripts/setup-localstack.sh
	echo "Running LocalStack setup..."
	./scripts/setup-localstack.sh
	echo "Setup complete!"

down:
	docker-compose down

setup: up

logs:
	docker-compose logs -f

clean:
	docker-compose down -v
	docker system prune -f

dev:
	docker-compose up --build

watch:
	docker-compose up --watch

ui:
	@echo "RabbitMQ Management UI: http://localhost:15672"
	@echo "Username: admin, Password: admin123"


