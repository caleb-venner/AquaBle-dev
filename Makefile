.PHONY: setup dev dev-backend dev-frontend clean kill refresh

# Default variables
PYTHON := uv run python
UVICORN := uv run uvicorn
HOST := 0.0.0.0
PORT := 8000

setup:
	@echo "Installing backend dependencies..."
	uv sync --all-groups
	@echo "Installing frontend dependencies..."
	cd frontend && npm install

dev-backend:
	@echo "Starting backend service on $(HOST):$(PORT)..."
	mkdir -p .log
	export AQUA_BLE_MOCK=0 && $(UVICORN) src.aquable.service:app --host $(HOST) --port $(PORT) --reload --reload-dir src 2>&1 | tee .log/backend_$$(date +%Y%m%d_%H%M%S).log

dev-frontend:
	@echo "Starting frontend dev server..."
	cd frontend && npm run dev -- --host --force

dev:
	@echo "Starting both backend and frontend..."
	# Run both in parallel using make -j2
	$(MAKE) -j2 dev-backend dev-frontend

test:
	@echo "Running backend tests..."
	uv run pytest

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

kill:
	@echo "Killing backend and frontend processes..."
	-pkill -f "uvicorn src.aquable.service:app"
	-pkill -f "vite"
	-lsof -ti:$(PORT) | xargs kill -9 2>/dev/null || true
	-lsof -ti:5173 | xargs kill -9 2>/dev/null || true
	@echo "All clean."

refresh:
	$(MAKE) -j2 kill
	$(MAKE) -j2 setup
