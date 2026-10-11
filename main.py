"""Run Blade.

    python main.py              open the local web page in your browser
    python main.py today ...    same as: python -m blade today ...
"""
import sys
import threading
import webbrowser

from blade.cli import main

PORT = 8317

if __name__ == "__main__":
    if len(sys.argv) == 1:
        threading.Timer(1.0, webbrowser.open, [f"http://127.0.0.1:{PORT}"]).start()
        main(["serve", "--port", str(PORT)])
    else:
        main()
