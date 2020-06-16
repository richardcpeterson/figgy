import sys

import pexpect
from figgy.test.cli.config import *
from figgy.test.cli.dev.get import DevGet
from figgy.test.cli.dev.delete import DevDelete
from figgy.test.cli.dev.put import DevPut

from figgy.test.cli.figgy import FiggyTest
from figgy.config import *
from figgy.utils.utils import *
import uuid
import time


class DevSync(FiggyTest):

    def __init__(self):
        super().__init__(None)
        self.missing_key = '/app/ci-test/v1/config12'

    def run(self):
        self.step("Preparing sync process...")
        self.prep_sync()
        self.step("Testing successful sync")
        self.sync_success()
        self.step("Testing multi-level sync")
        self.sync_multi_level_success()
        self.step("Testing sync with known orphaned parameters.")
        self.sync_with_orphans()

    def prep_sync(self):
        put = DevPut()
        put.add('/app/ci-test/v1/config9', DELETE_ME_VALUE, desc='desc', add_more=True)
        put.add('/app/ci-test/v1/config11', DELETE_ME_VALUE, desc='desc', add_more=True)
        put.add('/shared/jordan/testrepl', DELETE_ME_VALUE, desc='desc', add_more=True)
        put.add('/shared/jordan/testrepl2', DELETE_ME_VALUE, desc='desc', add_more=True)
        put.add('/shared/jordan/testrepl3', DELETE_ME_VALUE, desc='desc', add_more=True)
        put.add('/shared/jordan/testrepl4', DELETE_ME_VALUE, desc='desc', add_more=False)
        delete = DevDelete()
        delete.delete(self.missing_key)

    def sync_success(self):
        print(f"Testing: {CLI_NAME} config {Utils.get_first(sync)} --env {DEFAULT_ENV} "
              f"--config figgy/test/assets/success/figgy.json")
        child = pexpect.spawn(f'{CLI_NAME} config {Utils.get_first(sync)} --env {DEFAULT_ENV} '
                              f'--config figgy/test/assets/success/figgy.json --skip-upgrade',
                              encoding='utf-8', timeout=10)
        child.logfile = sys.stdout
        missing_key = '/app/ci-test/v1/config12'
        child.expect(f'.*Please input a value for.*{missing_key}.*')
        child.sendline(DELETE_ME_VALUE)
        child.expect('.*optional description:.*')
        child.sendline('desc')
        child.expect('.*value a secret.*')
        child.sendline('n')
        child.expect('.*Sync completed with no errors!')

    def sync_multi_level_success(self):
        missing_key = '/app/dev/thing/ci-test2/app/ci-test/v1/config12'
        delete = DevDelete()
        delete.delete(missing_key)

        put = DevPut()
        put.add('/app/dev/thing/ci-test2/config9', DELETE_ME_VALUE, desc='desc', add_more=True)
        put.add('/app/dev/thing/ci-test2/config11', DELETE_ME_VALUE, desc='desc', add_more=True)
        put.add('/shared/jordan/testrepl', DELETE_ME_VALUE, desc='desc', add_more=True)
        put.add('/shared/jordan/testrepl2', DELETE_ME_VALUE, desc='desc', add_more=True)
        put.add('/shared/jordan/testrepl3', DELETE_ME_VALUE, desc='desc', add_more=True)
        put.add('/shared/jordan/testrepl4', DELETE_ME_VALUE, desc='desc', add_more=False)

        print(f"Testing: {CLI_NAME} config {Utils.get_first(sync)} --env {DEFAULT_ENV} "
              f"--config figgy/test/assets/success/multi-level-ns.json")
        child = pexpect.spawn(f'{CLI_NAME} config {Utils.get_first(sync)} --env {DEFAULT_ENV} '
                              f'--config figgy/test/assets/success/multi-level-ns.json --skip-upgrade',
                              encoding='utf-8', timeout=10)

        child.expect(f'.*Please input a value for.*{missing_key}.*')
        child.sendline(DELETE_ME_VALUE)
        child.expect('.*optional description:.*')
        child.sendline('desc')
        child.expect('.*value a secret.*')
        child.sendline('n')
        child.expect('.*Sync completed with no errors!')

    def sync_with_orphans(self):
        delete = DevDelete()
        delete.delete(self.missing_key)
        print("Successful sync + cleanup passed!")

        print(f"Testing: {CLI_NAME} config {Utils.get_first(sync)} --env {DEFAULT_ENV} "
              f"--config figgy/test/assets/error/figgy.json")
        child = pexpect.spawn(f'{CLI_NAME} config {Utils.get_first(sync)} --env {DEFAULT_ENV} '
                              f'--config figgy/test/assets/error/figgy.json --skip-upgrade', timeout=10)
        child.expect('.*Unused Parameter:.*/app/ci-test/v1/config11.*Orphaned replication.*/shared/jordan/testrepl2.*')
        print("Sync with orphaned configs passed!")
