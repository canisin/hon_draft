from pathlib import Path
from PIL import Image

new_heroes = ( "riptide", "kinesis", "cthulhuphant", "ravenor" )

for image in Path( "static/images/heroes/reborn" ).iterdir():
    if image.stem in new_heroes:
        Image.open( image ) \
            .transpose( method = Image.Transpose.FLIP_TOP_BOTTOM ) \
            .save( image.with_suffix( ".png" ) )
