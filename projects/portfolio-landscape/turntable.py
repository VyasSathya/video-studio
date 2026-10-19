"""Render an existing GLB in background Blender. No model or game source is changed."""
import math,sys
from pathlib import Path
import bpy
from mathutils import Vector

args=sys.argv[sys.argv.index('--')+1:]
source=Path(args[0]);out=Path(args[1]);out.mkdir(parents=True,exist_ok=True)
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete()
bpy.ops.import_scene.gltf(filepath=str(source))
objects=list(bpy.context.scene.objects)
points=[o.matrix_world@Vector(c) for o in objects if o.type=='MESH' for c in o.bound_box]
lo=Vector(tuple(min(p[a] for p in points) for a in range(3)));hi=Vector(tuple(max(p[a] for p in points) for a in range(3)))
center=(lo+hi)*.5;size=max(hi-lo)
pivot=bpy.data.objects.new('Original asset',None);bpy.context.collection.objects.link(pivot);pivot.location=center
bpy.context.view_layer.update()
for o in objects:
    if o.parent is None:o.parent=pivot;o.matrix_parent_inverse=pivot.matrix_world.inverted()
pivot.location=(0,0,0)
pivot.rotation_euler[2]=0;pivot.keyframe_insert(data_path='rotation_euler',frame=1)
pivot.rotation_euler[2]=math.tau;pivot.keyframe_insert(data_path='rotation_euler',frame=97)
for action in bpy.data.actions:
    if hasattr(action,'fcurves'):
        for curve in action.fcurves:
            for key in curve.keyframe_points:key.interpolation='LINEAR'
def look(o,target=(0,0,0)):o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler()
bpy.ops.object.camera_add(location=(1.8*size,-3*size,1.3*size));camera=bpy.context.object;look(camera)
camera.data.type='ORTHO';camera.data.ortho_scale=size*2.7
scene=bpy.context.scene;scene.camera=camera
for name,loc,energy,color in [('Key',(2,-3,4),150,(1,.93,.82)),('Fill',(-3,-1,1),80,(.7,.82,1)),('Rim',(1,3,2),130,(.85,.94,1))]:
    bpy.ops.object.light_add(type='AREA',location=tuple(v*size for v in loc));o=bpy.context.object;o.name=name;o.data.energy=energy*size*size;o.data.size=3*size;o.data.color=color;look(o)
available=[i.identifier for i in scene.render.bl_rna.properties['engine'].enum_items]
scene.render.engine=next((x for x in ['BLENDER_EEVEE_NEXT','BLENDER_EEVEE'] if x in available),'CYCLES')
if hasattr(scene,'eevee') and hasattr(scene.eevee,'taa_render_samples'):scene.eevee.taa_render_samples=32
scene.world=scene.world or bpy.data.worlds.new('Neutral studio');scene.world.use_nodes=True
scene.world.node_tree.nodes['Background'].inputs['Color'].default_value=(.025,.03,.035,1)
scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.5
scene.view_settings.view_transform='AgX';scene.view_settings.exposure=-.4
scene.render.resolution_x=1920;scene.render.resolution_y=1080;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.render.fps=24;scene.frame_start=1;scene.frame_end=96
scene.render.filepath=str(out/'frame-');scene.render.film_transparent=False
scene.frame_set(1);scene.render.filepath=str(out/'preview.png');bpy.ops.render.render(write_still=True)
if '--preview' not in args:
    scene.render.filepath=str(out/'frame-');bpy.ops.render.render(animation=True)
