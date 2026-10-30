import json
import sqlite3
import sys


def main(database_path: str) -> None:
    cleanup = [
        "CharacterXDataQuest",
        "CharacterXMasterLevel",
        "CharacterXOneTimeDrop",
        "DOLCharactersXCustomParam",
        "DOLCharactersBackupXCustomParam",
        "DOLCharactersBackup",
        "DOLCharacters",
        "FactionAggroLevel",
        "Quest",
        "Task",
        "TimeXLevel",
        "PlayerXEffect",
        "PlayerBoats",
        "Inventory",
        "bot_settings",
        "bot_profiles",
        "offline_bot_commands",
        "offline_world_bots",
        "offline_auction_ledger",
        "offline_auction_escrow",
        "offline_auction_listings",
    ]
    with sqlite3.connect(database_path) as connection:
        connection.execute("PRAGMA foreign_keys=OFF")
        before = {
            table: connection.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
            for table in cleanup
        }
        for table in cleanup:
            connection.execute(f'DELETE FROM "{table}"')
        connection.execute(
            "UPDATE offline_runtime_status SET ServerState='Stopped', ServerPid=0, "
            "ActiveBots=0, WarmBots=0, ColdBots=0, ServerMemoryMb=0, "
            "TickP95Ms=0, AiWorkQueue=0"
        )
        connection.commit()
        connection.execute("VACUUM")
        after = {
            table: connection.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
            for table in cleanup
        }
        settings = {
            table: connection.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
            for table in (
                "offline_local_options",
                "offline_population_settings",
                "offline_auction_settings",
                "ServerProperty",
            )
        }
        print(json.dumps({
            "before": before,
            "after": after,
            "accounts": connection.execute("SELECT COUNT(*) FROM Account").fetchone()[0],
            "settings": settings,
        }, indent=2))


if __name__ == "__main__":
    main(sys.argv[1])
