#!/usr/bin/python3

import os
import sys
import requests
import argparse
from urllib.parse import urlparse


def dl(url, out):

    u = urlparse(url)

    p = u.path.split('/')

    print(p)

    f = p[len(p)-1]

    print("File out:", f)

    if out:
        f = out

    with open(f, "wb") as f_out:

        data = requests.get(url)

        if data.status_code == 200:
            f_out.write(data.content)
            print("File:", len(data.content), "data written")
        else:
            print("Error: ", data.status_code)


def main():

    parser = argparse.ArgumentParser(description='url downloader tester')
    parser.add_argument("-o", "--output", help="Output file")
    parser.add_argument(dest="url", help="Url to download")

    args = parser.parse_args()

    dl(args.url, args.output)


if __name__ == '__main__':
    main()
