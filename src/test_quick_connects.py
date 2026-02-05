#!/usr/bin/env python3
import os
import random
import sys

from selenium import webdriver
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.edge.service import Service as EdgeService

# Ensure src is importable
HERE = os.path.dirname(__file__)
ROOT = os.path.abspath(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import bot_v2 as bot


def main():
    # Small run: reduce QUICK_CONNECT_LIMIT for focused testing
    bot.QUICK_CONNECT_LIMIT = 4

    opts = EdgeOptions()
    opts.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64)")
    width = random.randint(1024, 1366)
    height = random.randint(768, 900)
    opts.add_argument(f"--window-size={width},{height}")

    # Try to reuse existing Edge profile for session cookies
    ud = os.path.join(
        os.environ.get("USERPROFILE", ""),
        "AppData",
        "Local",
        "Microsoft",
        "Edge",
        "User Data",
    )
    if os.path.exists(ud):
        opts.add_argument(f"--user-data-dir={ud}")
        opts.add_argument("--profile-directory=Default")

    try:
        service = EdgeService(executable_path=bot.DRIVER_FILENAME)
        driver = webdriver.Edge(options=opts, service=service)
        driver.set_page_load_timeout(60)

        print(
            "[test_quick_connects] Iniciando run_quick_connects() com QUICK_CONNECT_LIMIT=4"
        )
        bot.run_quick_connects(driver)

    except Exception as e:
        print("[test_quick_connects] Erro durante execução:", e)
    finally:
        try:
            driver.quit()
        except:
            pass


if __name__ == "__main__":
    main()
