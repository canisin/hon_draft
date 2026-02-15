import subprocess

command = "c:/Program Files/7-Zip/7z.exe x"
archive = "game_resources/reborn/resources0.jz"
output = "-ogame_resources/reborn"
filter = "heroes/*/base/icon.dds"
subprocess.run( f"{command} {archive} {output} {filter}" )

from pathlib import Path

for hero in Path( "game_resources/reborn/heroes" ).iterdir():
    icon = hero / "base/icon.dds"
    icon.rename( f"static/images/heroes/reborn/{ hero.name }.dds" )
