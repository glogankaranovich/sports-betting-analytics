FROM public.ecr.aws/docker/library/python:3.12-slim

# Install dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY backend/ /app/
WORKDIR /app

# Set Python path
ENV PYTHONPATH=/app

# Default command (can be overridden)
CMD ["python", "-c", "print('Specify a command: props_collector, analysis_generator, or benny_trader')"]
