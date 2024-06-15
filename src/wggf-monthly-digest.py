#!/usr/bin/env python

import argparse
import asyncio
from pathlib import Path
from typing import TypedDict
from datetime import datetime
import logging
import aiohttp

logger = logging.getLogger(__name__)
logging.basicConfig(handlers=[logging.StreamHandler()], level=logging.INFO)

AUTH_URL = "https://list.genealogy.net/mm/private/westfalengen/"
DATA_URL = "https://list.genealogy.net/mm/archiv/westfalengen/"


class Options(TypedDict):
    username: str
    password: str
    out_dir: Path
    verbose: bool


def parse_args() -> Options:
    parser = argparse.ArgumentParser(
        description="Utility to scrape the mailing list archive of WGGF https://www.wggf.de."
    )

    parser.add_argument(
        "out_dir",
        type=str,
        help="Directory to store the scraped data. Will be created, if non existent.",
    )

    parser.add_argument(
        "-u",
        "--username",
        type=str,
        help="Your member username you would usually use to authenticate.",
        required=True,
    )
    parser.add_argument(
        "-p",
        "--password",
        type=str,
        help="Your member password you would usually use to authenticate.",
        required=True,
    )

    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Print verbose output.",
    )

    args = parser.parse_args()

    if args.verbose:
        logger.setLevel(logging.DEBUG)

    out_dir = Path(args.out_dir)
    if not out_dir.exists():
        out_dir.mkdir(parents=True)
        logger.debug(f"Output directory not existent, created it {out_dir.absolute()}")

    options: Options = {
        "out_dir": Path(args.out_dir),
        "username": args.username,
        "password": args.password,
        "verbose": args.verbose,
    }

    return options


# source: https://stackoverflow.com/a/34325723
class ProgressBar:
    def __init__(
        self,
        *,
        total: int,
        prefix: str = "",
        suffix: str = "",
        decimals: int = 1,
        length: int = 100,
        fill: str = "█",
        printEnd: str = "\r",
    ):
        self.iteration = 0
        self.total = total
        self.prefix = prefix
        self.suffix = suffix
        self.decimals = decimals
        self.length = length
        self.fill = fill
        self.printEnd = printEnd

        self.finished = False

    def update(self, iteration: int):
        if self.finished:
            return

        percent = ("{0:." + str(self.decimals) + "f}").format(
            100 * (iteration / float(self.total))
        )
        filledLength = int(self.length * iteration // self.total)
        bar = self.fill * filledLength + "-" * (self.length - filledLength)
        print(f"\r{self.prefix} |{bar}| {percent}% {self.suffix}", end=self.printEnd)

        # Print New Line on Complete
        if iteration == self.total:
            self.__finish()

    def __finish(self):
        self.finished = True
        print("\n")


def data_url(year: int, month: int) -> str:
    # example: "https://list.genealogy.net/mm/archiv/westfalengen/2024-06/2024-06f.html"
    # each month (if existent) follow the above schema
    year_str = str(year)
    # add leading zero if month is less than 10
    month_str = f"{month:02d}"
    url = DATA_URL + f"{year_str}-{month_str}/{year_str}-{month_str}f.html"
    return url


def url_to_filename(url: str) -> str:
    # example: "https://list.genealogy.net/mm/archiv/westfalengen/2024-06/2024-06f.html"
    # extract the year and month from the url and return a filename
    year_str = url.split("/")[-1].split("-")[0]
    month_str = url.split("/")[-1].split("-")[1].replace("f.html", "")
    return f"wggf-monthly-digest-{year_str}-{month_str}"


def is_empty(body: str) -> bool:  # type: ignore
    # a html body will be send back with a message if the monthly digest is empty
    try:
        return "existiert nicht" in body and len(body) < 100
    except Exception as e:
        logger.error(
            f"Failed to check if digest is empty. Fallback to returning non empty case. Error: {e}"
        )
        return False


async def get_digest(
    url: str, session: aiohttp.ClientSession
) -> tuple[Path, str] | None:
    response = await session.get(url)

    try:
        # TODO: fix decoding errors
        body = await response.text(encoding="utf-8", errors="ignore")
    except Exception as e:
        logger.error(f"Failed to decode response body {url} with error: {e}")
        return

    if is_empty(body):
        logger.debug(f"Skipping empty monthly digest {url}")
        return

    if response.status == 200:
        logger.debug(f"Found monthly digest {url}")
        filename = url_to_filename(str(response.url)) + ".html"
        path = Path(options["out_dir"], filename).absolute()
        return path, body

    logger.error(f"Failed to scrape {url}")
    return


async def write_digest(body: str, file: Path):
    with open(file, "w", encoding="utf-8") as f:
        f.write(body)
        logger.debug(f"Saved monthly digest to {file}")


async def fetch(urls: list[str], options: Options, pb: None | ProgressBar):
    body = {"username": options["username"], "password": options["password"]}
    tasks = []
    auth_session = aiohttp.ClientSession()
    async with auth_session as session:
        await session.post(AUTH_URL, data=body)  # authenticate once via session cookie
        tasks = [get_digest(url, session) for url in urls]

        for idx, task in enumerate(asyncio.as_completed(tasks)):
            if pb:
                pb.update(idx + 1)
            result = await task
            if result is not None:
                path, body = result
                await write_digest(body, path)

        # futures = await asyncio.gather(*tasks)
        # for future in futures:
        #     if future is not None:
        #         path, body = future
        #         await write_digest(body, path)


if __name__ == "__main__":
    now = datetime.now()
    options = parse_args()

    now_year = now.year
    years = range(2000, now_year + 1)
    months = range(1, 13)
    urls = [data_url(year, month) for year in years for month in months]
    logger.debug(f"Scraping monthly digests from {len(urls)} urls.")

    progress = (
        None
        if options["verbose"]
        else ProgressBar(
            total=len(urls), prefix="Progress:", suffix="Complete", length=50
        )
    )

    asyncio.run(fetch(urls, options, pb=progress))

    timedelta = datetime.now() - now
    logger.info(f"Files saved to {options['out_dir'].absolute()}.")
    logger.info(f"Completed scraping monthly digests in {timedelta.seconds} seconds.")
