# Deploy `dev` to Vercel + Render

This setup deploys automatically from the `dev` branch:
- Frontend (`apps/web`) on Vercel
- API (`apps/api`) on Render using `apps/api/Dockerfile.render`

## 1) Push branch

```bash
git checkout dev
git pull origin dev
git push origin dev
```

## 2) Render (API)

Create a new **Web Service**:
- Branch: `dev`
- Runtime: `Docker`
- Dockerfile path: `apps/api/Dockerfile.render`
- Health check path: `/health`
- Auto deploy: `On`

Environment variables:
- `WEB_API_CORS_ORIGINS=https://<your-vercel-domain>,http://localhost:3000`
- `WEB_API_REQUEST_TIMEOUT_SECONDS=20`
- `WEB_API_RETRY_ATTEMPTS=1`
- `WEB_API_ANALYSIS_CACHE_TTL_SECONDS=180`
- `WEB_API_TICKER_INFO_CACHE_TTL_SECONDS=86400`
- `WEB_API_RATE_LIMIT_WINDOW_SECONDS=60`
- `WEB_API_RATE_LIMIT_ANALYSIS_REQUESTS=20`
- `WEB_API_RATE_LIMIT_CHAT_REQUESTS=12`

## 3) Vercel (Frontend)

Create a new project:
- Branch: `dev`
- Root Directory: `apps/web`
- Framework: `Next.js`
- Auto deploy: `On`

Environment variables:
- `NEXT_PUBLIC_API_BASE_URL=https://<your-render-service>.onrender.com`

## 4) Verify

- Render health endpoint: `https://<your-render-service>.onrender.com/health`
- Open Vercel URL and run a ticker analysis request from the UI.

## Notes

- `NEXT_PUBLIC_*` variables are embedded at build time in Next.js. If you change
  `NEXT_PUBLIC_API_BASE_URL`, trigger a new Vercel deployment.
- If you see CORS errors, ensure `WEB_API_CORS_ORIGINS` contains the exact Vercel domain.
