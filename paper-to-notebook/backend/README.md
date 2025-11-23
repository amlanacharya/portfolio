# Paper to Notebook - Backend API

FastAPI backend that converts research paper PDFs into executable Jupyter notebooks using Google's Gemini LLM.

## 🚀 Features

- Single Python file architecture (easy deployment)
- FastAPI with automatic OpenAPI docs
- Server-Sent Events (SSE) for real-time progress streaming
- LLM-powered notebook generation with 4-step pipeline
- CORS enabled for frontend integration
- Railway-ready deployment

## 📋 Requirements

- Python 3.9 or higher
- Gemini API key from [Google AI Studio](https://aistudio.google.com/apikey)

## 🛠️ Installation

### 1. Clone or navigate to the backend folder

```bash
cd backend
```

### 2. Create a virtual environment (recommended)

```bash
python -m venv venv

# On macOS/Linux:
source venv/bin/activate

# On Windows:
venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Set up environment variables (optional)

```bash
cp .env.example .env
# Edit .env and add your Gemini API key
```

## 🏃 Running Locally

### Option 1: Using Python directly

```bash
python app.py
```

The API will be available at `http://localhost:8000`

### Option 2: Using uvicorn (more control)

```bash
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

### Option 3: With custom port

```bash
PORT=3001 python app.py
```

## 📚 API Documentation

Once running, visit:

- **Interactive API docs (Swagger)**: http://localhost:8000/docs
- **Alternative docs (ReDoc)**: http://localhost:8000/redoc

## 🔌 API Endpoints

### `GET /`
Root endpoint with API information.

**Response:**
```json
{
  "message": "Paper to Notebook API",
  "version": "2.0",
  "endpoints": {
    "generate": "/api/generate",
    "download": "/api/download/{job_id}",
    "health": "/health"
  }
}
```

---

### `POST /api/generate`
Generate a Jupyter notebook from a PDF.

**Parameters:**
- `file` (form-data): PDF file (max 30MB)
- `api_key` (form-data): Gemini API key

**Response:** Server-Sent Events (SSE) stream with:
- `event: thinking` - LLM thinking process
- `event: progress` - Pipeline progress updates
- `event: draft_ready` - Draft notebook ready for download
- `event: complete` - Final notebook ready
- `event: error` - Error occurred

**Example using curl:**
```bash
curl -X POST http://localhost:8000/api/generate \
  -F "file=@paper.pdf" \
  -F "api_key=YOUR_GEMINI_API_KEY"
```

---

### `GET /api/download/{job_id}`
Download generated notebook.

**Parameters:**
- `job_id` (path): Job ID from generation response

**Response:** `.ipynb` file download

**Example:**
```bash
curl -O http://localhost:8000/api/download/abc123def456
```

---

### `GET /health`
Health check endpoint.

**Response:**
```json
{
  "status": "ok",
  "version": "2.0"
}
```

## 🧪 Testing the API

### Using curl:

```bash
# Test health endpoint
curl http://localhost:8000/health

# Generate notebook
curl -X POST http://localhost:8000/api/generate \
  -F "file=@your_paper.pdf" \
  -F "api_key=YOUR_API_KEY" \
  --no-buffer
```

### Using Python:

```python
import requests

# Upload PDF and generate notebook
with open("paper.pdf", "rb") as f:
    response = requests.post(
        "http://localhost:8000/api/generate",
        files={"file": f},
        data={"api_key": "YOUR_API_KEY"},
        stream=True
    )

    for line in response.iter_lines():
        if line:
            print(line.decode('utf-8'))
```

## 🚢 Deploying to Railway

Railway deployment is super simple with this single-file architecture!

### Method 1: Using Railway CLI

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login to Railway
railway login

# Initialize project
railway init

# Deploy
railway up
```

### Method 2: Using Railway Dashboard

1. Go to [Railway.app](https://railway.app)
2. Click **"New Project"** → **"Deploy from GitHub repo"**
3. Select your repository
4. Railway will auto-detect Python and deploy
5. Add environment variables in Railway dashboard:
   - `GOOGLE_API_KEY` (optional)
   - `MAX_UPLOAD_MB` (optional, default: 30)

### Method 3: One-Click Deploy

[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/new)

### Railway Configuration

Railway will automatically:
- Detect `requirements.txt` and install dependencies
- Run `python app.py`
- Set the `PORT` environment variable
- Provide a public URL

**No Docker needed!** Railway handles everything.

## 🔧 Configuration

Configuration is done via environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `GOOGLE_API_KEY` | Gemini API key (fallback) | Built-in demo key |
| `MAX_UPLOAD_MB` | Maximum PDF upload size | 30 |
| `PORT` | Server port | 8000 |

## 📁 Project Structure

```
backend/
├── app.py              # Single file with all logic
├── requirements.txt    # Python dependencies
├── .env.example        # Environment variables template
└── README.md          # This file
```

## 🔍 How It Works

The backend implements a 4-step pipeline:

1. **Analysis** - Extract paper structure, algorithms, and key concepts
2. **Design** - Plan a toy implementation with small-scale architecture
3. **Generate** - Create complete Jupyter notebook cells with PyTorch code
4. **Validate** - LLM reviews and repairs any issues

All steps use Google's Gemini 2.0 Flash model for fast, high-quality generation.

## 🐛 Troubleshooting

### "Module not found" errors
```bash
pip install -r requirements.txt
```

### Port already in use
```bash
PORT=3001 python app.py
```

### CORS errors from frontend
Make sure the frontend URL is allowed in CORS settings (currently set to allow all origins `*` for development).

### PDF upload fails
Check that:
- PDF is under 30MB
- File is a valid PDF
- API key is correct

### Gemini API errors
- Verify your API key at [Google AI Studio](https://aistudio.google.com/apikey)
- Check you have API quota remaining
- Ensure you're using a valid model (default: `gemini-2.0-flash-exp`)

## 📊 Performance

- Typical processing time: 2-5 minutes per paper
- Concurrent requests: Limited to 3 simultaneous generations
- Max PDF size: 30MB
- Max PDF pages: ~100 pages (soft limit)

## 🔐 Security Notes

- API keys are never logged or stored
- Temporary files are stored in system temp directory
- Files are kept only during request lifecycle
- In production, restrict CORS to your frontend domain

## 📝 License

Same as parent project.

## 🤝 Contributing

This is a single-file architecture for simplicity. If you want to contribute:
- Keep everything in `app.py`
- Maintain Railway compatibility
- Test locally before deploying

## 📧 Support

For issues, check:
1. API documentation at `/docs`
2. Health endpoint at `/health`
3. Backend logs for error messages
