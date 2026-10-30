"""Blender (background), FLAT light: upper-body close-up (front, 3/4, side) of each OBJ, one row each.
blender.exe -b --factory-startup --python views_upper.py -- <out.png> <a.obj> [...]"""
import math, sys
import bpy
from mathutils import Vector
args = sys.argv[sys.argv.index("--") + 1:]
out_png, objs = args[0], args[1:]
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.engine = "BLENDER_WORKBENCH"
sc.display.shading.light = "FLAT"
sc.display.shading.color_type = "TEXTURE"
sc.view_settings.view_transform = "Standard"
sc.world = bpy.data.worlds.new("w"); sc.world.color = (0.33, 0.35, 0.39)
YAWS = (0.0, 40.0, 90.0)
CELL = 64.0
for row, path in enumerate(objs):
    before = set(bpy.data.objects)
    bpy.ops.wm.obj_import(filepath=path, forward_axis="Y", up_axis="Z")
    imp = [o for o in bpy.data.objects if o not in before]
    bpy.context.view_layer.update()
    zs = [(o.matrix_world @ Vector(c)).z for o in imp for c in o.bound_box]
    top = max(zs)
    for col, yaw in enumerate(YAWS):
        grp = imp if col == 0 else []
        if col:
            for o in imp:
                c = o.copy(); c.data = o.data; sc.collection.objects.link(c); grp.append(c)
        for o in grp:
            o.rotation_euler = (0, 0, math.radians(yaw))
            o.location = Vector((col * CELL, 0, -row * CELL - (top - 26.0)))
cd = bpy.data.cameras.new("c"); cd.type = "ORTHO"; cd.ortho_scale = CELL * len(YAWS)
cd.clip_start = 0.1; cd.clip_end = 100000
cam = bpy.data.objects.new("c", cd); sc.collection.objects.link(cam)
cam.location = Vector(((len(YAWS) - 1) * CELL / 2, -500, -(len(objs) - 1) * CELL / 2))
cam.rotation_euler = (math.radians(90), 0, 0); sc.camera = cam
sc.render.resolution_x = 360 * len(YAWS); sc.render.resolution_y = 360 * len(objs)
sc.render.filepath = out_png
bpy.ops.render.render(write_still=True)
