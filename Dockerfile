
FROM python:3.12-slim

# Installer les bibliothèques système requises pour Pillow
RUN apt-get update && apt-get install -y \
    gcc \
    libjpeg-dev \
    zlib1g-dev \
    libpng-dev \
    && rm -rf /var/lib/apt/lists/*

# Crée un dossier de travail
WORKDIR /app

# Copier les fichiers dans le conteneur
COPY . /app

# Installer les dépendances Python
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Démarrer le bot
CMD ["python", "bot.py"]
