# JIRO Frontend

Separate Next.js App Router frontend for the JIRO FastAPI backend.

## Run locally

```bash
npm install
npm run dev
```

Set `NEXT_PUBLIC_API_BASE_URL` in `.env.local` when the backend is not at
`http://127.0.0.1:8000`. The client never accepts or stores provider secrets;
provider configuration remains server-side. The app keeps resume and job text
in component memory only and clears review state when the page is refreshed.

```bash
npm run build
```
