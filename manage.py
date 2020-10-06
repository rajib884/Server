#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys


def main():
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'PythonServer.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    if len(sys.argv) == 1:
        # Run Server
        sys.argv.append("runserver")
        sys.argv.append("--noreload")
        sys.argv.append("192.168.0.103:8000")

        # Make migrations
        # sys.argv.append("makemigrations")
        # sys.argv.append("MoeList")

        # Check deploy
        # sys.argv.append("check")
        # sys.argv.append("--deploy")

        # Create App
        # sys.argv.append("startapp")
        # sys.argv.append("browser")
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
