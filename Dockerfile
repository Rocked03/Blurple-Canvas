FROM python:3.10
LABEL authors="Rocked03"

# Set the working directory to /app
WORKDIR /app

# Copy only the requirements file initially to leverage Docker cache
COPY requirements.txt .

# Create a virtual environment and activate it
RUN python -m venv venv
ENV PATH="/app/venv/bin:$PATH"

# Upgrade pip inside the virtual environment
RUN pip install --upgrade pip

# Install dependencies
RUN pip install -r requirements.txt
RUN pip install "discord.py[voice] @ git+https://github.com/rapptz/discord.py"  # Newer version to support bot banner editing

# Copy the rest of the application code
COPY . .

# Set the command to run your Python script
CMD ["python", "main.py"]
