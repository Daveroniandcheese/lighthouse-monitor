#!/usr/bin/env python3
"""
Lighthouse Monitor - Weekly performance tracking with email alerts

Uses Google PageSpeed Insights API to run Lighthouse audits and
sends email alerts when scores change significantly.
"""

import json
import os
import smtplib
import sys
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Optional
from urllib.parse import urlencode

import requests

# Configuration defaults
DEFAULT_THRESHOLD = 5  # Alert if score changes by this many points
PAGESPEED_API_URL = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"

CATEGORIES = ["performance", "accessibility", "best-practices", "seo"]


def load_config() -> dict:
    """Load configuration from config.json or environment variables."""
    config_path = Path(__file__).parent / "config.json"
    
    if config_path.exists():
        with open(config_path) as f:
            config = json.load(f)
    else:
        config = {}
    
    # Environment variables override config file
    return {
        "urls": config.get("urls", os.environ.get("LIGHTHOUSE_URLS", "").split(",") if os.environ.get("LIGHTHOUSE_URLS") else []),
        "api_key": os.environ.get("PAGESPEED_API_KEY", config.get("api_key", "")),
        "threshold": int(os.environ.get("ALERT_THRESHOLD", config.get("threshold", DEFAULT_THRESHOLD))),
        "smtp_host": os.environ.get("SMTP_HOST", config.get("smtp_host", "smtp.gmail.com")),
        "smtp_port": int(os.environ.get("SMTP_PORT", config.get("smtp_port", 587))),
        "smtp_user": os.environ.get("SMTP_USER", config.get("smtp_user", "")),
        "smtp_password": os.environ.get("SMTP_PASSWORD", config.get("smtp_password", "")),
        "email_from": os.environ.get("EMAIL_FROM", config.get("email_from", "")),
        "email_to": os.environ.get("EMAIL_TO", config.get("email_to", "")),
        "categories": config.get("categories", CATEGORIES),
    }


def load_history() -> dict:
    """Load previous results from history file."""
    history_path = Path(__file__).parent / "history.json"
    
    if history_path.exists():
        with open(history_path) as f:
            return json.load(f)
    return {"runs": []}


def save_history(history: dict) -> None:
    """Save results to history file."""
    history_path = Path(__file__).parent / "history.json"
    
    with open(history_path, "w") as f:
        json.dump(history, f, indent=2)


def run_lighthouse(url: str, api_key: str, categories: list[str]) -> Optional[dict]:
    """Run Lighthouse audit via PageSpeed Insights API."""
    params = {
        "url": url,
        "strategy": "mobile",  # or "desktop"
    }
    
    for category in categories:
        params["category"] = params.get("category", [])
        if isinstance(params["category"], str):
            params["category"] = [params["category"]]
    
    # Build URL with multiple category params
    query_parts = [f"url={requests.utils.quote(url)}", "strategy=mobile"]
    for cat in categories:
        query_parts.append(f"category={cat}")
    if api_key:
        query_parts.append(f"key={api_key}")
    
    full_url = f"{PAGESPEED_API_URL}?{'&'.join(query_parts)}"
    
    try:
        print(f"Running Lighthouse for: {url}")
        response = requests.get(full_url, timeout=120)
        response.raise_for_status()
        data = response.json()
        
        # Extract scores
        lighthouse_result = data.get("lighthouseResult", {})
        categories_data = lighthouse_result.get("categories", {})
        
        scores = {}
        for cat in categories:
            cat_key = cat.replace("-", "")  # API returns without hyphens sometimes
            if cat in categories_data:
                scores[cat] = int(categories_data[cat]["score"] * 100)
            elif cat.replace("-", "") in categories_data:
                scores[cat] = int(categories_data[cat.replace("-", "")]["score"] * 100)
            # Handle 'best-practices' specifically
            elif cat == "best-practices" and "best-practices" in categories_data:
                scores[cat] = int(categories_data["best-practices"]["score"] * 100)
        
        return scores
        
    except requests.RequestException as e:
        print(f"Error running Lighthouse for {url}: {e}")
        return None


def compare_scores(current: dict, previous: dict, threshold: int) -> list[dict]:
    """Compare current scores to previous and return changes exceeding threshold."""
    changes = []
    
    for category, current_score in current.items():
        prev_score = previous.get(category)
        if prev_score is not None:
            diff = current_score - prev_score
            if abs(diff) >= threshold:
                changes.append({
                    "category": category,
                    "previous": prev_score,
                    "current": current_score,
                    "diff": diff,
                    "direction": "improved" if diff > 0 else "declined"
                })
    
    return changes


def format_email_html(results: list[dict], run_date: str) -> str:
    """Format results as HTML email."""
    html = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            h1 {{ color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px; }}
            h2 {{ color: #34495e; margin-top: 30px; }}
            .url-section {{ background: #f9f9f9; padding: 15px; border-radius: 8px; margin: 20px 0; }}
            .score-table {{ width: 100%; border-collapse: collapse; margin: 15px 0; }}
            .score-table th, .score-table td {{ padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }}
            .score-table th {{ background: #3498db; color: white; }}
            .improved {{ color: #27ae60; font-weight: bold; }}
            .declined {{ color: #e74c3c; font-weight: bold; }}
            .no-change {{ color: #7f8c8d; }}
            .alert {{ background: #fff3cd; border: 1px solid #ffc107; padding: 10px; border-radius: 4px; margin: 10px 0; }}
            .score-badge {{ display: inline-block; padding: 4px 12px; border-radius: 20px; font-weight: bold; }}
            .score-good {{ background: #d4edda; color: #155724; }}
            .score-ok {{ background: #fff3cd; color: #856404; }}
            .score-bad {{ background: #f8d7da; color: #721c24; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🔍 Lighthouse Report</h1>
            <p><strong>Run Date:</strong> {run_date}</p>
    """
    
    for result in results:
        url = result["url"]
        scores = result["scores"]
        changes = result.get("changes", [])
        previous = result.get("previous", {})
        
        html += f'<div class="url-section"><h2>{url}</h2>'
        
        if changes:
            html += '<div class="alert">⚠️ Score changes detected!</div>'
        
        html += """
            <table class="score-table">
                <tr>
                    <th>Category</th>
                    <th>Current</th>
                    <th>Previous</th>
                    <th>Change</th>
                </tr>
        """
        
        for category, score in scores.items():
            prev_score = previous.get(category, "N/A")
            
            # Determine score badge color
            if score >= 90:
                badge_class = "score-good"
            elif score >= 50:
                badge_class = "score-ok"
            else:
                badge_class = "score-bad"
            
            # Determine change display
            if prev_score != "N/A":
                diff = score - prev_score
                if diff > 0:
                    change_html = f'<span class="improved">+{diff} ↑</span>'
                elif diff < 0:
                    change_html = f'<span class="declined">{diff} ↓</span>'
                else:
                    change_html = '<span class="no-change">—</span>'
            else:
                change_html = '<span class="no-change">First run</span>'
            
            html += f"""
                <tr>
                    <td>{category.replace("-", " ").title()}</td>
                    <td><span class="score-badge {badge_class}">{score}</span></td>
                    <td>{prev_score}</td>
                    <td>{change_html}</td>
                </tr>
            """
        
        html += "</table></div>"
    
    html += """
        </div>
    </body>
    </html>
    """
    
    return html


def format_email_text(results: list[dict], run_date: str) -> str:
    """Format results as plain text email."""
    text = f"LIGHTHOUSE REPORT\n{'=' * 50}\nRun Date: {run_date}\n\n"
    
    for result in results:
        url = result["url"]
        scores = result["scores"]
        changes = result.get("changes", [])
        previous = result.get("previous", {})
        
        text += f"\n{url}\n{'-' * len(url)}\n\n"
        
        if changes:
            text += "⚠️  SCORE CHANGES DETECTED!\n\n"
        
        for category, score in scores.items():
            prev_score = previous.get(category, "N/A")
            
            if prev_score != "N/A":
                diff = score - prev_score
                if diff > 0:
                    change = f"+{diff} ↑"
                elif diff < 0:
                    change = f"{diff} ↓"
                else:
                    change = "—"
            else:
                change = "First run"
            
            text += f"  {category.replace('-', ' ').title():20} {score:3} (was {prev_score}) {change}\n"
        
        text += "\n"
    
    return text


def send_email(config: dict, subject: str, html_body: str, text_body: str) -> bool:
    """Send email via SMTP."""
    if not all([config["smtp_user"], config["smtp_password"], config["email_to"]]):
        print("Email not configured, skipping notification")
        return False
    
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = config["email_from"] or config["smtp_user"]
        msg["To"] = config["email_to"]
        
        msg.attach(MIMEText(text_body, "plain"))
        msg.attach(MIMEText(html_body, "html"))
        
        with smtplib.SMTP(config["smtp_host"], config["smtp_port"]) as server:
            server.starttls()
            server.login(config["smtp_user"], config["smtp_password"])
            server.sendmail(msg["From"], config["email_to"].split(","), msg.as_string())
        
        print(f"Email sent to {config['email_to']}")
        return True
        
    except Exception as e:
        print(f"Failed to send email: {e}")
        return False


def main():
    """Main execution flow."""
    config = load_config()
    
    if not config["urls"]:
        print("No URLs configured. Add URLs to config.json or set LIGHTHOUSE_URLS env var.")
        sys.exit(1)
    
    # Filter out empty strings from URLs
    urls = [u.strip() for u in config["urls"] if u.strip()]
    
    if not urls:
        print("No valid URLs found.")
        sys.exit(1)
    
    history = load_history()
    run_date = datetime.now().isoformat()
    
    # Get previous run for comparison
    previous_run = history["runs"][-1] if history["runs"] else None
    previous_scores = {}
    if previous_run:
        for result in previous_run.get("results", []):
            previous_scores[result["url"]] = result["scores"]
    
    # Run audits
    current_results = []
    has_changes = False
    
    for url in urls:
        scores = run_lighthouse(url, config["api_key"], config["categories"])
        
        if scores:
            prev = previous_scores.get(url, {})
            changes = compare_scores(scores, prev, config["threshold"])
            
            if changes:
                has_changes = True
            
            current_results.append({
                "url": url,
                "scores": scores,
                "previous": prev,
                "changes": changes
            })
            
            print(f"  Scores: {scores}")
            if changes:
                for change in changes:
                    print(f"  ⚠️  {change['category']}: {change['previous']} → {change['current']} ({change['direction']})")
    
    # Save to history
    history["runs"].append({
        "date": run_date,
        "results": [{"url": r["url"], "scores": r["scores"]} for r in current_results]
    })
    
    # Keep only last 52 runs (1 year of weekly data)
    if len(history["runs"]) > 52:
        history["runs"] = history["runs"][-52:]
    
    save_history(history)
    print(f"\nResults saved to history.json")
    
    # Send email
    if current_results:
        if has_changes:
            subject = "🚨 Lighthouse Alert: Score Changes Detected"
        else:
            subject = "✅ Lighthouse Report: No Significant Changes"
        
        html_body = format_email_html(current_results, run_date)
        text_body = format_email_text(current_results, run_date)
        
        send_email(config, subject, html_body, text_body)


if __name__ == "__main__":
    main()
