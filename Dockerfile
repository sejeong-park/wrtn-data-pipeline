FROM python:3.12-slim

RUN apt-get update && apt-get install -y \
    libglib2.0-0 \
    libnss3 \
    libgconf-2-4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libexpat1 \
    libfontconfig1 \
    libgbm1 \
    libgtk-3-0 \
    libpango-1.0-0 \
    libxcomposite1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxrandr2 \
    libxkbcommon0 \
    libasound2 \
    libcairo2 \
    libgdk-pixbuf2.0-0 \
    libnspr4 \
    libx11-6 \
    libxcursor1 \
    libxss1 \
    libxtst6 \
    && rm -rf /var/lib/apt/lists/*


WORKDIR /app

RUN pip install poetry

COPY pyproject.toml poetry.lock ./

RUN poetry install --no-root

RUN poetry run playwright install

RUN chmod +x /root/.cache/ms-playwright/chromium-*/chrome-linux/chrome

RUN apt-get update && apt-get install -y curl \
    && curl -o /usr/local/bin/wait-for-it.sh https://raw.githubusercontent.com/vishnubob/wait-for-it/master/wait-for-it.sh \
    && chmod +x /usr/local/bin/wait-for-it.sh

COPY . .

CMD ["/usr/local/bin/wait-for-it.sh", "db:3306", "--", "poetry", "run", "python", "app/main.py"]
