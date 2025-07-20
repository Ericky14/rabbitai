.PHONY: up down setup logs clean dev watch ui test test-upload frontend-install

up:
	docker-compose up -d
	chmod +x scripts/setup-localstack.sh
	echo "Running LocalStack setup..."
	./scripts/setup-localstack.sh
	echo "Waiting for services to stabilize..."
	sleep 5
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

urls:
	@echo "RabbitMQ Management UI: http://localhost:15672"
	@echo "Username: admin, Password: admin123"
	@echo "Frontend UI: http://localhost:3000"
	@echo "Grafana UI: http://localhost:3001"
	@echo "Username: admin, Password: admin123"

frontend-install:
	cd frontend && pnpm install

frontend-dev:
	cd frontend && pnpm dev

frontend-build:
	cd frontend && pnpm build

test:
	@echo "Testing AI Upscaler API endpoints..."
	@echo "1. Health check:"
	curl -s http://localhost:8080/health | jq '.' || curl -s http://localhost:8080/health
	@echo "\n2. Root endpoint:"
	curl -s http://localhost:8080/ | jq '.' || curl -s http://localhost:8080/
	@echo "\n3. Metrics endpoint:"
	curl -s http://localhost:8080/metrics | head -5
	@echo "\n4. Upload test (requires test image):"
	@if [ -f "test.jpg" ]; then \
		curl -s -X POST "http://localhost:8080/upscale" -F "file=@test.jpg" | jq '.' || curl -s -X POST "http://localhost:8080/upscale" -F "file=@test.jpg"; \
	elif [ -f "Fallout.jpg" ]; then \
		curl -s -X POST "http://localhost:8080/upscale" -F "file=@Fallout.jpg" | jq '.' || curl -s -X POST "http://localhost:8080/upscale" -F "file=@Fallout.jpg"; \
	else \
		echo "No test image found (test.jpg or Fallout.jpg)"; \
	fi

test-upload:
	@echo "Testing file upload with Fallout.jpg..."
	curl -v -X POST "http://localhost:8080/upscale" -F "file=@Fallout.jpg"

