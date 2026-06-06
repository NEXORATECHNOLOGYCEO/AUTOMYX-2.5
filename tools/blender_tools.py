
import os
import sys
import math
from pathlib import Path

# Intentar importar bpy (Blender) - opcional
try:
    import bpy
    BPY_AVAILABLE = True
except ImportError:
    BPY_AVAILABLE = False
    print("⚠️  Blender (bpy) no está disponible. Las herramientas de Blender mostrarán mensajes informativos.")

class BlenderTools:
    """
    Herramientas profesionales para controlar Blender y crear contenido 3D
    de forma automática y profesional.
    """

    @staticmethod
    def _check_blender_available():
        """Verifica si Blender está disponible y devuelve un mensaje si no lo está."""
        if not BPY_AVAILABLE:
            return "Blender (bpy) no está instalado o no está disponible en este entorno. Las herramientas de Blender requieren que ejecutes este código dentro de Blender o que tengas la librería bpy instalada."
        return None

    @staticmethod
    def open_blender():
        """
        Abre Blender si no está ya abierto.
        """
        check = BlenderTools._check_blender_available()
        if check:
            return check
            
        if bpy.context is not None:
            return "Blender ya está abierto y listo para usar."
        
        return "Blender no está abierto. Por favor, abre Blender para usar estas herramientas."

    @staticmethod
    def create_cube(size=2, location=(0, 0, 0), name="Cube"):
        """
        Crea un cubo 3D profesional con las dimensiones y posición especificadas.
        """
        check = BlenderTools._check_blender_available()
        if check:
            return check
            
        bpy.ops.mesh.primitive_cube_add(
            size=size,
            enter_editmode=False,
            align='WORLD',
            location=location,
            rotation=(0, 0, 0)
        )
        
        obj = bpy.context.active_object
        obj.name = name
        
        return f"Cubo '{name}' creado exitosamente en {location} con tamaño {size}."

    @staticmethod
    def create_sphere(radius=1, location=(0, 0, 0), name="Sphere", segments=32, rings=16):
        """
        Crea una esfera 3D profesional con alta calidad.
        """
        check = BlenderTools._check_blender_available()
        if check:
            return check
            
        bpy.ops.mesh.primitive_uv_sphere_add(
            radius=radius,
            segments=segments,
            ring_count=rings,
            enter_editmode=False,
            align='WORLD',
            location=location
        )
        
        obj = bpy.context.active_object
        obj.name = name
        
        return f"Esfera '{name}' creada exitosamente en {location} con radio {radius}."

    @staticmethod
    def create_torus(major_radius=1, minor_radius=0.25, location=(0, 0, 0), name="Torus"):
        """
        Crea un toro (donut) 3D profesional.
        """
        check = BlenderTools._check_blender_available()
        if check:
            return check
            
        bpy.ops.mesh.primitive_torus_add(
            align='WORLD',
            location=location,
            rotation=(0, 0, 0),
            major_radius=major_radius,
            minor_radius=minor_radius
        )
        
        obj = bpy.context.active_object
        obj.name = name
        
        return f"Toro '{name}' creado exitosamente en {location}."

    @staticmethod
    def create_cylinder(radius=1, depth=2, location=(0, 0, 0), name="Cylinder"):
        """
        Crea un cilindro 3D profesional.
        """
        check = BlenderTools._check_blender_available()
        if check:
            return check
            
        bpy.ops.mesh.primitive_cylinder_add(
            radius=radius,
            depth=depth,
            enter_editmode=False,
            align='WORLD',
            location=location
        )
        
        obj = bpy.context.active_object
        obj.name = name
        
        return f"Cilindro '{name}' creado exitosamente en {location}."

    @staticmethod
    def create_cone(radius=1, depth=2, location=(0, 0, 0), name="Cone"):
        """
        Crea un cono 3D profesional.
        """
        check = BlenderTools._check_blender_available()
        if check:
            return check
            
        bpy.ops.mesh.primitive_cone_add(
            radius=radius,
            depth=depth,
            enter_editmode=False,
            align='WORLD',
            location=location
        )
        
        obj = bpy.context.active_object
        obj.name = name
        
        return f"Cono '{name}' creado exitosamente en {location}."

    @staticmethod
    def apply_material(obj_name, color=(1, 0, 0, 1), roughness=0.5, metallic=0.0):
        """
        Aplica un material profesional a un objeto 3D con propiedades avanzadas.
        """
        check = BlenderTools._check_blender_available()
        if check:
            return check
            
        obj = bpy.data.objects.get(obj_name)
        if not obj:
            return f"Error: No se encontró el objeto '{obj_name}'."
        
        material = bpy.data.materials.new(name=f"Material_{obj_name}")
        material.use_nodes = True
        
        nodes = material.node_tree.nodes
        links = material.node_tree.links
        
        bsdf = nodes.get("Principled BSDF")
        if bsdf:
            bsdf.inputs["Base Color"].default_value = color
            bsdf.inputs["Roughness"].default_value = roughness
            bsdf.inputs["Metallic"].default_value = metallic
        
        if obj.data.materials:
            obj.data.materials[0] = material
        else:
            obj.data.materials.append(material)
        
        return f"Material aplicado exitosamente a '{obj_name}'."

    @staticmethod
    def set_object_location(obj_name, location=(0, 0, 0)):
        """
        Establece la posición de un objeto 3D en la escena.
        """
        check = BlenderTools._check_blender_available()
        if check:
            return check
            
        obj = bpy.data.objects.get(obj_name)
        if not obj:
            return f"Error: No se encontró el objeto '{obj_name}'."
        
        obj.location = location
        
        return f"Posición de '{obj_name}' actualizada a {location}."

    @staticmethod
    def set_object_rotation(obj_name, rotation=(0, 0, 0)):
        """
        Establece la rotación de un objeto 3D en la escena.
        """
        check = BlenderTools._check_blender_available()
        if check:
            return check
            
        obj = bpy.data.objects.get(obj_name)
        if not obj:
            return f"Error: No se encontró el objeto '{obj_name}'."
        
        obj.rotation_euler = rotation
        
        return f"Rotación de '{obj_name}' actualizada a {rotation}."

    @staticmethod
    def set_object_scale(obj_name, scale=(1, 1, 1)):
        """
        Establece la escala de un objeto 3D en la escena.
        """
        check = BlenderTools._check_blender_available()
        if check:
            return check
            
        obj = bpy.data.objects.get(obj_name)
        if not obj:
            return f"Error: No se encontró el objeto '{obj_name}'."
        
        obj.scale = scale
        
        return f"Escala de '{obj_name}' actualizada a {scale}."

    @staticmethod
    def delete_object(obj_name):
        """
        Elimina un objeto 3D de la escena.
        """
        check = BlenderTools._check_blender_available()
        if check:
            return check
            
        obj = bpy.data.objects.get(obj_name)
        if not obj:
            return f"Error: No se encontró el objeto '{obj_name}'."
        
        bpy.data.objects.remove(obj, do_unlink=True)
        
        return f"Objeto '{obj_name}' eliminado exitosamente."

    @staticmethod
    def clear_scene():
        """
        Limpia toda la escena de Blender eliminando todos los objetos.
        """
        check = BlenderTools._check_blender_available()
        if check:
            return check
            
        bpy.ops.object.select_all(action='SELECT')
        bpy.ops.object.delete()
        
        return "Escena limpiada completamente."

    @staticmethod
    def save_scene(file_path):
        """
        Guarda la escena de Blender en un archivo .blend.
        """
        check = BlenderTools._check_blender_available()
        if check:
            return check
            
        try:
            bpy.ops.wm.save_as_mainfile(filepath=str(file_path))
            return f"Escena guardada exitosamente en: {file_path}"
        except Exception as e:
            return f"Error guardando la escena: {e}"

    @staticmethod
    def render_image(output_path, resolution_x=1920, resolution_y=1080, samples=128):
        """
        Renderiza una imagen de alta calidad profesional.
        """
        check = BlenderTools._check_blender_available()
        if check:
            return check
            
        scene = bpy.context.scene
        scene.render.resolution_x = resolution_x
        scene.render.resolution_y = resolution_y
        scene.render.resolution_percentage = 100
        scene.render.image_settings.file_format = 'PNG'
        
        # Configuración de Cycles para calidad máxima
        scene.render.engine = 'CYCLES'
        scene.cycles.samples = samples
        scene.cycles.use_denoising = True
        
        scene.render.filepath = str(output_path)
        bpy.ops.render.render(write_still=True)
        
        return f"Imagen renderizada exitosamente en: {output_path}"

    @staticmethod
    def create_animation(obj_name, start_frame=1, end_frame=250, location_animation=None, rotation_animation=None):
        """
        Crea una animación profesional para un objeto 3D.
        """
        check = BlenderTools._check_blender_available()
        if check:
            return check
            
        obj = bpy.data.objects.get(obj_name)
        if not obj:
            return f"Error: No se encontró el objeto '{obj_name}'."
        
        scene = bpy.context.scene
        scene.frame_start = start_frame
        scene.frame_end = end_frame
        
        if location_animation:
            for frame, loc in location_animation.items():
                scene.frame_set(frame)
                obj.location = loc
                obj.keyframe_insert(data_path="location")
        
        if rotation_animation:
            for frame, rot in rotation_animation.items():
                scene.frame_set(frame)
                obj.rotation_euler = rot
                obj.keyframe_insert(data_path="rotation_euler")
        
        return f"Animación creada exitosamente para '{obj_name}' del frame {start_frame} al {end_frame}."

    @staticmethod
    def render_animation(output_path, resolution_x=1920, resolution_y=1080, samples=64):
        """
        Renderiza una animación profesional.
        """
        check = BlenderTools._check_blender_available()
        if check:
            return check
            
        scene = bpy.context.scene
        scene.render.resolution_x = resolution_x
        scene.render.resolution_y = resolution_y
        scene.render.resolution_percentage = 100
        scene.render.image_settings.file_format = 'FFMPEG'
        scene.render.ffmpeg.format = 'MPEG4'
        scene.render.ffmpeg.codec = 'H264'
        scene.render.ffmpeg.constant_rate_factor = 'MEDIUM'
        scene.render.ffmpeg.ffmpeg_preset = 'GOOD'
        
        scene.render.engine = 'CYCLES'
        scene.cycles.samples = samples
        scene.cycles.use_denoising = True
        
        scene.render.filepath = str(output_path)
        bpy.ops.render.render(animation=True, write_still=True)
        
        return f"Animación renderizada exitosamente en: {output_path}"

    @staticmethod
    def import_model(file_path):
        """
        Importa un modelo 3D desde archivos como .obj, .fbx, .glb, .gltf, etc.
        """
        check = BlenderTools._check_blender_available()
        if check:
            return check
            
        ext = os.path.splitext(file_path)[1].lower()
        
        try:
            if ext == '.obj':
                bpy.ops.wm.obj_import(filepath=str(file_path))
            elif ext == '.fbx':
                bpy.ops.import_scene.fbx(filepath=str(file_path))
            elif ext in ['.glb', '.gltf']:
                bpy.ops.import_scene.gltf(filepath=str(file_path))
            elif ext == '.blend':
                bpy.ops.wm.append(filepath=str(file_path))
            else:
                return f"Formato de archivo no compatible: {ext}"
            
            return f"Modelo importado exitosamente desde: {file_path}"
        except Exception as e:
            return f"Error importando el modelo: {e}"

    @staticmethod
    def export_model(file_path, obj_name=None):
        """
        Exporta un objeto 3D o la escena completa en diferentes formatos.
        """
        check = BlenderTools._check_blender_available()
        if check:
            return check
            
        ext = os.path.splitext(file_path)[1].lower()
        
        try:
            if obj_name:
                obj = bpy.data.objects.get(obj_name)
                if not obj:
                    return f"Error: No se encontró el objeto '{obj_name}'."
                bpy.ops.object.select_all(action='DESELECT')
                obj.select_set(True)
            
            if ext == '.obj':
                bpy.ops.wm.obj_export(filepath=str(file_path), use_selection=(obj_name is not None))
            elif ext == '.fbx':
                bpy.ops.export_scene.fbx(filepath=str(file_path), use_selection=(obj_name is not None))
            elif ext in ['.glb', '.gltf']:
                bpy.ops.export_scene.gltf(filepath=str(file_path), use_selection=(obj_name is not None))
            else:
                return f"Formato de archivo no compatible para exportar: {ext}"
            
            return f"Modelo exportado exitosamente a: {file_path}"
        except Exception as e:
            return f"Error exportando el modelo: {e}"

    @staticmethod
    def list_objects():
        """
        Lista todos los objetos en la escena.
        """
        check = BlenderTools._check_blender_available()
        if check:
            return []
            
        objects = []
        for obj in bpy.data.objects:
            objects.append({
                "name": obj.name,
                "type": obj.type,
                "location": list(obj.location),
                "rotation": list(obj.rotation_euler),
                "scale": list(obj.scale)
            })
        
        return objects

print("✅ BlenderTools cargado correctamente (compatible con y sin Blender instalado).")
