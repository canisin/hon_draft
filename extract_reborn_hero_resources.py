import subprocess
from pathlib import Path
from PIL import Image
import soundfile as sf

heroes = ( "*" )

command = "c:/Program Files/7-Zip/7z.exe x"
archive = "game_resources/reborn/resources0.jz"

if not Path( archive ).exists():
    print( "Failed to find reborn resources at game_resources/reborn" )
    quit

output = "-ogame_resources/reborn"
for hero in heroes:
    filter = f"heroes/{hero}/base/icon.dds"
    subprocess.run( f"{command} {archive} {output} {filter}" )
    filter = f"heroes/{hero}/base/sounds/voice/hero_select.*"
    subprocess.run( f"{command} {archive} {output} {filter}" )

new_icon_count = 0
conveted_sound_count = 0
new_sound_count = 0
for hero in Path( "game_resources/reborn/heroes" ).iterdir():
    target_icon = Path( f"static/images/heroes/reborn/{ hero.name }.png" )
    if target_icon.exists():
        print( f"Icon already exists for { hero.name }" )
    else:
        icon = hero / "base/icon.dds"
        if not icon.exists():
            print( f"Icon missing for { hero.name }" )
        else:
            Image.open( icon ) \
                .transpose( method = Image.Transpose.FLIP_TOP_BOTTOM ) \
                .save( icon.with_suffix( ".png" ) )
            icon = icon.with_suffix(  ".png" )
            icon.copy( target_icon )
            new_icon_count += 1

    target_sound = Path( f"static/sounds/heroes/reborn/{ hero.name }.ogg" )
    if target_sound.exists():
        print( f"Sound already exists for { hero.name }" )
    else:
        sound = hero / "base/sounds/voice/hero_select.wav"
        if sound.exists():
            print( f"Converting wave to ogg for { hero.name }" )
            data, samplerate = sf.read( sound )
            sf.write( sound.with_suffix( ".ogg" ), data, samplerate )
            converted_sound_count += 1
        sound = sound.with_suffix( ".ogg" )
        if not sound.exists():
            print( f"Sound missing or conversion failed for { hero.name }" )
        else:
            sound.copy( target_sound )
            new_sound_count += 1

print( f"{ new_icon_count } icons added" )
print( f"{ converted_sound_count } sounds converted" )
print( f"{ new_sound_count } sounds added" )
