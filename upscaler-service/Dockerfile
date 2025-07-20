FROM python:3.9-slim

WORKDIR /app

# Install system dependencies with optimizations
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libglib2.0-dev \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    build-essential \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies with optimizations
RUN pip install --no-cache-dir --upgrade pip

# Install PyTorch CPU version with optimizations
RUN pip install --no-cache-dir torch==2.0.1+cpu torchvision==0.15.2+cpu --index-url https://download.pytorch.org/whl/cpu

# Install other requirements
RUN pip install --no-cache-dir -r requirements.txt

# Copy weights directory
COPY weights/ /app/weights/

# Copy application code
COPY . .

# Set environment variables for optimization
ENV OMP_NUM_THREADS=2
ENV MKL_NUM_THREADS=2
ENV NUMEXPR_NUM_THREADS=2
ENV OPENBLAS_NUM_THREADS=2

EXPOSE 8083

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8083", "--workers", "1"]
