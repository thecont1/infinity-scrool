The Docker base image is parameterized so that you can choose any Chrome version at build time. 

Additionally, there is optional support to point Selenium to a specific Chrome binary via an environment variable for runtime switching.

## Ways to choose any Chrome version dynamically

- **Docker (build-time parameter, recommended)**
  - I updated [infinity-scrool/Dockerfile](cci:7://file:///Users/home/DEV/MY%20PROJECTS/infinity-scrool/Dockerfile:0:0-0:0) to accept a build arg `CHROME_TAG`:

    - `FROM selenium/standalone-chrome:${CHROME_TAG}`
    - Default: `141.0`
  - **BUILD** for a specific Chrome version:
    ```bash
    # Apple Silicon, emulate amd64 (most reliable)
    docker buildx build --platform linux/amd64 \
      --build-arg CHROME_TAG=141.0 \
      -t infinity-scrool:chrome-141 .

    # Example: pull 142.0 or 140.0 instead
    docker buildx build --platform linux/amd64 \
      --build-arg CHROME_TAG=142.0 \
      -t infinity-scrool:chrome-142 .
    ```
  - **RUN**:
    ```bash
    docker run --rm -it --platform linux/amd64 \
      -v "$(pwd):/app" \
      infinity-scrool:chrome-141 \
      "https://www.justdial.com/Bangalore/Restaurants/" -n 5
    ```
  - Please note:
    - Valid tags follow Selenium’s image tags, typically full Chrome major.minor, e.g. `141.0`, `142.0`. See tags at Docker Hub: `selenium/standalone-chrome`.
    - If a multi-arch manifest exists, you can omit `--platform`. Otherwise, keep `--platform linux/amd64` on Apple Silicon.

- **Chrome for Testing (runtime binary switch, no rebuild)**
  - Download the desired Chrome version binary from Chrome for Testing.
  - Run your script pointing Selenium to that binary (Selenium Manager will fetch a matching driver):
    ```python
    # add temporarily in setup_driver(), before driver init:
    chrome_options.binary_location = "/absolute/path/to/Google Chrome for Testing"
    ```
