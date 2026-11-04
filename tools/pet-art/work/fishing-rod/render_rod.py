"""Blender (background): the stock quarterstaff above the fishing rod, lying flat, textured, plus a close-up of the tip.

blender.exe -b --factory-startup --python render_rod.py -- <out.png> <texture> <quarterstaff.obj> <fishing_rod.obj>
"""
import sys

import bpy

args = sys.argv[sys.argv.index("--") + 1:]
out_png, texture, objs = args[0], args[1], args[2:]
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.engine = "BLENDER_WORKBENCH"
scene.display.shading.light = "FLAT"
scene.display.shading.color_type = "TEXTURE"
scene.world = bpy.data.worlds.new("w")
scene.world.color = (0.55, 0.62, 0.68)

material = bpy.data.materials.new("wood")
material.use_nodes = True
image = bpy.data.images.load(texture)
node = material.node_tree.nodes.new("ShaderNodeTexImage")
node.image = image
material.node_tree.links.new(node.outputs["Color"], material.node_tree.nodes["Principled BSDF"].inputs["Base Color"])

for row, path in enumerate(objs):
    before = set(bpy.data.objects)
    bpy.ops.wm.obj_import(filepath=path, forward_axis="Y", up_axis="Z")
    for o in set(bpy.data.objects) - before:
        o.data.materials.clear()
        o.data.materials.append(material)
        # Lie along X (the weapon's length is its Z), thickened 2x so the taper reads at this scale.
        o.rotation_euler = (0, 1.5708, 0)
        o.scale = (2, 2, 1)
        o.location = (0, -row * 14, 0)

camera = bpy.data.cameras.new("c")
camera.type = "ORTHO"
camera.ortho_scale = 140
cam = bpy.data.objects.new("c", camera)
scene.collection.objects.link(cam)
cam.location = (43, -7, 100)
scene.camera = cam
scene.render.resolution_x, scene.render.resolution_y = 1600, 420
scene.render.filepath = out_png
bpy.ops.render.render(write_still=True)
