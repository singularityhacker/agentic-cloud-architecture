FROM python:3.12-slim
WORKDIR /app
COPY . /app
RUN python -m pip install --no-cache-dir '.[hf]'
EXPOSE 8000
CMD ["python", "-m", "agent_arch.local_service"]
