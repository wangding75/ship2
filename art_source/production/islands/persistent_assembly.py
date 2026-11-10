"""Offline persistent assembly. Hidden parts are retained, never discarded.
Run through assemble_island_parts.py; see RESCUE_WORKFLOW.md.
"""
import argparse
import json
import os
import sys
import shutil
from pathlib import Path
import bpy
from mathutils import Matrix

PARTS = ('Beach', 'Grass', 'Trees', 'Reef')
ASSETS = ('ISL-S', 'ISL-M', 'ISL-L')
CAPS = {'ISL-S': (1500,600,200), 'ISL-M': (3500,1400,400), 'ISL-L': (7000,2500,700)}

def part(asset,lod,name):
    obj=bpy.data.objects.get(f'{asset}_LOD{lod}_{name}')
    if obj is None: raise ValueError(f'Missing {asset} LOD{lod} {name}')
    if obj.type!='MESH' or not obj.data.polygons:
        if not (asset=='ISL-S' and name=='Trees' and obj.type=='EMPTY'):
            raise ValueError(f'Unexpected empty part: {obj.name}')
    return obj

def assemble(asset,lod):
    """Fixed ordered corner copy; inverse transpose normals; mirror winding.
    Bake edited source world transforms into an identity output. No welding.
    """
    objects=[part(asset,lod,p) for p in PARTS]
    vertices,faces,normals,uv,slots,smooth=[],[],[],[],[],[]
    materials=[objects[i].data.materials[0] for i in (0,1,3)]
    counts={}
    for name,obj in zip(PARTS,objects):
        if obj.type=='EMPTY':
            counts[name]=0
            continue
        if obj.modifiers: raise ValueError(f'Apply modifiers explicitly: {obj.name}')
        mesh=obj.data
        slot=0 if name=='Beach' else 1 if name=='Grass' else 2
        if len(mesh.materials)!=1 or mesh.materials[0]!=materials[slot]:
            raise ValueError(f'Material mapping differs: {obj.name}')
        if len(mesh.uv_layers)!=1: raise ValueError(f'Expected one production UVMap: {obj.name}')
        matrix=obj.matrix_world.copy()
        if matrix.determinant()==0: raise ValueError(f'Singular transform: {obj.name}')
        normal_matrix=matrix.to_3x3().inverted().transposed()
        counts[name]=sum(len(p.vertices)-2 for p in mesh.polygons)
        for polygon in mesh.polygons:
            if len(polygon.vertices)!=3: raise ValueError(f'Triangulate explicitly: {obj.name}')
            loops=list(polygon.loop_indices)
            if matrix.determinant()<0: loops.reverse()
            face=[]
            for li in loops:
                face.append(len(vertices))
                vertices.append(tuple(matrix @ mesh.vertices[mesh.loops[li].vertex_index].co))
                normals.append(tuple((normal_matrix @ mesh.corner_normals[li].vector).normalized()))
                uv.append(tuple(mesh.uv_layers[0].data[li].uv))
            faces.append(face); slots.append(slot); smooth.append(polygon.use_smooth)
    if sum(counts.values())>CAPS[asset][lod]: raise ValueError(f'Budget exceeded: {asset} LOD{lod} {counts}')
    name=f'{asset}_LOD{lod}_Assembled'
    mesh=bpy.data.meshes.new(name)
    mesh.from_pydata(vertices,[],faces)
    for material in materials: mesh.materials.append(material)
    layer=mesh.uv_layers.new(name='UVMap')
    for polygon,slot,smoothing in zip(mesh.polygons,slots,smooth):
        polygon.material_index=slot; polygon.use_smooth=smoothing
    for i,value in enumerate(uv): layer.data[i].uv=value
    mesh.normals_split_custom_set(normals); mesh.update()
    old=bpy.data.objects.get(name)
    if old:
        old_mesh=old.data
        bpy.data.objects.remove(old,do_unlink=True)
        if old_mesh.users==0: bpy.data.meshes.remove(old_mesh)
    mesh.name=name
    obj=bpy.data.objects.new(name,mesh)
    bpy.context.scene.collection.objects.link(obj)
    obj.matrix_world=Matrix.Identity(4)
    obj['t07_role']='assembled_lod'
    obj['t07_sources']=json.dumps([o.name for o in objects])
    return obj,counts

def preview(asset,lod,mode):
    if mode not in ('parts','assembled') or lod not in (0,1,2): raise ValueError('Invalid preview')
    for level in range(3):
        merged=bpy.data.objects.get(f'{asset}_LOD{level}_Assembled')
        if merged is None: raise ValueError('Assemble before changing preview')
        merged.hide_viewport=merged.hide_render=not (mode=='assembled' and level==lod)
        merged.hide_set(False)
        for name in PARTS:
            obj=part(asset,level,name); obj.hide_set(False)
            obj.hide_viewport=obj.hide_render=not (mode=='parts' and level==lod)
    bpy.context.scene[f't07_preview_{asset}']=f'{mode}:LOD{lod}'

def export(obj,path):
    bpy.ops.object.select_all(action='DESELECT')
    old=(obj.hide_viewport,obj.hide_render)
    obj.hide_viewport=obj.hide_render=False
    obj.select_set(True); bpy.context.view_layer.objects.active=obj
    try:
        bpy.ops.export_scene.fbx(filepath=str(path),use_selection=True,object_types={'MESH'},
            apply_scale_options='FBX_SCALE_UNITS',axis_forward='Y',axis_up='Z',bake_space_transform=True,
            apply_unit_scale=True,global_scale=1.0,mesh_smooth_type='FACE',use_mesh_modifiers=True,
            add_leaf_bones=False,colors_type='NONE',path_mode='STRIP',embed_textures=False)
    finally: obj.hide_viewport,obj.hide_render=old

def snapshot(obj):
    m=obj.data
    return dict(vertices=[list(v.co) for v in m.vertices],faces=[list(p.vertices) for p in m.polygons],
        normals=[list(n.vector) for n in m.corner_normals],uv=[list(v.uv) for v in m.uv_layers[0].data],
        slots=[p.material_index for p in m.polygons],materials=[m.name for m in m.materials],
        matrix=[list(r) for r in obj.matrix_world],source_references=obj['t07_sources'])

def main():
    root=Path(__file__).resolve().parent
    cur=Path(bpy.data.filepath).resolve() if bpy.data.filepath else None
    src=(root/'source'/'S1_T07_islands.blend').resolve()
    default_out=cur if (cur is not None and cur!=src) else (root/'source'/'S1_T07_reassembled.blend')
    default_rep=os.environ.get('T07_PART_REPORT') or str(root/'evidence'/'part_reassembly.json')
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',default=str(default_out))
    parser.add_argument('--export-dir',default=str(root/'export'/'reassembled'))
    parser.add_argument('--report',default=default_rep)
    argv=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
    args=parser.parse_args(argv)
    output,exports,report=map(lambda p:Path(p).resolve(),(args.output,args.export_dir,args.report))
    for p in (output.parent,exports,report.parent): p.mkdir(parents=True,exist_ok=True)
    # STRIP writes filename-only FBX references: place the two shared atlases beside exports.
    textures=Path(__file__).resolve().parent/'textures'
    for name in ('island_atlas_1024.png','island_atlas_512.png'):
        shutil.copyfile(textures/name,exports/name)
    before,rows={},[]
    for asset in ASSETS:
        for lod in range(3):
            obj,counts=assemble(asset,lod); before[obj.name]=snapshot(obj)
            export(obj,exports/f'{asset}_LOD{lod}.fbx')
            rows.append(dict(asset=asset,lod=lod,triangles=counts,slots=3))
        preview(asset,0,'assembled')
    bpy.context.preferences.filepaths.save_version=0
    bpy.ops.wm.save_as_mainfile(filepath=str(output)); bpy.ops.wm.open_mainfile(filepath=str(output))
    after={name:snapshot(bpy.data.objects[name]) for name in before}
    if before!=after: raise AssertionError('Saved geometry/corner data changed after reopening')
    payload=dict(status='DEVELOPMENT_OK',acceptance='NOT_RUN',saved_reopened_exact=True,outputs=rows,
                 preview={a:bpy.context.scene[f't07_preview_{a}'] for a in ASSETS})
    report.write_text(json.dumps(payload,indent=2)+'\n',encoding='utf-8'); print(json.dumps(payload))
