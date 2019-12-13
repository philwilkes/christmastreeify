# christmastreeify
Turn your point clouds of trees into Christmas trees

<img align="center" width=400 src="sketchfab_animation.gif">

```
usage: christmasify.py [-h] --tree TREE [--sketchfab] [--zmin ZMIN]
                       [--vertical_spacing VERTICAL_SPACING] [--replace-brown]
                       [--snow] [--verbose]

optional arguments:
  -h, --help            show this help message and exit
  --tree TREE           the tree you want to christmastreeify
  --sketchfab           make sketchfab ready (creates .zip file for animation)
  --zmin ZMIN           bottom of the decorations e.g. bottom of crown
  --vertical_spacing VERTICAL_SPACING spacing between baubaul layers
  --replace-brown       replace the existing tree colour with a horrible brown
  --snow                add a snowy ground
  --verbose             print fun things to screen
  ```

For best results edit your point cloud first e.g. remove ground and noise etc.
