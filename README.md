# Lighthouse Monitor

Automated weekly Lighthouse performance monitoring with email alerts when scores change significantly.

## Features

- 📊 **Tracks all Lighthouse categories**: Performance, Accessibility, Best Practices, SEO
- 📈 **Historical comparison**: Compares each run against previous results
- 🚨 **Smart alerts**: Email notifications when scores change beyond your threshold
- 🕐 **Automated scheduling**: Runs weekly via GitHub Actions (free!)
- 📧 **Beautiful emails**: HTML reports with color-coded scores
- 🔧 **Configurable**: Adjust thresholds, categories, and URLs easily

## Quick Setup

### 1. Create a GitHub Repository

Create a new repository and clone it locally, then copy these files into it.

### 2. Get a PageSpeed Insights API Key (Optional but Recommended)

Without an API key, you're limited to a few requests. With one, you get 25,000/day free.

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (or select existing)
3. Enable the **PageSpeed Insights API**
4. Go to **Credentials** → **Create Credentials** → **API Key**
5. Copy the API key

### 3. Configure GitHub Secrets

Go to your repository → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**

Add these secrets:

| Secret Name | Description | Example |
|-------------|-------------|---------|
| `LIGHTHOUSE_URLS` | Comma-separated URLs to monitor | `https://example.com,https://example.com/products` |
| `PAGESPEED_API_KEY` | Your Google API key | `AIza...` |
| `ALERT_THRESHOLD` | Points change to trigger alert (optional, default: 5) | `5` |
| `SMTP_HOST` | Your SMTP server | `smtp.gmail.com` |
| `SMTP_PORT` | SMTP port (optional, default: 587) | `587` |
| `SMTP_USER` | Email username | `your-email@gmail.com` |
| `SMTP_PASSWORD` | Email password or app password | `your-app-password` |
| `EMAIL_FROM` | From address (optional, defaults to SMTP_USER) | `alerts@yourdomain.com` |
| `EMAIL_TO` | Recipient email(s), comma-separated | `you@example.com` |

### 4. Gmail Setup (if using Gmail)

Gmail requires an "App Password" rather than your regular password:

1. Enable 2-Factor Authentication on your Google account
2. Go to [Google App Passwords](https://myaccount.google.com/apppasswords)
3. Generate a new app password for "Mail"
4. Use this as your `SMTP_PASSWORD`

### 5. Test It

1. Go to **Actions** tab in your repository
2. Select **Lighthouse Monitor** workflow
3. Click **Run workflow** → **Run workflow**
4. Watch the logs to verify it works

## Local Development

To run locally:

```bash
# Install dependencies
pip install -r requirements.txt

# Copy and edit config
cp config.example.json config.json
# Edit config.json with your settings

# Run
python lighthouse_monitor.py
```

## Configuration Options

### Via config.json (local development)

```json
{
  "urls": [
    "https://example.com",
    "https://example.com/blog"
  ],
  "api_key": "your-api-key",
  "threshold": 5,
  "categories": ["performance", "accessibility", "best-practices", "seo"],
  "smtp_host": "smtp.gmail.com",
  "smtp_port": 587,
  "smtp_user": "your-email@gmail.com",
  "smtp_password": "your-app-password",
  "email_from": "your-email@gmail.com",
  "email_to": "recipient@example.com"
}
```

### Via Environment Variables (GitHub Actions)

Environment variables override config.json values. See the secrets table above.

## Adjusting the Schedule

Edit `.github/workflows/lighthouse.yml` and change the cron expression:

```yaml
schedule:
  - cron: '0 8 * * 0'  # Every Sunday at 8am UTC
```

Common schedules:
- `'0 8 * * 0'` - Weekly on Sunday at 8am UTC
- `'0 8 * * 1'` - Weekly on Monday at 8am UTC
- `'0 8 1 * *'` - Monthly on the 1st at 8am UTC
- `'0 8 * * *'` - Daily at 8am UTC

Use [crontab.guru](https://crontab.guru/) to build custom schedules.

## History Data

Results are stored in `history.json` and committed back to the repo after each run. This keeps up to 52 weeks of data (1 year).

## Troubleshooting

### "No URLs configured"
Make sure `LIGHTHOUSE_URLS` secret is set correctly with comma-separated URLs.

### "Failed to send email"
- Check SMTP credentials
- For Gmail, ensure you're using an App Password
- Verify `EMAIL_TO` is set

### Rate limiting
Without an API key, PageSpeed Insights has strict limits. Add your API key to avoid this.

### Action not running on schedule
- GitHub may delay scheduled actions by minutes to hours during high load
- Use **Run workflow** button to test manually
- Check if the repo has had recent activity (scheduled actions pause on inactive repos)

## License

MIT
