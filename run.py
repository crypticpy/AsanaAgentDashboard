#!/usr/bin/env python3
"""
Script to run the Asana Portfolio Dashboard.
"""
import os
import subprocess
import sys

def main():
    """
    Run the Streamlit app.
    """
    # Get the directory of this script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Change to the script directory
    os.chdir(script_dir)
    
    # Run the Streamlit app
    cmd = [sys.executable, "-m", "streamlit", "run", "app.py"]
    subprocess.run(cmd)

if __name__ == "__main__":
    main() 