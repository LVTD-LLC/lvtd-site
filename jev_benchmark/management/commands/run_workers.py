"""Supervise existing Django-Q and the long-lived benchmark coordinator."""

import signal
import subprocess
import sys
import time

from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Supervise Django-Q and the durable benchmark queue."

    def handle(self, *args, **options):
        children = []
        stopping = False

        def stop(*_):
            nonlocal stopping
            stopping = True
            for child in children:
                if child.poll() is None:
                    child.terminate()

        for sig in (signal.SIGTERM, signal.SIGINT):
            signal.signal(sig, stop)
        try:
            for command in (["qcluster"], ["work_jev_benchmark", "--watch"]):
                children.append(
                    subprocess.Popen([sys.executable, "manage.py", *command])
                )
            while all(child.poll() is None for child in children):
                time.sleep(1)
            if not stopping:
                raise CommandError(
                    "Worker child exited; supervisor stopping. "
                    "Deployment restart policy must restart it."
                )
        finally:
            stop()
            for child in children:
                try:
                    child.wait(timeout=1200)
                except subprocess.TimeoutExpired:
                    child.kill()
                    child.wait()
