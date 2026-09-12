import argparse

from email_service.email_processor import process_unread_emails, run_forever


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Company AI email listener"
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Check the inbox once and then stop",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=5,
        help="Seconds to wait between inbox checks",
    )

    args = parser.parse_args()

    if args.once:
        process_unread_emails()
    else:
        run_forever(args.interval)
