"""International comparison page; existing URL and features are preserved."""

from src.comparison_ui import render_comparison
from src.ui import footer, page_header

page_header("SIDE BY SIDE", "Put performance in perspective.", "Compare up to ten companies from the same starting point. Every line begins at 0%, using adjusted prices on shared trading dates.")
render_comparison()
footer()
