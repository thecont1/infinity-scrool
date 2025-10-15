# Dockerfile to run infinity_scrool.py against Chrome 141 on Apple Silicon
# Uses amd64 Selenium standalone Chrome image (emulated on Apple Silicon)

# Pin to Chrome line (platform is selected at build/run time)
ARG CHROME_TAG=141.0
FROM selenium/standalone-chrome:${CHROME_TAG}

USER root

# Install Python and pip
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       python3 python3-pip python3-venv \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy only requirements first to leverage Docker layer caching
COPY requirements.txt ./
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy the rest of the project
COPY . .

# Optional: silence Selenium Manager telemetry (avoids plausible.io logs)
ENV SE_MANAGER_TELEMETRY=0

# Default entrypoint: run the scraper; pass URL and flags via `docker run ...`
ENTRYPOINT ["python3", "infinity_scrool.py"]
