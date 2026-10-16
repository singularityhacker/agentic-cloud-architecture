FROM python:3.12-slim
WORKDIR /app
COPY . /app
RUN python -m pip install --no-cache-dir '.[hf,strands]'
EXPOSE 8000
CMD ["python", "-m", "agent_arch.local_service"]
