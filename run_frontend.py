"""
CLI launcher for the Production RAG AI Assistant Streamlit Frontend.
Usage:
    python run_frontend.py [--port 8501] [--api-url http://localhost:8000]
"""
import argparse
import os
import subprocess
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def main():
    parser = argparse.ArgumentParser(description="Launch the Production RAG Assistant Python Web UI.")
    parser.add_argument("--port", type=int, default=8501, help="Port to run Streamlit on (default: 8501)")
    parser.add_argument("--api-url", type=str, default="http://localhost:8000", help="FastAPI backend URL (default: http://localhost:8000)")
    args = parser.parse_args()

    script_dir = Path(__file__).resolve().parent
    app_path = script_dir / "production-rag-ai-assistant" / "frontend" / "dashboard.py"
    if not app_path.exists():
        app_path = script_dir / "frontend" / "dashboard.py"

    if not app_path.exists():
        print(f"Error: Could not find frontend entrypoint at {app_path}")
        sys.exit(1)

    os.environ["API_BASE_URL"] = args.api_url

    print("=" * 65)
    print("Launching Production RAG Assistant Frontend")
    print(f"Target Backend API: {args.api_url}")
    print(f"Streamlit Web UI:   http://localhost:{args.port}")
    print("=" * 65)

    cmd = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        str(app_path),
        f"--server.port={args.port}",
        "--server.headless=true",
        "--theme.base=dark",
        "--theme.primaryColor=#6366F1",
        "--theme.backgroundColor=#0B0F17",
        "--theme.secondaryBackgroundColor=#131B2A",
        "--theme.textColor=#F8FAFC",
    ]

    project_root = app_path.parent.parent

    try:
        subprocess.run(cmd, check=True, cwd=str(project_root))
    except KeyboardInterrupt:
        print("\nFrontend stopped.")


if __name__ == "__main__":
    main()

