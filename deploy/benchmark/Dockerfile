FROM python:3.12-slim

WORKDIR /app

# Install dependencies
RUN pip install --no-cache-dir httpx

# Copy benchmark files
COPY run_benchmark.py .
COPY test_jobs/ ./test_jobs/

# Create results directory
RUN mkdir -p /app/results

ENTRYPOINT ["python", "run_benchmark.py"]
CMD ["--runs", "3"]
