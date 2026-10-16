import argparse
import pathlib

CLI = argparse.ArgumentParser(description="COBalD - the Opportunistic Balancing Daemon")
CLI.add_argument("CONFIGURATION", help="path to configuration", type=pathlib.Path)
CLI.add_argument(
    "--timeout", help="limit deamon run duration (for testing)", type=float
)
CLI_LOG = CLI.add_argument_group("Startup Logging")
CLI_LOG.add_argument(
    "--log-level",
    help="initial logging level",
    default="INFO",
    choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
    type=str.upper,
)
CLI_LOG.add_argument(
    "--log-target",
    help="initial logging target; stdout, stderr or a file path",
    default="stderr",
)
CLI_LOG.add_argument(
    "--log-journal",
    help="use short formatting suitable for journals",
    action="store_true",
)
