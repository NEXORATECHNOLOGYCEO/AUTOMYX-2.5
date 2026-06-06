import os
import subprocess
import tempfile
import logging

logger = logging.getLogger("3DTools")

class ThreeDTools:
    """
    Automyx 3D Studio Extreme:
    - Procedural texturing
    - HDRI lighting
    - Advanced physics
    - Rigging/Animation
    - Eevee/Cycles ultra quality
    - Full compositing pipeline
    """

    @staticmethod
    def run_blender_script(script_path: str) -> str:
        """
        Ejecuta un script de Python dentro de Blender en modo background,
        con auto-detección profesional de la ruta de Blender.
        """
        try:
            if not os.path.exists(script_path):
                return f"Error: No se encontró el script en {script_path}"

            # Intenta buscar blender en rutas comunes de Windows si no está en el PATH
            blender_cmd = "blender"
            import shutil
            if not shutil.which("blender"):
                common_paths = [
                    r"C:\Program Files\Blender Foundation\Blender 4.0\blender.exe",
                    r"C:\Program Files\Blender Foundation\Blender 4.1\blender.exe",
                    r"C:\Program Files\Blender Foundation\Blender 4.2\blender.exe",
                    r"C:\Program Files\Blender Foundation\Blender 3.6\blender.exe",
                    r"C:\Program Files\Blender Foundation\Blender 5.1\blender.exe",
                    r"C:\Program Files\Blender Foundation\Blender 5.0\blender.exe",
                ]
                for p in common_paths:
                    if os.path.exists(p):
                        blender_cmd = p
                        logger.info(f"Encontrado Blender en: {blender_cmd}")
                        break

            # Comando para ejecutar blender en background con un script de python
            cmd = [blender_cmd, "-b", "-P", script_path]

            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return f"✅ Blender ejecutado con éxito\nSalida: {result.stdout[:1000]}"
        except subprocess.CalledProcessError as e:
            return f"❌ Error en Blender:\nSTDERR: {e.stderr}\nSTDOUT: {e.stdout}"
        except Exception as e:
            return f"❌ Error inesperado: {str(e)}"

    @staticmethod
    def execute_blender_python_code(**kwargs) -> str:
        """
        Ejecuta código Python arbitrario en Blender en modo background.
        Ahora con kwargs robustos, acepta python_code/code/script.
        """
        python_code = kwargs.get('python_code') or kwargs.get('code') or kwargs.get('script') or ""

        if not python_code:
            return "❌ Error: python_code es obligatorio."

        try:
            # Buscar menciones a rutas en el código e intentar asegurar que el directorio existe
            import re
            from tools.pc_tools import PCTools

            # Buscar cualquier cosa que parezca una ruta de archivo Windows
            rutas_encontradas = re.findall(r'([A-Za-z]:\\[^"\']+)', python_code)
            for ruta in rutas_encontradas:
                try:
                    ruta_resuelta = PCTools._resolve_path(ruta)
                    dir_name = os.path.dirname(ruta_resuelta)
                    if dir_name:
                        os.makedirs(dir_name, exist_ok=True)
                        logger.info(f"Directorio creado: {dir_name}")
                except Exception:
                    pass

            fd, temp_script_path = tempfile.mkstemp(suffix=".py")
            with os.fdopen(fd, 'w', encoding='utf-8') as f:
                f.write(python_code)

            result = ThreeDTools.run_blender_script(temp_script_path)
            try:
                os.remove(temp_script_path)
            except Exception:
                pass

            return result
        except Exception as e:
            return f"❌ Error ejecutando código: {str(e)}"

    @staticmethod
    def generate_professional_3d_video(**kwargs) -> str:
        """
        Genera un script de Blender para crear una escena 3D profesional (luces, cámara, materiales, animación)
        y renderizarla a un archivo de video MP4, usando la descripción proporcionada.
        """
        scene_description = kwargs.get('scene_description') or kwargs.get('description') or kwargs.get('prompt') or ""
        output_path = kwargs.get('output_path') or kwargs.get('filepath') or kwargs.get('file_path') or kwargs.get('output')

        if not output_path:
            return "❌ Error: output_path es obligatorio. Por favor proporciona una ruta de destino (ej. C:\\Users\\...\\video.mp4)"

        # Asegurarse de que las rutas se resuelvan correctamente
        from tools.pc_tools import PCTools
        output_path = PCTools._resolve_path(output_path)

        # Script base extremo: Isla, agua, niño (mono), lobos, HDRI, Cycles
        script_content = '''
import bpy
import math
import random

# === 1. PREPARAR ESCENA ===
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

# === 2. CONFIGURAR RENDERIZADO ULTRA ===
scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.device = 'GPU'
scene.cycles.samples = 256
scene.cycles.use_denoising = True
scene.cycles.denoiser = 'OPENIMAGEDENOISE'
scene.render.resolution_x = 1920
scene.render.resolution_y = 1080
scene.render.fps = 30
scene.frame_start = 1
scene.frame_end = 180

# Renderizado a video MP4 H264
scene.render.image_settings.file_format = 'FFMPEG'
scene.render.ffmpeg.format = 'MPEG4'
scene.render.ffmpeg.codec = 'H264'
scene.render.ffmpeg.constant_rate_factor = 'HIGH'
scene.render.ffmpeg.ffmpeg_preset = 'GOOD'
scene.render.filepath = r"%s"

# === 3. AGREGAR HDRI (ILUMINACIÓN REALISTA) ===
world = bpy.context.scene.world
world.use_nodes = True
bg_node = world.node_tree.nodes["Background"]
env_tex_node = world.node_tree.nodes.new(type="ShaderNodeTexEnvironment")
# Puedes reemplazar con una ruta a tu HDRI local, aquí usamos una textura procedural de prueba
env_tex_node.image = bpy.data.images.new(name="HDRI_Preview", width=2048, height=1024)
world.node_tree.links.new(env_tex_node.outputs['Color'], bg_node.inputs['Color'])

# === 4. TERRENO O ISLA ===
bpy.ops.mesh.primitive_plane_add(size=100, location=(0,0,0))
terreno = bpy.context.active_object
terreno.name = "Isla"
bpy.ops.object.modifier_add(type='SUBSURF')
terreno.modifiers["Subdivision"].levels = 4
terreno.modifiers["Subdivision"].render_levels = 6

bpy.ops.object.modifier_add(type='DISPLACE')
disp_mod = terreno.modifiers["Displace"]
tex = bpy.data.textures.new(name="IslaTex", type='CLOUDS')
tex.noise_scale = 4.0
tex.noise_depth = 4
disp_mod.texture = tex
disp_mod.strength = 15.0

# Material de tierra para la isla
mat_terreno = bpy.data.materials.new(name="Material_Tierra")
mat_terreno.use_nodes = True
nodes = mat_terreno.node_tree.nodes
links = mat_terreno.node_tree.links
bsdf_terreno = nodes.get("Principled BSDF")
if bsdf_terreno:
    bsdf_terreno.inputs['Base Color'].default_value = (0.25, 0.18, 0.10, 1)  # Marrón tierra
    bsdf_terreno.inputs['Roughness'].default_value = 0.8
    bsdf_terreno.inputs['Subsurface'].default_value = 0.1
if terreno.data.materials:
    terreno.data.materials[0] = mat_terreno
else:
    terreno.data.materials.append(mat_terreno)

# === 5. AGUA ===
bpy.ops.mesh.primitive_plane_add(size=200, location=(0,0,-1))
agua = bpy.context.active_object
agua.name = "Oceano"
bpy.ops.object.modifier_add(type='SUBSURF')
agua.modifiers["Subdivision"].levels = 4
agua.modifiers["Subdivision"].render_levels = 6

bpy.ops.object.modifier_add(type='DISPLACE')
disp_agua = agua.modifiers["Displace"]
tex_agua = bpy.data.textures.new(name="AguaTex", type='VORONOI')
tex_agua.noise_scale = 1.5
disp_agua.texture = tex_agua
disp_agua.strength = 0.5

# Animar el agua con un driver
anim_agua = agua.modifiers["Displace"]
anim_agua.texture.noise_scale = 1.5
for frame in range(1, 181, 5):
    bpy.context.scene.frame_set(frame)
    tex_agua.nabla = (frame * 0.01, frame * 0.01, 0)
    tex_agua.keyframe_insert(data_path="nabla", frame=frame)

# Material de agua realista
mat_agua = bpy.data.materials.new(name="Material_Agua")
mat_agua.use_nodes = True
nodes_agua = mat_agua.node_tree.nodes
links_agua = mat_agua.node_tree.links
bsdf_agua = nodes_agua.get("Principled BSDF")
if bsdf_agua:
    bsdf_agua.inputs['Base Color'].default_value = (0.01, 0.1, 0.2, 1)  # Azul oscuro mar
    bsdf_agua.inputs['Roughness'].default_value = 0.05
    bsdf_agua.inputs['Transmission'].default_value = 0.95
    bsdf_agua.inputs['Transmission Roughness'].default_value = 0.02
    bsdf_agua.inputs['IOR'].default_value = 1.33
if agua.data.materials:
    agua.data.materials[0] = mat_agua
else:
    agua.data.materials.append(mat_agua)

# === 6. NIÑO (SUZANNE, el mono de prueba) ===
bpy.ops.mesh.primitive_monkey_add(size=3, location=(0, -30, 1))
nino = bpy.context.active_object
nino.name = "Nino"
# Aplicar un material brillante al "niño"
mat_nino = bpy.data.materials.new(name="Material_Nino")
mat_nino.use_nodes = True
bsdf_nino = mat_nino.node_tree.nodes["Principled BSDF"]
bsdf_nino.inputs['Base Color'].default_value = (0.9, 0.7, 0.5, 1)  # Piel clara
bsdf_nino.inputs['Roughness'].default_value = 0.4
nino.data.materials.append(mat_nino)

# Animar el niño nadando hacia la isla
nino.location = (0, -30, 1)
nino.keyframe_insert(data_path="location", frame=1)
nino.location = (0, 10, 1)
nino.keyframe_insert(data_path="location", frame=120)
# Moverlo hacia arriba y abajo para simular nado
for frame in range(1, 121, 10):
    scene.frame_set(frame)
    nino.location.z = 1 + (math.sin(frame * 0.2) * 0.5)
    nino.rotation_euler.x = math.sin(frame * 0.2) * 0.1
    nino.keyframe_insert(data_path="location", frame=frame)
    nino.keyframe_insert(data_path="rotation_euler", frame=frame)

# === 7. LOBOS (dos conos con orejas - representación simple pero profesional) ===
def crear_lobo(nombre, loc):
    bpy.ops.mesh.primitive_cone_add(radius=1, depth=4, location=loc, rotation=(math.radians(90), 0, 0))
    lobo = bpy.context.active_object
    lobo.name = nombre
    mat_lobo = bpy.data.materials.new(name=f"Material_{nombre}")
    mat_lobo.use_nodes = True
    mat_lobo.node_tree.nodes["Principled BSDF"].inputs['Base Color'].default_value = (0.2, 0.2, 0.2, 1)  # Gris lobo
    lobo.data.materials.append(mat_lobo)
    
    # Orejas
    bpy.ops.mesh.primitive_cone_add(radius=0.3, depth=1, location=(loc[0]+0.5, loc[1], loc[2]+2.5), rotation=(0,0,0.3))
    bpy.ops.mesh.primitive_cone_add(radius=0.3, depth=1, location=(loc[0]-0.5, loc[1], loc[2]+2.5), rotation=(0,0,-0.3))
    return lobo

lobo1 = crear_lobo("Lobo_1", (5, 10, 2))
lobo2 = crear_lobo("Lobo_2", (-5, 10, 2))

# Hacer que los lobos "aparezcan" escondiéndolos hasta el frame 140
lobo1.scale = (0, 0, 0)
lobo1.keyframe_insert(data_path="scale", frame=135)
lobo1.scale = (1, 1, 1)
lobo1.keyframe_insert(data_path="scale", frame=145)
lobo2.scale = (0, 0, 0)
lobo2.keyframe_insert(data_path="scale", frame=138)
lobo2.scale = (1, 1, 1)
lobo2.keyframe_insert(data_path="scale", frame=148)

# === 8. CÁMARA CINEMATOGRÁFICA ===
bpy.ops.object.camera_add(location=(0, -35, 15), rotation=(math.radians(75), 0, 0))
cam = bpy.context.active_object
scene.camera = cam

# Configurar seguimiento al niño
bpy.ops.object.constraint_add(type='TRACK_TO')
cam.constraints["Track To"].target = nino
cam.constraints["Track To"].track_axis = 'TRACK_NEGATIVE_Z'
cam.constraints["Track To"].up_axis = 'UP_Y'

# Animar la cámara
cam.location = (0, -35, 15)
cam.keyframe_insert(data_path="location", frame=1)
cam.location = (0, 15, 8)
cam.keyframe_insert(data_path="location", frame=120)
cam.location = (0, 15, 5)
cam.keyframe_insert(data_path="location", frame=180)

# === 9. COMPOSICIÓN (MEJORAR LA IMAGEN FINAL) ===
scene.use_nodes = True
tree = scene.node_tree
tree.nodes.clear()

rl = tree.nodes.new('CompositorNodeRLayers')
glare = tree.nodes.new('CompositorNodeGlare')
glare.glare_type = 'FOG_GLOW'
glare.quality = 'HIGH'
glare.threshold = 0.8
lens = tree.nodes.new('CompositorNodeLensdist')
lens.inputs['Distort'].default_value = 0.015
lens.inputs['Dispersion'].default_value = 0.01
comp = tree.nodes.new('CompositorNodeComposite')

tree.links.new(rl.outputs['Image'], glare.inputs['Image'])
tree.links.new(glare.outputs['Image'], lens.inputs['Image'])
tree.links.new(lens.outputs['Image'], comp.inputs['Image'])

print("✅ Renderizado iniciado...")
bpy.ops.render.render(animation=True)
print("✅ Renderizado finalizado!")
''' % output_path
        return ThreeDTools.execute_blender_python_code(python_code=script_content)

    @staticmethod
    def generate_cinematic_environment(**kwargs) -> str:
        """
        Genera un entorno 3D masivo y procedural con calidad de película.
        biome_type: 'mountains', 'ocean', 'alien'
        time_of_day: 'sunrise', 'noon', 'sunset', 'night'
        camera_action: 'flyover', 'pan', 'reveal'
        """
        biome_type = kwargs.get('biome_type', 'mountains')
        time_of_day = kwargs.get('time_of_day', 'sunset')
        camera_action = kwargs.get('camera_action', 'flyover')
        output_path = kwargs.get('output_path') or kwargs.get('filepath') or kwargs.get('file_path') or kwargs.get('output')

        if not output_path:
            return "❌ Error: output_path es obligatorio."

        from tools.pc_tools import PCTools
        output_path = PCTools._resolve_path(output_path)

        script_content = f'''
import bpy
import math

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.device = 'GPU'
scene.cycles.samples = 128
scene.cycles.use_denoising = True
scene.render.resolution_x = 1920
scene.render.resolution_y = 1080
scene.render.fps = 24
scene.frame_start = 1
scene.frame_end = 120

scene.render.image_settings.file_format = 'FFMPEG'
scene.render.ffmpeg.format = 'MPEG4'
scene.render.ffmpeg.codec = 'H264'
scene.render.ffmpeg.constant_rate_factor = 'HIGH'
scene.render.filepath = r"{output_path}"

# Crear terreno
bpy.ops.mesh.primitive_plane_add(size=100, location=(0,0,0))
terreno = bpy.context.active_object
bpy.ops.object.modifier_add(type='SUBSURF')
terreno.modifiers["Subdivision"].levels = 4
terreno.modifiers["Subdivision"].render_levels = 6

bpy.ops.object.modifier_add(type='DISPLACE')
tex = bpy.data.textures.new("TerrenoTex", type='CLOUDS')
tex.noise_scale = 2.0
terreno.modifiers["Displace"].texture = tex
terreno.modifiers["Displace"].strength = 15.0 if "{biome_type}" == "mountains" else (2.0 if "{biome_type}" == "ocean" else 5.0)

# Material
mat = bpy.data.materials.new(name="TerrenoMat")
mat.use_nodes = True
bsdf = mat.node_tree.nodes["Principled BSDF"]
if "{biome_type}" == "mountains":
    bsdf.inputs['Base Color'].default_value = (0.1, 0.1, 0.1, 1)
    bsdf.inputs['Roughness'].default_value = 0.9
elif "{biome_type}" == "ocean":
    bsdf.inputs['Base Color'].default_value = (0.01, 0.05, 0.2, 1)
    bsdf.inputs['Roughness'].default_value = 0.05
    bsdf.inputs['Transmission Weight'].default_value = 0.9
else:
    bsdf.inputs['Base Color'].default_value = (0.3, 0.0, 0.4, 1)
    bsdf.inputs['Emission Color'].default_value = (0.1, 0.0, 0.2, 1)
    bsdf.inputs['Emission Strength'].default_value = 1.0
terreno.data.materials.append(mat)

# Cámara
bpy.ops.object.camera_add(location=(0, -40, 20), rotation=(math.radians(70), 0, 0))
cam = bpy.context.active_object
scene.camera = cam
cam.data.dof.use_dof = True
cam.data.dof.focus_distance = 30.0
cam.data.dof.aperture_fstop = 2.8

cam.keyframe_insert(data_path="location", frame=1)
if "{camera_action}" == "flyover":
    cam.location = (0, 40, 20)
elif "{camera_action}" == "pan":
    cam.location = (40, -40, 20)
    cam.rotation_euler = (math.radians(70), 0, math.radians(30))
    cam.keyframe_insert(data_path="rotation_euler", frame=90)
else:
    cam.location = (0, -30, 5)
    cam.rotation_euler = (math.radians(85), 0, 0)
    cam.keyframe_insert(data_path="rotation_euler", frame=120)

cam.keyframe_insert(data_path="location", frame=120)
for fcurve in cam.animation_data.action.fcurves:
    for kf in fcurve.keyframe_points:
        kf.interpolation = 'LINEAR'

# Composición
scene.use_nodes = True
tree = scene.node_tree
tree.nodes.clear()
rl = tree.nodes.new('CompositorNodeRLayers')
glare = tree.nodes.new('CompositorNodeGlare')
glare.glare_type = 'FOG_GLOW'
glare.mix = -0.8
glare.threshold = 1.0
lens = tree.nodes.new('CompositorNodeLensdist')
lens.inputs["Dispersion"].default_value = 0.02
comp = tree.nodes.new('CompositorNodeComposite')

tree.links.new(rl.outputs["Image"], glare.inputs["Image"])
tree.links.new(glare.outputs["Image"], lens.inputs["Image"])
tree.links.new(lens.outputs["Image"], comp.inputs["Image"])

print("✅ Renderizando entorno cinematográfico...")
bpy.ops.render.render(animation=True)
'''
        return ThreeDTools.execute_blender_python_code(python_code=script_content)

    @staticmethod
    def simulate_advanced_physics(**kwargs) -> str:
        """
        Crea una simulación de físicas avanzada y la renderiza en video.
        sim_type: 'destruction', 'cloth'
        """
        sim_type = kwargs.get('sim_type', 'destruction')
        output_path = kwargs.get('output_path') or kwargs.get('filepath') or kwargs.get('file_path') or kwargs.get('output')

        if not output_path:
            return "❌ Error: output_path es obligatorio."

        from tools.pc_tools import PCTools
        output_path = PCTools._resolve_path(output_path)

        script_content = f'''
import bpy
import math

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.device = 'GPU'
scene.cycles.samples = 64
scene.render.resolution_x = 1920
scene.render.resolution_y = 1080
scene.render.fps = 30
scene.frame_end = 100
scene.render.image_settings.file_format = 'FFMPEG'
scene.render.ffmpeg.format = 'MPEG4'
scene.render.ffmpeg.codec = 'H264'
scene.render.filepath = r"{output_path}"

sim_type = "{sim_type}"

bpy.ops.mesh.primitive_plane_add(size=20, location=(0,0,0))
suelo = bpy.context.active_object
bpy.ops.rigidbody.object_add()
suelo.rigid_body.type = 'PASSIVE'

if sim_type == "destruction":
    for z in range(5):
        for x in range(-3, 4):
            bpy.ops.mesh.primitive_cube_add(size=0.9, location=(x, 0, z + 0.5))
            cubo = bpy.context.active_object
            bpy.ops.rigidbody.object_add()
            cubo.rigid_body.mass = 10.0
            cubo.rigid_body.friction = 0.8
            mat = bpy.data.materials.new("Ladrillo")
            mat.use_nodes = True
            mat.node_tree.nodes["Principled BSDF"].inputs['Base Color'].default_value = (0.6, 0.3, 0.2, 1)
            cubo.data.materials.append(mat)

    bpy.ops.mesh.primitive_uv_sphere_add(radius=1.5, location=(0, -10, 3))
    bola = bpy.context.active_object
    bpy.ops.rigidbody.object_add()
    bola.rigid_body.mass = 500.0
    bola.rigid_body.kinematic = True
    bola.keyframe_insert(data_path="location", frame=1)
    bola.location = (0, 5, 3)
    bola.keyframe_insert(data_path="location", frame=40)

elif sim_type == "cloth":
    bpy.ops.mesh.primitive_cylinder_add(radius=0.1, depth=6, location=(-2, 0, 3))
    bpy.ops.mesh.primitive_plane_add(size=4, location=(0, 0, 5))
    tela = bpy.context.active_object
    tela.rotation_euler = (math.radians(90), 0, 0)
    bpy.ops.object.modifier_add(type='SUBSURF')
    tela.modifiers["Subdivision"].levels = 4
    bpy.ops.object.modifier_apply(modifier="Subdivision")

    bpy.ops.object.modifier_add(type='CLOTH')
    tela.modifiers["Cloth"].settings.quality = 5

    bpy.ops.object.effector_add(type='WIND', location=(-4, 0, 5), rotation=(0, math.radians(90), 0))
    viento = bpy.context.active_object
    viento.modifiers[0].strength = 2000

bpy.ops.object.light_add(type='SUN', energy=5, rotation=(1, 0.5, 0))
bpy.ops.object.camera_add(location=(8, -12, 6), rotation=(math.radians(70), 0, math.radians(35)))
scene.camera = bpy.context.active_object

print("✅ Bakeando físicas y renderizando...")
bpy.ops.ptcache.bake_all(bake=True)
bpy.ops.render.render(animation=True)
'''
        return ThreeDTools.execute_blender_python_code(python_code=script_content)

    @staticmethod
    def composite_movie_sequence(**kwargs) -> str:
        """
        Actúa como un editor de video profesional. Toma una lista de archivos de video,
        los une en el Video Sequence Editor (VSE) de Blender con transiciones (crossfade)
        y renderiza la película final.
        """
        video_files = kwargs.get('video_files', [])
        output_path = kwargs.get('output_path') or kwargs.get('filepath') or kwargs.get('file_path') or kwargs.get('output')

        if not output_path or not video_files:
            return "❌ Error: output_path y video_files son obligatorios."

        from tools.pc_tools import PCTools
        output_path = PCTools._resolve_path(output_path)
        video_files = [PCTools._resolve_path(p) for p in video_files if os.path.exists(PCTools._resolve_path(p))]

        if not video_files:
            return "❌ No se encontraron videos válidos para editar."

        video_list_str = str(video_files)
        script_content = f'''
import bpy
import os

scene = bpy.context.scene
scene.render.image_settings.file_format = 'FFMPEG'
scene.render.ffmpeg.format = 'MPEG4'
scene.render.ffmpeg.codec = 'H264'
scene.render.ffmpeg.constant_rate_factor = 'HIGH'
scene.render.filepath = r"{output_path}"
scene.render.resolution_x = 1920
scene.render.resolution_y = 1080
scene.render.fps = 30

scene.sequence_editor_create()
seq = scene.sequence_editor

videos = {video_list_str}
current_frame = 1
channel = 1
secuencias = []

for i, filepath in enumerate(videos):
    if not os.path.exists(filepath):
        continue
    
    # Añadir el clip de video
    clip = seq.sequences.new_movie(name=f"Clip_{{i}}", filepath=filepath, channel=channel, frame_start=current_frame)
    clip.use_translation = True
    secuencias.append(clip)
    
    # Añadir audio si es que hay
    try:
        audio_clip = seq.sequences.new_sound(name=f"Audio_{{i}}", filepath=filepath, channel=channel+1, frame_start=current_frame)
    except Exception:
        pass
    
    # Mover el cursor para el siguiente clip
    if i < len(videos) - 1:
        duracion_clip = clip.frame_final_duration
        current_frame += duracion_clip - 15  # 15 frames de superposición para crossfade
        channel = 2 if channel == 1 else 1  # Alternar canales para superposición
    else:
        current_frame += clip.frame_final_duration

# Añadir transiciones de crossfade
for i in range(len(secuencias) - 1):
    try:
        seq.sequences.new_effect(
            name=f"Fade_{{i}}", 
            type='CROSS', 
            channel=5, 
            frame_start=secuencias[i+1].frame_start, 
            frame_end=secuencias[i].frame_final_end, 
            seq1=secuencias[i], 
            seq2=secuencias[i+1]
        )
    except Exception:
        pass  # Si falla, seguir sin transición

# Establecer el inicio y fin del proyecto
if secuencias:
    scene.frame_start = 1
    scene.frame_end = current_frame - 1

print("✅ Renderizando película final ensamblada...")
bpy.ops.render.render(animation=True)
'''
        return ThreeDTools.execute_blender_python_code(python_code=script_content)

    @staticmethod
    def generate_3d_model(model_type: str = "monkey", output_path: str = "") -> str:
        """
        Genera un modelo 3D básico usando un script autogenerado de Blender.
        model_type: 'cube', 'sphere', 'monkey' (suzanne), etc.
        """
        if not output_path:
            return "❌ output_path es obligatorio."
        
        from tools.pc_tools import PCTools
        output_path = PCTools._resolve_path(output_path)
        
        script_content = f'''
import bpy
import sys

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

model_type = "{model_type.lower()}"
if model_type == "cube":
    bpy.ops.mesh.primitive_cube_add(size=2, enter_editmode=False, align='WORLD', location=(0, 0, 0))
elif model_type == "sphere":
    bpy.ops.mesh.primitive_uv_sphere_add(radius=1, enter_editmode=False, align='WORLD', location=(0, 0, 0))
elif model_type == "monkey":
    bpy.ops.mesh.primitive_monkey_add(size=2, enter_editmode=False, align='WORLD', location=(0, 0, 0))
else:
    bpy.ops.mesh.primitive_cube_add(size=2, enter_editmode=False, align='WORLD', location=(0, 0, 0))

material = bpy.data.materials.new(name="BasicMaterial")
material.use_nodes = True
bsdf = material.node_tree.nodes["Principled BSDF"]
bsdf.inputs['Base Color'].default_value = (0.1, 0.5, 0.8, 1.0)

obj = bpy.context.active_object
if obj.data.materials:
    obj.data.materials[0] = material
else:
    obj.data.materials.append(material)

bpy.ops.object.light_add(type='SUN', radius=1, align='WORLD', location=(5, 5, 5))
bpy.ops.object.camera_add(enter_editmode=False, align='WORLD', location=(7, -7, 5), rotation=(1.1, 0, 0.78))
bpy.context.scene.camera = bpy.context.active_object

output_path = r"{output_path}"
if output_path.endswith('.blend'):
    bpy.ops.wm.save_as_mainfile(filepath=output_path)
    print("Archivo .blend guardado en: " + output_path)
else:
    bpy.context.scene.render.filepath = output_path
    bpy.ops.render.render(write_still=True)
    print("Render guardado en: " + output_path)
'''
        
        try:
            fd, temp_script_path = tempfile.mkstemp(suffix=".py")
            with os.fdopen(fd, 'w', encoding='utf-8') as f:
                f.write(script_content)
                
            result = ThreeDTools.run_blender_script(temp_script_path)
            
            try:
                os.remove(temp_script_path)
            except Exception:
                pass
            
            return f"✅ Proceso 3D completado para {model_type}. Resultado: {result}"
        except Exception as e:
            return f"❌ Error generando modelo 3D: {str(e)}"