FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN chmod +x start.sh

# Migrations run inside start.sh, deliberately NOT chained with '&&' — see the
# comment block there for why a database failure must not stop the port binding.
CMD ["./start.sh"]
