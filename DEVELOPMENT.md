# Development Guide

## Project Structure

```
classical-music-player/
├── backend/                    # FastAPI backend
│   ├── app/
│   │   ├── main.py            # FastAPI app entry point
│   │   ├── models.py          # Database models
│   │   ├── schemas.py         # Pydantic schemas
│   │   ├── config.py          # Configuration
│   │   ├── database.py        # Database setup
│   │   ├── services.py        # Business logic
│   │   ├── utils.py           # Utilities
│   │   └── routers/           # API endpoints
│   ├── tests/                 # Unit tests
│   │   ├── conftest.py        # Pytest fixtures
│   │   ├── test_services.py   # Service tests
│   │   └── test_models.py     # Model tests
│   ├── tools/                 # Debugging tools
│   │   └── debug_prompt.py    # Prompt debugging script
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/                  # Vue 3 frontend
│   ├── src/
│   │   ├── components/        # Vue components
│   │   ├── pages/             # Page components
│   │   ├── layouts/           # Layout templates
│   │   ├── stores/            # Pinia state
│   │   ├── api/               # API clients
│   │   ├── App.vue
│   │   └── main.ts
│   ├── index.html
│   ├── vite.config.ts
│   ├── Dockerfile
│   └── package.json
├── testdata/
│   └── audio/                 # Test audio files in M4A format
├── docker-compose.yml
├── .gitignore
├── README.md
└── DEVELOPMENT.md             # This file
```

## Prerequisites

- Docker & Docker Compose
- Node.js 20+ (for frontend development)
- Python 3.12+ (for backend development)
- FFmpeg (for audio processing)

## Quick Start with Docker

1. Create `.env` file in project root:
   ```bash
   OPENAI_API_KEY=your_api_key_here
   ```

2. Start all services:
   ```bash
   docker compose up --build
   ```

3. Access:
   - Frontend: http://localhost:5173
   - Backend: http://localhost:8000
   - Database: localhost:5432

## Backend Development

### Setup Local Environment

```bash
cd backend
python -m venv venv

# On Windows
venv\Scripts\activate
# On macOS/Linux
source venv/bin/activate

pip install -r requirements.txt
```

### Run Backend Locally

```bash
cd backend
uvicorn app.main:app --reload
```

Backend will be available at `http://localhost:8000`

### Run Tests

```bash
cd backend
pytest tests/ -v

# Run specific test file
pytest tests/test_services.py -v

# Run with coverage
pytest tests/ --cov=app
```

### Debug LLM Prompts

Test prompt engineering without running full backend:

```bash
cd backend/tools
export OPENAI_API_KEY=your_key
python debug_prompt.py /path/to/audio/file.m4a
```

This script will:
1. Read ID3 tags from the audio file
2. Display the generated prompt
3. Call OpenAI API
4. Show the LLM response
5. Parse and display the extracted JSON

## Frontend Development

### Setup Local Environment

```bash
cd frontend
npm install
```

### Run Development Server

```bash
npm run dev
```

Frontend will be available at `http://localhost:5173`

### Build for Production

```bash
npm run build
```

Built files will be in `frontend/dist/`

### Run Tests

```bash
npm test
```

## Testing with Test Data

The `testdata/audio/` directory contains 23 sample M4A audio files for testing.

### Backend Tests with Test Data

The test suite automatically discovers and tests with files in `testdata/audio/`:

```bash
cd backend
pytest tests/test_services.py::TestMetadataExtraction::test_read_tags_multiple_files -v -s
```

This will:
1. Read ID3 tags from each test file
2. Verify tag extraction works correctly
3. Print extracted metadata for each file

### Monitor Test Data Processing

```bash
cd backend/tools
python debug_prompt.py ../../../testdata/audio/092.019-Antonio\ Vivaldi-Concerto\ for\ 4\ Violins,\ Cello,\ Strings\ and\ Continu.m4a
```

## Database

### View Database

Connect with psql:

```bash
psql -h localhost -U user -d musicdb -W
```

Password: `password`

### Reset Database

```bash
docker compose down -v
docker compose up
```

## API Documentation

Once backend is running, visit `http://localhost:8000/docs` for interactive API docs (Swagger UI).

### Key Endpoints

- `POST /api/v1/auth/token` - Login
- `GET /api/v1/auth/me` - Current user
- `POST /api/v1/audio/import` - Import audio file
- `GET /api/v1/search?query=...` - Search music
- `GET /api/v1/works` - List works
- `GET /api/v1/works/{work_id}/recommendations` - Get recommendations

## Common Tasks

### Add New Backend Endpoint

1. Create router in `backend/app/routers/`
2. Define models in `backend/app/models.py`
3. Define schemas in `backend/app/schemas.py`
4. Add services in `backend/app/services.py`
5. Include router in `backend/app/main.py`

### Add New Frontend Page

1. Create component in `frontend/src/pages/`
2. Add route in `frontend/src/router/index.ts`
3. Link from navigation in `frontend/src/layouts/MainLayout.vue`

### Test New Audio Format Support

Edit `backend/app/services.py`:

```python
SUPPORTED_FORMATS = {
    '.your_format': 'flac',
    # ... other formats
}
```

Then test with:

```bash
cd backend/tools
python debug_prompt.py /path/to/file.your_format
```

## Debugging

### Backend

Enable debug logging:

```python
# In app/main.py
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Frontend

Use Vue DevTools browser extension and browser console:

```javascript
// In browser console
localStorage.setItem('debug', 'app:*')
location.reload()
```

## Troubleshooting

### Port Already in Use

```bash
# Find process using port
lsof -i :8000  # Backend
lsof -i :5173  # Frontend
lsof -i :5432  # Database

# Kill process
kill -9 <PID>
```

### Database Connection Issues

```bash
# Check if container is running
docker ps

# Check logs
docker compose logs db

# Restart database
docker compose restart db
```

### Frontend Not Starting

```bash
# Check Node version
node --version

# Clear node_modules and reinstall
rm -rf frontend/node_modules
npm install --prefix frontend
```

## Production Deployment

### Build Docker Images

```bash
docker compose build
```

### Push to Registry

```bash
docker tag classical-music-player-backend:latest registry/backend:latest
docker tag classical-music-player-frontend:latest registry/frontend:latest
docker push registry/backend:latest
docker push registry/frontend:latest
```

### Deploy on Server

```bash
docker compose -f docker-compose.yml up -d
```

## Performance Tips

- Use `--prod` flag when building frontend
- Enable caching in nginx for static assets
- Configure database connection pooling
- Use Redis for session/cache layer (future enhancement)

## Contributing

1. Create feature branch: `git checkout -b feature/my-feature`
2. Make changes and test
3. Commit: `git commit -am 'Add my feature'`
4. Push: `git push origin feature/my-feature`
5. Create Pull Request

## License

[Your License Here]
