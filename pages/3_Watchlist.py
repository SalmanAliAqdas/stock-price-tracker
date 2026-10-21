"""International session watchlist."""

from src.ui import footer, page_header
from src.watchlist_ui import render_watchlist

page_header("YOUR SHORTLIST", "Keep your companies close.", "Follow up to 100 companies, search and sort your list, and export a backup for your next session.")
render_watchlist()
footer()
