from pathlib import Path
from PIL import Image

for image in Path( "static/images/heroes" ).iterdir():
    Image.open( image ).transpose( method = Image.Transpose.FLIP_TOP_BOTTOM ).save( image.with_suffix( ".png" ) )
