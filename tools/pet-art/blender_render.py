"""Run inside Blender (background): import OBJs with textures and render front and 3/4 views.

blender.exe -b --factory-startup --python blender_render.py -- <out.png> <a.obj> [<b.obj> ...]
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
scene.render.resolution_x = 360 * max(2, 2 * len(objs))
scene.render.resolution_y = 520
scene.render.film_transparent = False
scene.world = bpy.data.worlds.new("w")
scene.world.color = (0.12, 0.13, 0.15)

spacing = 90.0
cameras = []
for index, path in enumerate(objs):
    before = set(bpy.data.objects)
    bpy.ops.wm.obj_import(filepath=path, forward_axis="Y", up_axis="Z")
    imported = [o for o in bpy.data.objects if o not in before]
    for pose, yaw in enumerate((0.0, 35.0)):
        offset = (index * 2 + pose) * spacing
        if pose == 0:
            group = imported
        else:
            group = []
            for o in imported:
                copy = o.copy()
                copy.data = o.data
                scene.collection.objects.link(copy)
                group.append(copy)
        for o in group:
            o.rotation_euler = (0, 0, math.radians(yaw))
            o.location = Vector((offset, 0, 0))
    for o in imported:
        for slot in o.material_slots:
            tex = [n for n in slot.material.node_tree.nodes if n.type == "TEX_IMAGE"]
            print("MATERIAL", o.name, slot.material.name, "texture:",
                  tex[0].image.filepath if tex and tex[0].image else None,
                  "size:", tuple(tex[0].image.size) if tex and tex[0].image else None)

count = len(objs) * 2
cam_data = bpy.data.cameras.new("cam")
cam_data.type = "ORTHO"
cam_data.ortho_scale = spacing * count * 1.0
cam = bpy.data.objects.new("cam", cam_data)
scene.collection.objects.link(cam)
cam.location = Vector(((count - 1) * spacing / 2, -400, 36))
cam.rotation_euler = (math.radians(90), 0, 0)
scene.camera = cam
scene.render.resolution_x = int(scene.render.resolution_y * count * spacing / 110)
cam_data.sensor_fit = "HORIZONTAL"
scene.render.filepath = out_png
bpy.ops.render.render(write_still=True)
print("RENDERED", out_png)
