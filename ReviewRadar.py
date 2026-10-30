import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from openai import OpenAI
import requests

# 1. Initialize OpenAI Client (Replace with your actual API key)
client = OpenAI(api_key="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")

# 2. Setup Google Sheets Authentication
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
gc = gspread.authorize(creds)

# Open your Google Sheet database
sheet = gc.open("Reputation bot").sheet1

def process_new_reviews():
    rows = sheet.get_all_records()
    
    for idx, row in enumerate(rows, start=2):  # start=2 because row 1 is headers
        # Process only if Sentiment column (Column G) is empty
        if not row.get("Sentiment"):
            review_text = row.get("ReviewText", "")
            if not review_text:
                continue

            # AI Prompt for Sentiment, Category, and Draft Reply
            prompt = f"""
            Analyze this customer review: "{review_text}"
            Return format exactly like this:
            Sentiment: [Positive/Neutral/Negative]
            Category: [Customer Service / Pricing / Quality / Other]
            DraftReply: [Short, polite response]
            """
            
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}]
            )
            ai_output = response.choices[0].message.content

            # Parse AI Output
            sentiment = "Neutral"
            draft_reply = ""
            
            for line in ai_output.strip().split("\n"):
                if line.startswith("Sentiment:"):
                    sentiment = line.replace("Sentiment:", "").strip()
                elif line.startswith("DraftReply:"):
                    draft_reply = line.replace("DraftReply:", "").strip()

            # Determine Status
            status = "Needs Follow-Up" if "Negative" in sentiment else "Resolved"

            # Write back to Google Sheet
            # Column 7 = Sentiment (G), Column 8 = DraftReply (H), Column 9 = Status (I)
            sheet.update_cell(idx, 7, sentiment)
            sheet.update_cell(idx, 8, draft_reply)
            sheet.update_cell(idx, 9, status)
            
            # If negative, send Discord/Slack Webhook notification
            if "Negative" in sentiment:
                webhook_url = "https://discord.com/api/webhooks/1565584207584034896/sKjI-58ZovFlFTqZO8OXhbKuIDENo7jfXS0LpbJyyhAEZpBNkTEiOjlaYr_q8YZm3AaO"
                payload = {
                    "content": f"🚨 **Negative Review Alert!**\n**Review:** {review_text}\n**Suggested Reply:** {draft_reply}"
                }
                requests.post(webhook_url, json=payload)

if __name__ == "__main__":
    process_new_reviews()
    print("Reviews processed successfully!")