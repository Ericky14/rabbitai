.PHONY: up down setup logs clean dev watch ui test test-upload frontend-install grafana-debug grafana-reload

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

grafana-debug:
	@echo "Checking Grafana dashboard loading..."
	@echo "1. Grafana logs:"
	docker-compose logs grafana | tail -20
	@echo "\n2. Dashboard files:"
	ls -la monitoring/grafana/dashboards/
	@echo "\n3. Provisioning config:"
	cat monitoring/grafana/provisioning/dashboards/dashboard.yml
	@echo "\n4. Testing Grafana API:"
	curl -s -u admin:admin123 http://localhost:3001/api/search | jq '.' || echo "Grafana not responding"

grafana-reload:
	@echo "Restarting Grafana to reload dashboards..."
	docker-compose restart grafana
	@echo "Waiting for Grafana to start..."
	sleep 10
	@echo "Checking dashboards:"
	curl -s -u admin:admin123 http://localhost:3001/api/search | jq '.'


metrics-debug:
	@echo "=== Checking metrics endpoints ==="
	@echo "1. AI Upscaler API metrics:"
	curl -s http://localhost:8080/metrics | grep -E "(api_requests|file_uploads|analytics)" || echo "No metrics found"
	@echo "\n2. Analytics Service metrics:"
	curl -s http://localhost:8081/metrics | grep -E "analytics_events" || echo "No analytics metrics found"
	@echo "\n3. Prometheus targets:"
	curl -s http://localhost:9090/api/v1/targets | jq '.data.activeTargets[] | {job: .labels.job, health: .health, lastError: .lastError}' || echo "Prometheus not responding"
	@echo "\n4. Sample queries:"
	curl -s "http://localhost:9090/api/v1/query?query=api_requests_total" | jq '.data.result' || echo "No API request data"

test-metrics:
	@echo "Testing metrics generation..."
	curl -v -X POST "http://localhost:8080/upscale" -F "file=@test.jpg" || echo "Upload test failed"
	@echo "\nWaiting 5 seconds for metrics..."
	sleep 5
	@echo "Checking metrics:"
	curl -s http://localhost:8080/metrics | grep api_requests_total


