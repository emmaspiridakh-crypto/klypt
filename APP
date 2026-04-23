from flask import Flask
import threading
import bot as discord_bot
 
app = Flask(__name__)
 
@app.route("/")
def home():
    return "🤖 Bot is running!", 200
 
@app.route("/health")
def health():
    return {"status": "ok", "bot": str(discord_bot.bot.user)}, 200
 
def run_flask():
    app.run(host="0.0.0.0", port=8080)
 
def run_bot():
    import os
    discord_bot.bot.run(os.getenv("DISCORD_TOKEN"))
 
if __name__ == "__main__":
    # Τρέχουμε Flask σε thread
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    # Τρέχουμε το bot στο main thread
    run_bot()
