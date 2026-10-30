"""Checks of the modern-test package builder's file selection and server configuration (build_modern_test_package.py)."""
import tempfile
import unittest
from pathlib import Path
import build_modern_test_package as b


class ModernPackageTests(unittest.TestCase):
    def test_no_client_profile_or_personal_file_is_copied(self):
        for path in ['client-modern/app/game.dll', 'modern-client.json', 'client-patch.json', 'account.txt', 'logs/server.log',
                     'data/opendaoc.sqlite3.db', 'server/logs/x.txt', 'modern-profile-verification.json']:
            self.assertFalse(b.keep_runtime(Path(path)), path)
        for path in ['server/GameServer.dll', 'server/navmesh/roads.json', 'OfflineDAoC.exe', 'server/config/serverconfig.xml']:
            self.assertTrue(b.keep_runtime(Path(path)), path)

    def test_the_world_path_becomes_package_relative(self):
        with tempfile.TemporaryDirectory() as folder:
            config = Path(folder) / 'serverconfig.xml'
            config.write_text('<root><Server><IP>127.0.0.1</IP><Port>10330</Port><AutoAccountCreation>False</AutoAccountCreation>'
                              '<DBConnectionString>Data Source=C:\\Users\\someone\\runtime\\data\\opendaoc.sqlite3.db;Version=3'
                              '</DBConnectionString></Server></root>', encoding='utf-8')
            b.server_config(config)
            text = config.read_text(encoding='utf-8')
            self.assertIn('Data Source=../data/opendaoc.sqlite3.db;Version=3', text)
            self.assertIn('<AutoAccountCreation>True</AutoAccountCreation>', text)
            self.assertNotIn('someone', text)

    def test_host_for_friends_is_switched_off(self):
        with tempfile.TemporaryDirectory() as folder:
            config = Path(folder) / 'serverconfig.xml'
            config.write_text('<root><Server>\n<Port>10330</Port>\n<IP>0.0.0.0</IP>\n<RegionIP>127.0.0.1</RegionIP>\n'
                              '<UdpIP>0.0.0.0</UdpIP>\n<EnableUPnP>True</EnableUPnP>\n<PublicIP>auto</PublicIP>\n'
                              '<AutoAccountCreation>False</AutoAccountCreation>\n<DBConnectionString>Data Source=x.db;Version=3</DBConnectionString>\n</Server></root>',
                              encoding='utf-8')
            b.server_config(config)
            text = config.read_text(encoding='utf-8')
            for line in ('<IP>127.0.0.1</IP>', '<UdpIP>127.0.0.1</UdpIP>', '<EnableUPnP>False</EnableUPnP>',
                         '<RegionIP>127.0.0.1</RegionIP>'):
                self.assertIn(line, text)
            self.assertNotIn('PublicIP', text)
        self.assertFalse(b.keep_runtime(Path('server/config/serverconfig.before-host-for-friends.xml')))


if __name__ == '__main__':
    unittest.main()
