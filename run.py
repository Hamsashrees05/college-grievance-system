"""Start the website:  python run.py   ->  http://127.0.0.1:5000"""
import os

from dotenv import load_dotenv

load_dotenv()

from app import create_app          # noqa: E402  (must come after load_dotenv)
from app.db import init_db          # noqa: E402
from app.escalation import start_scheduler  # noqa: E402

app = create_app()
with app.app_context():
    init_db()  # creates tables if they do not exist yet (does not delete data)

if __name__ == "__main__":
    start_scheduler(app)
    # use_reloader=False so the daily escalation job can never be started twice
    app.run(host="127.0.0.1", port=5000, debug=os.environ.get("FLASK_DEBUG") == "1", use_reloader=False)
