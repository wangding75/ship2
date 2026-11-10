"""Development regression, isolated copies only; no GPU and no acceptance claim."""
import collections
import json
import math
import sys
from pathlib import Path
import bpy
from mathutils import Matrix

sys.path.insert(0,str(Path(__file__).resolve().parent))
import persistent_assembly as assembly

out=Path(sys.argv[sys.argv.index('--')+1]).resolve(); out.mkdir(parents=True,exist_ok=True)
rows=[]

def directed_corners(obj, material_names=True):
    m=obj.data; matrix=obj.matrix_world
    result=[]
    for p in m.polygons:
        loops=list(p.loop_indices)
        if matrix.determinant()<0: loops.reverse()
        corners=[]
        for li in loops:
            co=matrix @ m.vertices[m.loops[li].vertex_index].co
            corners.append((tuple(co),tuple(m.uv_layers[0].data[li].uv)))
        # Cyclic rotations are the same directed triangle; reversal is NOT.
        key=min(tuple(corners[i:]+corners[:i]) for i in range(3))
        result.append((m.materials[p.material_index].name,key))
    return collections.Counter(result)

def source_corners(asset,lod):
    result=collections.Counter()
    for name in assembly.PARTS:
        obj=assembly.part(asset,lod,name)
        if obj.type=='MESH': result.update(directed_corners(obj))
    return result

def assert_preview(asset,lod,mode):
    visible=[]
    for level in range(3):
        merged=bpy.data.objects[f'{asset}_LOD{level}_Assembled']
        if not merged.hide_render: visible.append(merged.name)
        for name in assembly.PARTS:
            ob=assembly.part(asset,level,name)
            if ob.type=='MESH' and not ob.hide_render: visible.append(ob.name)
    expected=[f'{asset}_LOD{lod}_Assembled'] if mode=='assembled' else [assembly.part(asset,lod,n).name for n in assembly.PARTS if assembly.part(asset,lod,n).type=='MESH']
    assert sorted(visible)==sorted(expected),(visible,expected)
    for name in visible: assert not bpy.data.objects[name].hide_viewport
    return visible

# Real modifications include vertex edit, translation, nonuniform scale and a
# negative determinant. The reference compares directed triangles and UV/material
# independently of the assembler's indexed output layout.
for asset in assembly.ASSETS:
    for lod in range(3):
        reef=assembly.part(asset,lod,'Reef')
        reef.location.x+=3.25
        reef.rotation_euler.z=0.2
        reef.scale=(-1.0,1.25,0.75)
        reef.data.vertices[0].co.z+=0.125
        if asset!='ISL-S': assembly.part(asset,lod,'Trees').location.y-=2.0
bpy.context.view_layer.update()
for asset in assembly.ASSETS:
    for lod in range(3):
        expected=source_corners(asset,lod)
        merged,counts=assembly.assemble(asset,lod)
        assert directed_corners(merged)==expected,(asset,lod,'directed geometry/UV/material mismatch')
        first=assembly.snapshot(merged)
        merged,_=assembly.assemble(asset,lod)
        assert first==assembly.snapshot(merged),(asset,lod,'nondeterminism')
        # Check transformed source normals against stored output corner normals;
        # Blender stores unit vectors, so report the actual angular deviation.
        expected_normals=[]
        for name in assembly.PARTS:
            ob=assembly.part(asset,lod,name)
            if ob.type!='MESH': continue
            nm=ob.matrix_world.to_3x3().inverted().transposed()
            for p in ob.data.polygons:
                loops=list(p.loop_indices)
                if ob.matrix_world.determinant()<0: loops.reverse()
                expected_normals.extend((nm @ ob.data.corner_normals[i].vector).normalized() for i in loops)
        dots=[max(-1,min(1,a.dot(b.vector))) for a,b in zip(expected_normals,merged.data.corner_normals)]
        assert min(dots)>0.99999,(asset,lod,'normal direction changed')
        rows.append(dict(asset=asset,lod=lod,edited_directed_geometry_uv_material_equal=True,
                         deterministic_mesh_data=True,min_normal_dot=min(dots),triangles=counts))
    assembly.preview(asset,0,'assembled')
before={o.name:assembly.snapshot(o) for o in bpy.data.objects if o.get('t07_role')=='assembled_lod'}
copy=out/'edited-reassembled.blend'
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(copy)); bpy.ops.wm.open_mainfile(filepath=str(copy))
assert before=={n:assembly.snapshot(bpy.data.objects[n]) for n in before}
previews=[]
for mode in ('parts','assembled'):
    for lod in range(3):
        for asset in assembly.ASSETS: assembly.preview(asset,lod,mode)
        bpy.ops.wm.save_as_mainfile(filepath=str(copy)); bpy.ops.wm.open_mainfile(filepath=str(copy))
        for asset in assembly.ASSETS:
            previews.append(dict(asset=asset,lod=lod,mode=mode,visible=assert_preview(asset,lod,mode)))
# Negative case must fail instead of producing a silent three-part M island.
bad=bpy.data.objects['ISL-M_LOD0_Trees']; bad.name='missing_Trees'
try:
    assembly.assemble('ISL-M',0)
    raise AssertionError('Missing required part was accepted')
except ValueError: pass
bad.name='ISL-M_LOD0_Trees'
(out/'mutation-regression.json').write_text(json.dumps(dict(development='PASS',acceptance='NOT_RUN',
    rows=rows,preview_save_reopen=previews,edited_mesh_save_reopen_exact=True,
    missing_required_part_rejected=True,normal_direction_regression_dot_floor=0.99999,
    note='Normal dot floor is a development corruption check, not a replacement precision/visual acceptance threshold.'),indent=2),encoding='utf-8')
print('DEVELOPMENT: 9 edited assemblies, directed triangles/UV/material, deterministic rebuild, exact reopen, 18 persisted preview modes, negative missing-part test passed')
