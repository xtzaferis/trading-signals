# Cloudflare advisory scheduler

This optional Worker dispatches the existing GitHub Pages advisory workflow
every five minutes, but only from 17:00 inclusive until 19:00 exclusive in
`Europe/Athens`. It does not scan markets, hold exchange credentials, or send
orders. Cloudflare Cron Triggers run in UTC; the Worker checks Athens local time
at runtime so daylight-saving changes are handled automatically.

## 1. Create a restricted GitHub token

In GitHub, create a fine-grained personal access token with:

- Repository access: **Only select repositories** > `trading-signals`
- Repository permission: **Actions: Read and write**
- A short expiration date that you will renew deliberately

No Contents write permission or exchange credential is required. Copy the
token once and do not add it to `.env`, Wrangler configuration, or Git.

## 2. Configure and deploy the Worker

From this directory, authenticate Wrangler, store the token as an encrypted
Cloudflare secret, and deploy:

```powershell
cd deploy\cloudflare-advisory-scheduler
npx wrangler login
npx wrangler secret put GITHUB_TOKEN
npx wrangler deploy
```

Paste the fine-grained token only when `wrangler secret put` prompts for it.
The committed `wrangler.jsonc` declares a five-minute Cron Trigger. The Worker
runs every five minutes but skips GitHub dispatches outside the Athens session.

## 3. Verify

During 17:00–19:00 Athens time, open GitHub **Actions** and confirm new runs are
labelled `Manually run`/`workflow_dispatch` approximately every five minutes.
Cloudflare **Workers & Pages > trading-signals-scheduler > Logs** should show a
successful dispatch status. Outside the session it logs that dispatch was
skipped.

The existing GitHub `schedule` remains enabled as a fallback. Occasional
duplicate triggers are serialized by the workflow's concurrency group.

## Security and removal

Rotate or revoke the fine-grained token if it is ever pasted anywhere except
the Cloudflare secret prompt. To stop this scheduler, remove its Cron Trigger
or delete the Worker in Cloudflare, then revoke the GitHub token.
