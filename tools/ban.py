from asyncio import create_subprocess_shell
from asyncio.subprocess import PIPE
from re import search

from config import NFTABLES_INPUT, NFTABLES_OUTPUT


class BanFail(Exception):

    def __init__(self, state=None):
        super().__init__()
        self.state = state


class Ban:

    ban_types = ('ban', 'slowban')
    commands = {
        'apply': 'nft add element inet %s "{ban_type}" "{{{ip}}}"' % NFTABLES_INPUT,
        'remove': 'nft delete element inet %s "{ban_type}" "{{{ip}}}"' % NFTABLES_OUTPUT,
    }

    def __init__(self, ban_type, action, timeout=None):
        if not timeout:
            timeout = '0s'
        timeout = str(timeout)
        try:
            int(timeout)
            timeout += 's'
        except ValueError:
            pass

        if not search('^(\d+d)?(\d+h)?(\d+m)?(\d+s)?$', timeout):
            raise BanFail('timeout_invalid')
        if action not in self.commands:
            raise BanFail('wrong_state')
        if ban_type not in self.ban_types:
            raise BanFail('wrong_type')

        self.action = action
        self.type = ban_type
        self.timeout = timeout
        self.template = self.commands[action]

    def __call__(self, ip_list):
        return self._ban(ip_list)

    @classmethod
    async def test_ban(cls):
        err = await cls._run_cmd("nft -v")
        if err:
            raise BanFail

    async def _ban(self, ip_list):
        if len(ip_list) == 0:
            raise BanFail('wrong_userid')

        err = await self._run_cmd(self._make_cmd(ip_list))
        if err:
            await self._handle_failure(ip_list)

        return self.action + '_ok'

    def _make_cmd(self, ip_list):
        if self.action == 'apply':
            ip_arg = ', '.join('%s timeout %s' % (ip, self.timeout)
                               for ip in ip_list)
        else:
            ip_arg = ', '.join(ip_list)
        return self.template.format(timeout=self.timeout,
                                    ban_type=self.type, ip=ip_arg)

    @staticmethod
    async def _run_cmd(cmd):
        process = await create_subprocess_shell(cmd, stderr=PIPE)
        code = await process.wait()
        stderr = await process.stderr.readline()
        if code == 0:
            return None
        else:
            return stderr.decode('utf-8').rstrip(" \n")

    async def _handle_failure(self, ip_list):
        """Removes all bans that we tried to set."""
        if self.action == 'apply':
            try:
                ban = Ban(self.type, 'remove')
                await ban(ip_list)
            except BanFail:
                raise BanFail('backend_failure')
        raise BanFail(self.action + '_fail')
