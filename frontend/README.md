# Frontend - Classical Music Player

Vue 3 + TypeScript + Vite + PWA frontend for streaming classical music.

## Features

- **Search**: AI-powered search with natural language support
- **Playback**: Audio streaming with support for FLAC, MP3, M4A formats
- **Library**: Personal playlist and favorite management
- **PWA**: Progressive Web App support for offline access
- **Responsive**: Mobile-first design with Tailwind CSS
- **Authentication**: JWT-based user authentication

## Setup

```bash
cd frontend
npm install
npm run dev
```

## Build

```bash
npm run build
```

## Testing

```bash
npm test
```

## Environment Variables

Create `.env.local`:

```
VUE_APP_BASE_URL=http://localhost:8000
```

## Project Structure

- `src/components` - Reusable Vue components
- `src/pages` - Page components
- `src/layouts` - Layout templates
- `src/stores` - Pinia state management
- `src/api` - API client and services
