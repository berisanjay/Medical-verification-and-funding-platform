# Deployment Guide

Complete guide for deploying the Medical Document Verification System to production.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Local Development](#local-development)
3. [Production Deployment](#production-deployment)
   - [AWS Deployment](#aws-deployment)
   - [Google Cloud Platform](#google-cloud-platform)
   - [Azure Deployment](#azure-deployment)
   - [Docker Deployment](#docker-deployment)
4. [Database Setup](#database-setup)
5. [Environment Configuration](#environment-configuration)
6. [Security Best Practices](#security-best-practices)
7. [Monitoring & Logging](#monitoring--logging)
8. [Scaling Strategies](#scaling-strategies)

---

## Prerequisites

### Required Software
- Python 3.8+
- Node.js 14+
- MongoDB 4.4+
- Tesseract OCR
- Poppler
- Nginx (for production)
- PM2 (for Node.js process management)

### Required Accounts
- Cloud provider account (AWS/GCP/Azure)
- MongoDB Atlas account (for cloud database)
- Domain name (optional but recommended)
- SSL certificate (Let's Encrypt recommended)

---

## Local Development

### 1. Clone and Setup

```bash
git clone https://github.com/yourusername/medical-verification.git
cd medical-crowdfunding-verification
```

### 2. Install Dependencies

**Flask Backend**:
```bash
cd flask-backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
python -m spacy download en_core_web_sm
python -m spacy download en_core_sci_sm
```

**Node Backend**:
```bash
cd node-backend
npm install
```

### 3. Configure Environment

**Flask (.env)**:
```env
FLASK_ENV=development
FLASK_DEBUG=True
MONGO_URI=mongodb://localhost:27017/
DB_NAME=medical_verification
```

**Node (.env)**:
```env
PORT=3000
NODE_ENV=development
FLASK_API_URL=http://127.0.0.1:5000
```

### 4. Run Services

Terminal 1 - MongoDB:
```bash
mongod
```

Terminal 2 - Flask:
```bash
cd flask-backend
source venv/bin/activate
python app.py
```

Terminal 3 - Node:
```bash
cd node-backend
npm start
```

Terminal 4 - Frontend:
```bash
cd frontend/public
python -m http.server 8080
```

---

## Production Deployment

### AWS Deployment

#### 1. EC2 Instance Setup

**Launch EC2 Instance**:
- AMI: Ubuntu 22.04 LTS
- Instance Type: t3.medium (2 vCPU, 4 GB RAM)
- Security Group: Allow ports 22, 80, 443, 3000, 5000

**Connect to Instance**:
```bash
ssh -i your-key.pem ubuntu@your-ec2-ip
```

#### 2. Install Dependencies

```bash
# Update system
sudo apt-get update
sudo apt-get upgrade -y

# Install Python
sudo apt-get install python3-pip python3-venv -y

# Install Node.js
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install nodejs -y

# Install Tesseract
sudo apt-get install tesseract-ocr -y

# Install Poppler
sudo apt-get install poppler-utils -y

# Install Nginx
sudo apt-get install nginx -y

# Install PM2
sudo npm install -g pm2
```

#### 3. Setup Application

```bash
# Clone repository
git clone https://github.com/yourusername/medical-verification.git
cd medical-crowdfunding-verification

# Flask setup
cd flask-backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python -m spacy download en_core_web_sm
python -m spacy download en_core_sci_sm
deactivate

# Node setup
cd ../node-backend
npm install --production

# Create environment files
nano .env  # Add production settings
```

#### 4. Configure MongoDB

**Option A: Local MongoDB**:
```bash
sudo apt-get install mongodb -y
sudo systemctl start mongodb
sudo systemctl enable mongodb
```

**Option B: MongoDB Atlas (Recommended)**:
1. Create account at https://www.mongodb.com/cloud/atlas
2. Create cluster
3. Get connection string
4. Update MONGO_URI in .env

#### 5. Setup PM2

**Create ecosystem.config.js**:
```javascript
module.exports = {
  apps: [
    {
      name: 'flask-api',
      cwd: './flask-backend',
      script: 'venv/bin/python',
      args: 'app.py',
      env: {
        FLASK_ENV: 'production'
      }
    },
    {
      name: 'node-server',
      cwd: './node-backend',
      script: 'server.js',
      env: {
        NODE_ENV: 'production',
        PORT: 3000
      }
    }
  ]
};
```

**Start services**:
```bash
pm2 start ecosystem.config.js
pm2 save
pm2 startup
```

#### 6. Configure Nginx

**Create Nginx config** (`/etc/nginx/sites-available/medical-verification`):
```nginx
server {
    listen 80;
    server_name your-domain.com;

    # Frontend
    location / {
        root /home/ubuntu/medical-crowdfunding-verification/frontend/public;
        try_files $uri $uri/ /index.html;
    }

    # Node.js API
    location /api/ {
        proxy_pass http://localhost:3000/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    # Flask API
    location /flask/ {
        proxy_pass http://localhost:5000/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

**Enable site**:
```bash
sudo ln -s /etc/nginx/sites-available/medical-verification /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

#### 7. SSL Certificate (Let's Encrypt)

```bash
sudo apt-get install certbot python3-certbot-nginx -y
sudo certbot --nginx -d your-domain.com
sudo systemctl reload nginx
```

#### 8. Setup S3 for File Storage (Optional)

```bash
pip install boto3

# In Flask app
import boto3

s3 = boto3.client('s3',
    aws_access_key_id='YOUR_KEY',
    aws_secret_access_key='YOUR_SECRET'
)
```

---

### Google Cloud Platform

#### 1. Create VM Instance

```bash
gcloud compute instances create medical-verification \
    --zone=us-central1-a \
    --machine-type=e2-medium \
    --image-family=ubuntu-2204-lts \
    --image-project=ubuntu-os-cloud \
    --boot-disk-size=50GB
```

#### 2. Setup Similar to AWS

Follow AWS steps 2-7 with GCP-specific configurations.

#### 3. Use Cloud Storage

```bash
pip install google-cloud-storage

# In Flask app
from google.cloud import storage

client = storage.Client()
bucket = client.bucket('your-bucket-name')
```

---

### Azure Deployment

#### 1. Create App Service

Use Azure Portal or CLI:
```bash
az webapp create \
    --resource-group myResourceGroup \
    --plan myAppServicePlan \
    --name medical-verification \
    --runtime "NODE|18-lts"
```

#### 2. Deploy Application

```bash
az webapp deployment source config-local-git
git remote add azure <deployment-url>
git push azure main
```

---

### Docker Deployment

#### 1. Create Dockerfiles

**Flask Dockerfile** (`flask-backend/Dockerfile`):
```dockerfile
FROM python:3.10-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN python -m spacy download en_core_web_sm
RUN python -m spacy download en_core_sci_sm

COPY . .

EXPOSE 5000

CMD ["python", "app.py"]
```

**Node Dockerfile** (`node-backend/Dockerfile`):
```dockerfile
FROM node:18-alpine

WORKDIR /app

COPY package*.json ./
RUN npm ci --production

COPY . .

EXPOSE 3000

CMD ["node", "server.js"]
```

#### 2. Create docker-compose.yml

```yaml
version: '3.8'

services:
  mongodb:
    image: mongo:6
    restart: always
    volumes:
      - mongodb_data:/data/db
    environment:
      MONGO_INITDB_DATABASE: medical_verification

  flask-api:
    build: ./flask-backend
    restart: always
    depends_on:
      - mongodb
    environment:
      MONGO_URI: mongodb://mongodb:27017/
      DB_NAME: medical_verification
    ports:
      - "5000:5000"

  node-server:
    build: ./node-backend
    restart: always
    depends_on:
      - flask-api
    environment:
      FLASK_API_URL: http://flask-api:5000
      PORT: 3000
    ports:
      - "3000:3000"

  nginx:
    image: nginx:alpine
    restart: always
    depends_on:
      - node-server
    volumes:
      - ./frontend/public:/usr/share/nginx/html
      - ./nginx.conf:/etc/nginx/nginx.conf
    ports:
      - "80:80"
      - "443:443"

volumes:
  mongodb_data:
```

#### 3. Deploy

```bash
docker-compose up -d
docker-compose ps
docker-compose logs -f
```

---

## Database Setup

### MongoDB Atlas (Cloud)

1. **Create Cluster**: https://cloud.mongodb.com/
2. **Configure Network Access**: Add your IP
3. **Create Database User**
4. **Get Connection String**:
   ```
   mongodb+srv://username:password@cluster.mongodb.net/medical_verification
   ```
5. **Update .env**:
   ```env
   MONGO_URI=mongodb+srv://username:password@cluster.mongodb.net/
   DB_NAME=medical_verification
   ```

### Backup Strategy

```bash
# Create backup
mongodump --uri="your-mongo-uri" --out=/backup/$(date +%Y%m%d)

# Restore backup
mongorestore --uri="your-mongo-uri" /backup/20240120
```

---

## Environment Configuration

### Production Environment Variables

**Flask**:
```env
FLASK_ENV=production
FLASK_DEBUG=False
MONGO_URI=mongodb+srv://user:pass@cluster.mongodb.net/
DB_NAME=medical_verification
MAX_FILE_SIZE_MB=50
LOG_LEVEL=INFO
SECRET_KEY=your-secret-key-here
```

**Node**:
```env
NODE_ENV=production
PORT=3000
FLASK_API_URL=http://localhost:5000
MAX_FILE_SIZE_MB=50
```

---

## Security Best Practices

### 1. API Security

- **Rate Limiting**: Implement with Flask-Limiter
- **CORS**: Configure properly
- **Input Validation**: Sanitize all inputs
- **Authentication**: Add JWT tokens
- **HTTPS**: Always use SSL/TLS

### 2. File Upload Security

```python
# Validate file types
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'webp'}

# Scan for malware (optional)
import clamd
cd = clamd.ClamdUnixSocket()
scan_result = cd.scan(file_path)
```

### 3. Database Security

- Use strong passwords
- Enable authentication
- Limit network access
- Regular backups
- Encrypt sensitive data

### 4. Server Security

```bash
# Configure firewall
sudo ufw allow 22
sudo ufw allow 80
sudo ufw allow 443
sudo ufw enable

# Keep system updated
sudo apt-get update
sudo apt-get upgrade -y
```

---

## Monitoring & Logging

### 1. Application Logging

**Python (Flask)**:
```python
import logging
logging.basicConfig(
    filename='/var/log/medical-verification/flask.log',
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

**Node.js**:
```javascript
const winston = require('winston');
const logger = winston.createLogger({
  level: 'info',
  format: winston.format.json(),
  transports: [
    new winston.transports.File({ filename: 'error.log', level: 'error' }),
    new winston.transports.File({ filename: 'combined.log' })
  ]
});
```

### 2. PM2 Monitoring

```bash
pm2 monit
pm2 logs
pm2 describe app-name
```

### 3. Set Up Monitoring Tools

- **New Relic**: Application performance monitoring
- **Datadog**: Infrastructure monitoring
- **Sentry**: Error tracking
- **CloudWatch**: AWS monitoring

---

## Scaling Strategies

### 1. Horizontal Scaling

**Load Balancer Configuration**:
```nginx
upstream flask_backend {
    server 10.0.1.1:5000;
    server 10.0.1.2:5000;
    server 10.0.1.3:5000;
}

upstream node_backend {
    server 10.0.1.1:3000;
    server 10.0.1.2:3000;
}
```

### 2. Caching

**Redis Caching**:
```python
import redis
cache = redis.Redis(host='localhost', port=6379)

# Cache OCR results
cache.set(f'ocr:{file_hash}', text, ex=3600)
```

### 3. Background Jobs

**Celery for Async Processing**:
```python
from celery import Celery

app = Celery('tasks', broker='redis://localhost:6379')

@app.task
def process_document(file_path):
    # Heavy OCR and NLP processing
    pass
```

### 4. CDN for Static Assets

Use Cloudflare, CloudFront, or similar CDN for frontend files.

---

## Performance Optimization

1. **Database Indexing**:
```javascript
db.verifications.createIndex({ "created_at": -1 })
db.verifications.createIndex({ "final_status": 1 })
```

2. **Compress Responses**:
```python
from flask_compress import Compress
Compress(app)
```

3. **Connection Pooling**:
```python
mongo_client = MongoClient(MONGO_URI, maxPoolSize=50)
```

---

## Troubleshooting

### Common Issues

**Port already in use**:
```bash
sudo lsof -i :3000
sudo kill -9 <PID>
```

**Permission denied**:
```bash
sudo chown -R $USER:$USER /path/to/app
```

**MongoDB connection failed**:
```bash
sudo systemctl status mongodb
sudo systemctl restart mongodb
```

---

## Maintenance

### Regular Tasks

1. **Update Dependencies**: Monthly
2. **Review Logs**: Weekly
3. **Backup Database**: Daily
4. **Security Patches**: As released
5. **Performance Review**: Monthly

---

**Last Updated**: January 2024
