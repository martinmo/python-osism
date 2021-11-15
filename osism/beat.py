import logging
import subprocess

from cliff.command import Command


class Run(Command):

    log = logging.getLogger(__name__)

    def take_action(self, parsed_args):
        p = subprocess.Popen(f"celery --broker=redis://redis beat", shell=True)
        p.wait()
