Keeping the demo warm (stop the 1-minute cold start)
=====================================================

The demo runs on Render's free tier, which puts the app to sleep after about
15 minutes without traffic. The next visitor waits up to ~1 minute while it
wakes. The app now shows a splash explaining this, but for a live judging
session you want the app already awake.

You set this up yourself in about 3 minutes. Nothing to install.

Option A - cron-job.org (recommended)
-------------------------------------
1. Go to https://cron-job.org and create a free account (email only).
2. Create a new cronjob:
   - URL:  https://setu-demo-3ogx.onrender.com/health
   - Schedule: every 10 minutes (any interval between 5 and 14 minutes works)
   - Request method: GET
3. Save. The /health endpoint is a tiny JSON response made exactly for this;
   it does not touch the database or any student data.

Option B - UptimeRobot
----------------------
1. Go to https://uptimerobot.com and create a free account.
2. Add a new monitor:
   - Monitor type: HTTP(s)
   - URL: https://setu-demo-3ogx.onrender.com/health
   - Monitoring interval: 5 minutes (free plan minimum)
3. Save.

Notes
-----
- Either service alone is enough; do not run both.
- Before judging, still open the demo once 2-3 minutes early. A keep-warm
  ping keeps the app awake, but the very first load after a deploy always
  takes a few extra seconds.
- The keep-warm ping does not fix Render's other free-tier limits (monthly
  free hours, occasional slow first response after a redeploy).
- I have not signed up for anything on your behalf. These steps are yours
  to do (or skip) - the app works without this, just with the cold-start wait.
