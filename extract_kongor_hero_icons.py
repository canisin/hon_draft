from pathlib import Path
import zipfile

not_found = []

archive = zipfile.ZipFile( "textures/textures.s2z", "r" )
heroes = zipfile.Path( archive, "00000000/heroes/" )
for hero in heroes.iterdir():
    print( f"Extracting {hero.name}.." )
    if not ( hero / "icon.dds" ).exists():
        not_found.append( hero.name )
        continue

    Path( f"static/images/heroes/{hero.name}.dds" ) \
        .write_bytes( archive.read( f"00000000/heroes/{hero.name}/icon.dds" ) )

print( "missing icons:" )
for missing_hero in not_found:
    print( missing_hero )
