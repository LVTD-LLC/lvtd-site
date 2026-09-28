import signal
import threading

from django.core.management.base import BaseCommand, CommandError

from jev_benchmark.queue import run_queue


class Command(BaseCommand):
    help = "Process missing work; --watch discovers new jobs and due retries."

    def add_arguments(self, parser):
        parser.add_argument("--watch", action="store_true")
        parser.add_argument("--workers", type=int, default=8)
        parser.add_argument("--max-requests", type=int, default=5000)
        parser.add_argument("--poll-seconds", type=int, default=30)

    def handle(self, *args, **options):
        if (
            options["watch"]
            and threading.current_thread() is not threading.main_thread()
        ):
            raise CommandError(
                "Watch mode must run in the main thread for signal handling."
            )
        stop = threading.Event()
        if threading.current_thread() is threading.main_thread():
            for sig in (signal.SIGTERM, signal.SIGINT):
                signal.signal(sig, lambda *_: stop.set())
        while not stop.is_set():
            try:
                stats = run_queue(
                    workers=options["workers"],
                    max_requests=options["max_requests"],
                    report=self.stdout.write,
                    stop_requested=stop.is_set,
                )
                if any(stats.values()):
                    self.stdout.write(str(stats))
            except (RuntimeError, ValueError) as error:
                self.stderr.write(str(error))
                if not options["watch"]:
                    raise
            if not options["watch"]:
                break
            stop.wait(max(10, options["poll_seconds"]))
