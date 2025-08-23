# Ollama Setup Guide

## What is Ollama?

Ollama is a local AI model runner that allows you to run large language models (LLMs) on your own machine without needing cloud APIs. This makes the AI Interview Screener more private, cost-effective, and faster.

## Installation

### 1. Install Ollama

**macOS:**
```bash
curl -fsSL https://ollama.ai/install.sh | sh
```

**Linux:**
```bash
curl -fsSL https://ollama.ai/install.sh | sh
```

**Windows:**
Download from [ollama.ai](https://ollama.ai/download)

### 2. Start Ollama

```bash
ollama serve
```

### 3. Pull a Model

Choose one of these models:

**Llama 2 (Recommended for interviews):**
```bash
ollama pull llama2
```

**Mistral (Good balance of speed and quality):**
```bash
ollama pull mistral
```

**CodeLlama (Good for technical interviews):**
```bash
ollama pull codellama
```

**Phi-2 (Fast and lightweight):**
```bash
ollama pull phi
```

## Configuration

### 1. Environment Variables

Update your `.env` file:

```env
# Ollama Configuration
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama2
```

### 2. Available Models

You can use any model available in Ollama. Popular choices:

- `llama2` - Good all-around model
- `mistral` - Fast and capable
- `codellama` - Great for technical questions
- `phi` - Lightweight and fast
- `llama2:13b` - Larger, more capable version
- `llama2:7b` - Smaller, faster version

### 3. Model Management

**List available models:**
```bash
ollama list
```

**Remove a model:**
```bash
ollama rm modelname
```

**Update a model:**
```bash
ollama pull modelname
```

## Testing Ollama

### 1. Test the API

```bash
curl -X POST http://localhost:11434/api/generate \
  -H "Content-Type: application/json" \
  -d '{
    "model": "llama2",
    "prompt": "Generate 3 interview questions for a software engineer position."
  }'
```

### 2. Test with Python

```python
import requests

response = requests.post('http://localhost:11434/api/generate', json={
    'model': 'llama2',
    'prompt': 'Generate 3 interview questions for a software engineer position.'
})

print(response.json()['response'])
```

## Performance Tips

### 1. Model Selection

- **For development/testing**: Use `phi` or `llama2:7b` (faster)
- **For production**: Use `llama2` or `mistral` (better quality)
- **For technical interviews**: Use `codellama`

### 2. Hardware Requirements

- **Minimum**: 8GB RAM, any modern CPU
- **Recommended**: 16GB+ RAM, GPU acceleration
- **Optimal**: 32GB+ RAM, NVIDIA GPU

### 3. GPU Acceleration

If you have an NVIDIA GPU:

```bash
# Install CUDA version
ollama pull llama2:13b-cuda

# Use CUDA model
OLLAMA_MODEL=llama2:13b-cuda
```

## Troubleshooting

### 1. Ollama Not Starting

```bash
# Check if Ollama is running
ps aux | grep ollama

# Restart Ollama
pkill ollama
ollama serve
```

### 2. Model Not Found

```bash
# List available models
ollama list

# Pull the model
ollama pull modelname
```

### 3. Out of Memory

- Use a smaller model (7B instead of 13B)
- Close other applications
- Increase swap space

### 4. Slow Responses

- Use a smaller model
- Enable GPU acceleration
- Check system resources

## Production Deployment

### 1. Local Deployment

For local deployment, ensure Ollama is running:

```bash
# Start Ollama as a service
sudo systemctl enable ollama
sudo systemctl start ollama
```

### 2. Cloud Deployment

For cloud deployment, you have several options:

**Option 1: Self-hosted Ollama**
- Deploy Ollama on a VPS
- Update `OLLAMA_BASE_URL` to your server URL

**Option 2: Use Ollama Cloud**
- Sign up at [ollama.ai](https://ollama.ai)
- Use cloud-hosted models

**Option 3: Alternative Local Models**
- Use other local model runners (LM Studio, etc.)
- Update the service to use different APIs

### 3. Environment Variables for Production

```env
# For local Ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama2

# For remote Ollama
OLLAMA_BASE_URL=https://your-ollama-server.com
OLLAMA_MODEL=llama2

# For Ollama Cloud
OLLAMA_BASE_URL=https://api.ollama.ai
OLLAMA_MODEL=llama2
```

## Benefits of Using Ollama

1. **Privacy**: All data stays on your machine
2. **Cost**: No API costs or usage limits
3. **Speed**: No network latency
4. **Reliability**: No dependency on external services
5. **Customization**: Can fine-tune models for specific use cases

## Next Steps

1. Install Ollama following the instructions above
2. Pull a model (recommend `llama2` to start)
3. Update your environment variables
4. Test the API endpoints
5. Deploy with your preferred model

Your AI Interview Screener is now powered by local AI models!
