"""Blender (background): render weapon OBJs side by side, front and side views.

blender.exe -b --factory-startup --python blender_weapons.py -- <out.png> <a.obj> [...]
"""
import math
import sys

import bpy
from mathutils import Vector

args = sys.argv[sys.argv.index("--") + 1:]
out_png, objs = args[0], args[1:]
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.engine = "BLENDER_WORKBENCH"
scene.display.shading.light = "STUDIO"
scene.display.shading.color_type = "TEXTURE"
scene.world = bpy.data.worlds.new("w")
scene.world.color = (0.12, 0.13, 0.15)

spacing = 40.0
column = 0
for path in objs:
    before = set(bpy.data.objects)
    bpy.ops.wm.obj_import(filepath=path, forward_axis="Y", up_axis="Z")
    imported = [o for o in bpy.data.objects if o not in before]
    # Longest axis up so maces and shields both stand.
    size = Vector((0, 0, 0))
    for o in imported:
        size = Vector(max(a, b) for a, b in zip(size, o.dimensions))
    tilt = (math.radians(90), 0, 0) if size.y > size.z and size.y >= size.x else (0, math.radians(90), 0) if size.x > size.z else (0, 0, 0)
    for view, yaw in enumerate((0.0, 180.0)):
        group = imported if view == 0 else []
        if view:
            for o in imported:
                copy = o.copy()
                copy.data = o.data
                scene.collection.objects.link(copy)
                group.append(copy)
        for o in group:
            o.rotation_mode = "XYZ"
            o.rotation_euler = tilt
            o.location = Vector((column * spacing, 0, 0))
            o.rotation_euler.rotate_axis("Z", math.radians(yaw))
        column += 1

cam_data = bpy.data.cameras.new("cam")
cam_data.type = "ORTHO"
cam_data.ortho_scale = spacing * column
cam = bpy.data.objects.new("cam", cam_data)
scene.collection.objects.link(cam)
cam.location = Vector(((column - 1) * spacing / 2, -300, 0))
cam.rotation_euler = (math.radians(90), 0, 0)
scene.camera = cam
scene.render.resolution_y = 480
scene.render.resolution_x = int(480 * column * spacing / 48)
cam_data.sensor_fit = "HORIZONTAL"
scene.render.filepath = out_png
bpy.ops.render.render(write_still=True)
