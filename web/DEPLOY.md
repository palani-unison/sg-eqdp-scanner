# Deploying eqdp-screener to Vercel

The web app builds clean (`npm run build` ✓). To deploy you need to (1) link a Vercel project named `eqdp-screener` and (2) set environment variables there.

## Path A — Vercel CLI (fastest, no GitHub required first)

Run these from inside the `web/` directory.

```bash
# 1. Link a new Vercel project named eqdp-screener
#    When prompted, accept defaults except:
#      Set up and deploy? Y
#      Which scope? <your account>
#      Link to existing project? N
#      Project name: eqdp-screener
#      In which directory is your code located? ./
vercel link --project eqdp-screener --yes

# 2. Push environment variables to the linked project (production scope)
#    The values are read from web/.env.local — Vercel CLI handles them.
vercel env add NEXT_PUBLIC_SUPABASE_URL production < <(grep '^NEXT_PUBLIC_SUPABASE_URL=' .env.local | cut -d= -f2-)
vercel env add NEXT_PUBLIC_SUPABASE_ANON_KEY production < <(grep '^NEXT_PUBLIC_SUPABASE_ANON_KEY=' .env.local | cut -d= -f2-)
vercel env add SUPABASE_SERVICE_KEY production < <(grep '^SUPABASE_SERVICE_KEY=' .env.local | cut -d= -f2-)
vercel env add ADMIN_EMAIL production < <(grep '^ADMIN_EMAIL=' .env.local | cut -d= -f2-)
vercel env add RESEND_API_KEY production < <(grep '^RESEND_API_KEY=' .env.local | cut -d= -f2-)
vercel env add RESEND_FROM_EMAIL production < <(grep '^RESEND_FROM_EMAIL=' .env.local | cut -d= -f2-)
vercel env add NEXT_PUBLIC_SITE_URL production
# When prompted, paste the production URL Vercel gives you (e.g. https://eqdp-screener.vercel.app)

# 3. Deploy production
vercel --prod
```

The first `vercel link` prints the project URL. After step 3, the production URL appears in stdout — that's your live site.

## Path B — Connect GitHub repo (preferred for ongoing CI/CD)

```bash
# From the project root
git init
git add .
git commit -m "Initial commit"
gh repo create sg-eqdp-scanner --public --source . --remote origin --push

# Then in the Vercel dashboard:
#   New Project → Import Git → pick sg-eqdp-scanner
#   Set Root Directory: web
#   Framework: Next.js (auto-detected)
#   Project name: eqdp-screener
#   Add the same six env vars as in Path A under Environment → Production
#   Click Deploy
```

Path B is what you want long-term — every push to `main` auto-deploys.

## After first deploy

1. **Open `/admin` in production** — the middleware redirects you to `/login`. Sign in with the admin password (`Eqdp2026!`) using the **Password (admin)** tab.
2. **Rotate the admin password** via Supabase Dashboard → Authentication → Users → `pachidam@outlook.com` → Reset Password. The current password is in chat history; rotate it.
3. **Update Supabase Auth redirect URLs** — Supabase Dashboard → Authentication → URL Configuration → add `https://<your-vercel-url>/auth/callback` to "Redirect URLs". Without this, magic links 404.
4. **Set `NEXT_PUBLIC_SITE_URL`** in `.env.local` and Vercel to your real production URL (so magic-link callbacks point there in dev).

## What's deployed

- `/` landing
- `/about` personal-research framing
- `/disclaimer` full text
- `/login` magic link or admin password
- `/register` public registration (magic link)
- `/admin` (gated to ADMIN_EMAIL) — pipeline runs + counts
- `/admin/users` (gated) — registration list
- `/brief` (gated) — top-15 candidate scores from Supabase
- `/tracker` (gated) — pipeline status + stale-data banner

## Coming next

- `/brief` charts (event-study CARs with bootstrap CI shading, sector heatmap)
- Per-stock detail drawers
- Live filings feed in `/tracker` (depends on Day-6 SGXNet scraper)
- On-demand PDF export
