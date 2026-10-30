"""Run inside Blender (background): import OBJs and render each from front, 3/4, side and back.

blender.exe -b --factory-startup --python blender_views.py -- <out.png> <a.obj> [<b.obj> ...]
Every OBJ gets one row of four views, auto-framed on its bounding box.
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
scene.display.shading.show_specular_highlight = False
scene.view_settings.view_transform = "Standard"
scene.world = bpy.data.worlds.new("w")
scene.world.color = (0.10, 0.11, 0.13)

YAWS = (0.0, 35.0, 90.0, 180.0)
cell = 0.0
rows = []
for path in objs:
    before = set(bpy.data.objects)
    bpy.ops.wm.obj_import(filepath=path, forward_axis="Y", up_axis="Z")
    imported = [o for o in bpy.data.objects if o not in before]
    bpy.context.view_layer.update()
    corners = [o.matrix_world @ Vector(c) for o in imported for c in o.bound_box]
    lo = Vector((min(c.x for c in corners), min(c.y for c in corners), min(c.z for c in corners)))
    hi = Vector((max(c.x for c in corners), max(c.y for c in corners), max(c.z for c in corners)))
    centre = (lo + hi) / 2
    cell = max(cell, (hi - lo).length * 1.05)
    rows.append((imported, centre))

for row, (imported, centre) in enumerate(rows):
    for column, yaw in enumerate(YAWS):
        group = imported if column == 0 else []
        if column:
            for o in imported:
                copy = o.copy()
                copy.data = o.data
                scene.collection.objects.link(copy)
                group.append(copy)
        for o in group:
            o.rotation_euler = (0, 0, math.radians(yaw))
            o.location = Vector((column * cell, 0, -row * cell)) - centre

cam_data = bpy.data.cameras.new("cam")
cam_data.type = "ORTHO"
cam_data.ortho_scale = cell * len(YAWS)
cam_data.clip_start = 0.1
cam_data.clip_end = 100000.0
cam = bpy.data.objects.new("cam", cam_data)
scene.collection.objects.link(cam)
cam.location = Vector(((len(YAWS) - 1) * cell / 2, -10 * cell, -(len(rows) - 1) * cell / 2))
cam.rotation_euler = (math.radians(90), 0, 0)
scene.camera = cam
cam_data.sensor_fit = "HORIZONTAL"
scene.render.resolution_x = 420 * len(YAWS)
scene.render.resolution_y = 520 * len(rows)
scene.render.filepath = out_png
bpy.ops.render.render(write_still=True)
print("RENDERED", out_png)
