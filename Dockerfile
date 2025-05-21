FROM python:3.10-slim

WORKDIR /app

COPY pyproject.toml poetry.lock* /app/
RUN pip install poetry
RUN poetry install --no-root

COPY . /app

EXPOSE 8000

CMD ["poetry", "run", "python", "-m", "src.topwr_ml.chatbot.main"]