"""Real saved blend and binary FBX measurements; exact rational scalar rounding.
No cached metrics, no empirical tolerance, no Unity execution.
"""
import json,sys,struct,hashlib,math
from fractions import Fraction as F
from pathlib import Path
import bpy
from io_scene_fbx import parse_fbx

def bits(x): return struct.unpack('<I',struct.pack('<f',x))[0]
def value(b): return struct.unpack('<f',struct.pack('<I',b))[0]
def adjacent(x):
    if x==0: return -value(1),value(1)
    b=bits(x)
    return (value(b-1),value(b+1)) if x>0 else (value(b+1),value(b-1))

def rounding(exact):
    guess=struct.unpack('<f',struct.pack('<f',float(exact)))[0]
    low,high=adjacent(guess)
    # Resolve using exact distances including ties-to-even, independent of the
    # binary64 intermediate used to locate the three candidate floats.
    x=min((low,guess,high),key=lambda v:(abs(F(v)-exact),bits(v)&1))
    low,high=adjacent(x); lo=(F(low)+F(x))/2; hi=(F(high)+F(x))/2
    assert lo<=exact<=hi
    if exact in (lo,hi): assert bits(x)&1==0
    return x,dict(exact_input=str(exact),f32=x,bits=bits(x),previous=low,next=high,
                  rounding_interval=[str(lo),str(hi)],lower_half_ulp=str(F(x)-lo),
                  upper_half_ulp=str(hi-F(x)),signed_error=str(F(x)-exact))

def child(e,id): return next(c for c in e.elems if c.id==id)
def arr(e,id): return list(child(e,id).props[0])
def file_sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()

root,out=map(Path,sys.argv[sys.argv.index('--')+1:]); out.mkdir(parents=True,exist_ok=True)
package=json.loads((root/'data/island_module_package.json').read_text(encoding='utf-8-sig'))
saved=root/'source/S1_T07_reassembled.blend'
bpy.ops.wm.open_mainfile(filepath=str(saved.resolve()))
rows=[]; all_points=[]
for a in package['canonical_integers']['archetypes']:
    asset=a['archetype_id']; ring=next(p['outer'] for p in a['polygons'] if p['kind']=='land')
    expected=[]
    for k,(x,z) in enumerate(ring):
        fx,rx=rounding(F(x,100000)); fz,rz=rounding(F(z,100000))
        expected.append((fx,-fz,0.0))
        all_points.append(dict(asset=asset,index=k,x=rx,z=rz,
            radial_error_squared=str((F(fx)-F(x,100000))**2+(F(fz)-F(z,100000))**2)))
    for lod in range(3):
        obj=bpy.data.objects[f'{asset}_LOD{lod}_Assembled']; m=obj.data
        assert obj.matrix_world==__import__('mathutils').Matrix.Identity(4)
        vertices=[tuple(v.co) for v in m.vertices]
        water=set(v for v in vertices if v[2]==0)
        assert water==set(expected),(asset,lod,'stored coordinate differs from exact nearest f32')
        mapping={p:k for k,p in enumerate(expected)}
        edges=set()
        for e in m.edges:
            p,q=(vertices[i] for i in e.vertices)
            if p in mapping and q in mapping: edges.add(tuple(sorted((mapping[p],mapping[q]))))
        canonical_edges={tuple(sorted((k,(k+1)%len(ring)))) for k in range(len(ring))}
        assert edges==canonical_edges
        fbx=root/f'export/reassembled/{asset}_LOD{lod}.fbx'
        tree,version=parse_fbx.parse(str(fbx.resolve()))
        objects=child(tree,b'Objects')
        geometry=next(e for e in objects.elems if e.id==b'Geometry')
        model=next(e for e in objects.elems if e.id==b'Model')
        def props(element):
            return {p.props[0].decode():[v.decode() if isinstance(v,bytes) else v for v in p.props[4:]] for p in child(element,b'Properties70').elems}
        model_props=props(model); global_props=props(child(tree,b'GlobalSettings'))
        for name,default in [('Lcl Translation',[0.,0.,0.]),('Lcl Rotation',[0.,0.,0.]),('Lcl Scaling',[1.,1.,1.])]:
            assert model_props.get(name,default)==default

        raw=arr(geometry,b'Vertices'); fbx_vertices=list(zip(raw[0::3],raw[1::3],raw[2::3]))
        assert fbx_vertices==vertices,(asset,lod,'FBX position transform differs')
        indices=arr(geometry,b'PolygonVertexIndex')
        source_indices=[]
        for face in m.polygons:
            source_indices.extend(list(face.vertices)[:-1]+[-face.vertices[-1]-1])
        assert indices==source_indices,(asset,lod,'FBX directed face order differs')
        uv_elem=child(geometry,b'LayerElementUV'); raw_uv=arr(uv_elem,b'UV'); uv_index=arr(uv_elem,b'UVIndex')
        decoded_uv=[(raw_uv[i*2],raw_uv[i*2+1]) for i in uv_index]
        assert decoded_uv==[tuple(v.uv) for v in m.uv_layers[0].data]
        mat=arr(child(geometry,b'LayerElementMaterial'),b'Materials')
        assert mat==[p.material_index for p in m.polygons]
        normal_elem=child(geometry,b'LayerElementNormal'); raw_n=arr(normal_elem,b'Normals')
        ni=arr(normal_elem,b'NormalsIndex')
        decoded_n=[tuple(raw_n[i*3:i*3+3]) for i in ni]
        source_n=[tuple(n.vector) for n in m.corner_normals]
        max_normal_delta=max(abs(a-b) for va,vb in zip(decoded_n,source_n) for a,b in zip(va,vb))
        # Raw normals are retained even if exporter normalization changes bits;
        # do not invent an epsilon or imply this is an exact normal PASS.
        rows.append(dict(asset=asset,lod=lod,blend_matrix=[list(r) for r in obj.matrix_world],
            actual_waterline=[list(p) for p in sorted(water)],unique_ring_points=len(water),
            stored_nearest_f32_exact=True,topology_exact=True,fbx_version=version,
            fbx_position_dtype='binary64 exact promotion of stored binary32; identity axis/unit transform',
            fbx_positions_faces_uv_material_indices_exact=True,fbx_sha256=file_sha(fbx),
            fbx_model_properties=model_props,fbx_global_axis_unit_properties=global_props,
            normal_bitwise_equal=decoded_n==source_n,normal_max_component_delta=max_normal_delta))
        (out/f'{asset}_LOD{lod}_normals.json').write_text(json.dumps(dict(source=source_n,fbx=decoded_n)),encoding='utf-8')
# Exercise asymmetric spacing, negative numbers, zero and exact halfway ties.
cases=[F(0),F(1),F(-1),F(2),F(-2),F(1,2**150),F(-1,2**150),F(1)+F(1,2**24),F(1)+F(3,2**24)]
tests=[rounding(v)[1] for v in cases]
report=dict(geometry_sha=package['geometry_sha'],source_sha256=file_sha(saved),
    stage='saved blend + raw binary FBX; Unity NOT_RUN',points=all_points,rows=rows,
    rounding_edge_cases=tests,measurement='exact Fraction arithmetic for scalar/squared radial errors; no measurement epsilon')
(out/'precision-stages.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(rows,indent=2))
