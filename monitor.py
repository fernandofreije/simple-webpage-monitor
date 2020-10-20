from yaml import safe_load
from tinydb import TinyDB, Query
from dhooks import Webhook
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import logging
import datetime
import asyncio
import re

TAG_RE = re.compile(r'<[^>]+>')


class Monitor:
    def __init__(self):
        with open('config/pages.yml', 'r') as pages_file, open('config/config.yml') as config_file:
            self.pages = safe_load(pages_file)
            self.config = safe_load(config_file)
        now = datetime.datetime.now()
        logging.basicConfig(filename=f'log/DEBUG-{now.day}-{now.month}-{now.year}.log' if self.config['log_level'] == 'DEBUG' else f'log/{now.day}-{now.month}-{now.year}.log',
                            filemode='a',
                            format='%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s',
                            datefmt='%H:%M:%S',
                            level=logging.DEBUG if self.config['log_level'] == 'DEBUG' else logging.INFO)
        self.db = Database()
        self.notifier = DiscordNotifier(self.config['webhook_url'])

    def close(self):
        self.db.clearAll()
        self.db.close()
        self.notifier.close()

    async def run(self):
        await asyncio.gather(*[self.check_page(
            name, page['url'], page['selector'], page['refresh_time']) for name, page in self.pages.items()])

    async def check_page(self, name, url, selector, refresh_time):
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        driver = webdriver.Chrome(
            self.config['driver_path'], options=chrome_options)
        while True:
            logging.info(f'checking {url}')
            driver.get(url)
            logging.debug(driver.page_source)
            html = None
            try:
                html = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, selector))).get_attribute("innerHTML")
                html = TAG_RE.sub('', html)
                html = html.replace("\n", " ").replace('\t', "")
                html = re.sub(' +', ' ', html)

            except Exception as e:
                logging.error(e)
            if not html:
                logging.error(
                    f'{selector} does not find results')
                await asyncio.sleep(int(refresh_time))
                continue
            logging.info(f'html for {name} is {html}')
            diff = self.db.checkDiff(name, html)
            if (diff):
                logging.info(f'{name} has changed!')
                self.notifier.notify(name, url, diff)
            await asyncio.sleep(int(refresh_time))


class Database:
    def __init__(self):
        self.db = TinyDB('db/db.json')

    def close(self):
        self.db.close()

    def clearAll(self):
        self.db.truncate()

    def __insertVersion(self, name, html):
        self.db.insert({'name': name, 'html': html})

    def __updateVersion(self, name, html):
        self.db.update({'html': html}, Query().name == name)

    def checkDiff(self, name, html):
        pages = self.db.search(Query().name == name)
        if not pages:
            self.__insertVersion(name, html)
            return None

        if (pages[0]['html'] != html):
            self.__updateVersion(name, html)
            return {'old_html': pages[0]['html'], 'new_html': html}

        return None


class DiscordNotifier:
    def __init__(self, webhook):
        self.webhook = Webhook(webhook)

    def close(self):
        self.webhook.close()

    def notify(self, name, url, diff):
        self.webhook.send(
            f'*{name}* - ({url}) has html has changed from: \n `{diff["old_html"]}` \n --------------------------------------- \n `{diff["new_html"]}`')


if __name__ == "__main__":
    monitor = Monitor()
    try:
        asyncio.run(monitor.run())
    except KeyboardInterrupt:
        monitor.close()
