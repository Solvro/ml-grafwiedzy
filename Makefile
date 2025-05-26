# Run neo4j
run-neo4j:
	docker-compose up --build -d neo4j

# Run the chatbot rag
run-rag:
	docker-compose run --build --rm rag

# Run the pipe script
run-pipe:
	docker-compose run --build --rm rag poetry run python -m src.topwr_ml.pipe.main

# Stop all services
stop:
	docker-compose down

# Rebuild the app container
rebuild:
	docker-compose build --no-cache

# Clear volumes (neo4j data)
clear-volumes:
	docker-compose down -v
