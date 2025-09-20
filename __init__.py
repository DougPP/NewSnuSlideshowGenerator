# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####

import bpy
import re
from bpy.props import *

import random
import glob
import os
import sys
import math
from mathutils import Vector
import json
from bpy_extras.image_utils import load_image
from bpy.app.handlers import persistent

bl_info = {
    "name": "Snu Slideshow Generator",
    "description": "Assists in creating image slideshows with a variety of options.",
    "author": "Hudson Barkley (Snu)",
    "version": (0, 88, 0),
    "blender": (4, 4, 0),
    "location": "3D View Sidebar, 'Slideshow' tab.",
    "wiki_url": "https://github.com/snuq/SnuSlideshowGenerator",
    "category": "Import-Export"
}


# Transform definitions
transforms = [
    {
        'name': 'None',
        'influence': [(0, 1)],
        'zLoc': [(0, 1)],
        'zRot': [(0, 1)],
        'xLoc': [(0, 1)]
    },
    {
        'name': 'Move Left Complete With Pause',
        'xLoc': [(-1, 0), (0, 1), (1, 0)]
    },
    {
        'name': 'Move Right Complete With Pause',
        'xLoc': [(1, 0), (0, 1), (-1, 0)]
    },
    {
        'name': 'Move Left Little',
        'xLoc': [(-0.15, 1), (0.15, 1)]
    },
    {
        'name': 'Move Right Little',
        'xLoc': [(0.15, 1), (-0.15, 1)]
    },
    {
        'name': 'Rotate Left Around Top',
        'zLoc': [(-0.1, 1)],
        'zRot': [(-10, 1), (10, 1)],
        'xLoc': [(-0.1, 1), (0.1, 1)]
    },
    {
        'name': 'Rotate Left Around Bottom',
        'zLoc': [(-0.1, 1)],
        'zRot': [(10, 1), (-10, 1)],
        'xLoc': [(-0.1, 1), (0.1, 1)]
    },
    {
        'name': 'Rotate Right Around Top',
        'zLoc': [(-0.1, 1)],
        'zRot': [(10, 1), (-10, 1)],
        'xLoc': [(0.1, 1), (-0.1, 1)]
    },
    {
        'name': 'Rotate Right Around Bottom',
        'zLoc': [(-0.1, 1)],
        'zRot': [(-10, 1), (10, 1)],
        'xLoc': [(0.1, 1), (-0.1, 1)]
    },
    {
        'name': 'Pan To Target',
        'influence': [(0, 1), (1, 1)]
    },
    {
        'name': 'Rotate Left',
        'zLoc': [(-0.1, 1)],
        'zRot': [(10, 1), (-10, 1)]
    },
    {
        'name': 'Rotate Right',
        'zLoc': [(-0.1, 1)],
        'zRot': [(-10, 1), (10, 1)]
    },
    {
        'name': 'Zoom In',
        'influence': [(0, 1), (1, 1)],
        'zLoc': [(0, 1), (-0.3, 1)]
    },
    {
        'name': 'Zoom Out',
        'influence': [(1, 1), (0, 1)],
        'zLoc': [(-0.3, 1), (0, 1)]
    },
    {
        'name': 'Zoom In And Rotate Left',
        'influence': [(0, 1), (1, 1)],
        'zLoc': [(0, 1), (-0.3, 1)],
        'zRot': [(0, 1), (-10, 1)]
    },
    {
        'name': 'Zoom In And Rotate Right',
        'influence': [(0, 1), (1, 1)],
        'zLoc': [(0, 1), (-0.3, 1)],
        'zRot': [(0, 1), (10, 1)]
    },
    {
        'name': 'Zoom Out And Rotate Left',
        'influence': [(1, 1), (0, 1)],
        'zLoc': [(-0.3, 1), (0, 1)],
        'zRot': [(10, 1), (0, 1)]
    },
    {
        'name': 'Zoom Out And Rotate Right',
        'influence': [(1, 1), (0, 1)],
        'zLoc': [(-0.3, 1), (0, 1)],
        'zRot': [(-10, 1), (0, 1)]
    }
]


def get_extensions_image():
    return list(bpy.path.extensions_image) + [x.upper() for x in list(bpy.path.extensions_image)]


def get_extensions_video():
    return list(bpy.path.extensions_movie) + [x.upper() for x in list(bpy.path.extensions_movie)]


def get_image(filepath):
    for image in bpy.data.images:
        if image.filepath == filepath:
            return image


def update_scene(scene):
    for view_layer in scene.view_layers:
        view_layer.update()
        view_layer.objects.update()


def select_plane(image_plane, scene):
    if image_plane:
        if image_plane.name in bpy.context.view_layer.objects:
            image_plane.select_set(True)
            bpy.context.view_layer.objects.active = image_plane


def is_generator_scene(scene):
    if scene.snu_slideshow_generator.is_generator_scene or scene.name == 'Slideshow Generator':
        return True
    else:
        return False


@persistent
def slideshow_autoupdate(_):
    if is_generator_scene(bpy.context.scene):
        update_order()
        lock_view()


def lock_view():
    space = get_first_3d_view()
    if space:
        space.region_3d.view_rotation = (1.0, 0, 0, 0)
        space.region_3d.view_perspective = 'ORTHO'


def format_seconds(seconds):
    if seconds > 60:
        minutes, extra_seconds = divmod(seconds, 60)
        length_formatted = str(int(minutes))+" Minutes, "+str(int(extra_seconds))+" Seconds"
    else:
        length_formatted = str(round(seconds, 2)) + " Seconds"
    return length_formatted


def get_fps(scene):
    return scene.render.fps / scene.render.fps_base


def sanitize_text_for_driver(text):
    """Sanitize text content to be safe for use in driver expressions"""
    # Escape quotes and special characters
    text = text.replace('\\', '\\\\')  # Escape backslashes first
    text = text.replace('"', '\\"')    # Escape double quotes
    text = text.replace('\n', '\\n')   # Escape newlines
    text = text.replace('\r', '\\r')   # Escape carriage returns
    text = text.replace('\t', '\\t')   # Escape tabs
    return text

def create_scene(oldscene, scenename):
    newscene = bpy.data.scenes.new(scenename)

    # Copy render settings
    for prop in oldscene.render.bl_rna.properties:
        if not prop.is_readonly:
            value = eval('oldscene.render.'+prop.identifier)
            try:
                setattr(newscene.render, prop.identifier, value)
            except Exception as e:
                pass
    for prop in oldscene.render.image_settings.bl_rna.properties:
        if not prop.is_readonly:
            value = eval('oldscene.render.image_settings.'+prop.identifier)
            try:
                setattr(newscene.render.image_settings, prop.identifier, value)
            except Exception as e:
                pass
    for prop in oldscene.render.ffmpeg.bl_rna.properties:
        if not prop.is_readonly:
            value = eval('oldscene.render.ffmpeg.'+prop.identifier)
            try:
                setattr(newscene.render.ffmpeg, prop.identifier, value)
            except Exception as e:
                pass

    newscene.view_settings.view_transform = oldscene.view_settings.view_transform

    # Set slideshow-specific settings
    newscene.render.film_transparent = False
    newscene.render.engine = 'BLENDER_EEVEE_NEXT'
    newscene.eevee.use_shadows = True
    newscene.eevee.shadow_ray_count = 4
    newscene.eevee.shadow_step_count = 4
    newscene.render.resolution_percentage = 100
    newscene.render.image_settings.color_mode = 'RGB'
    return newscene


def aspect_ratio(scene):
    render = scene.render
    return (render.pixel_aspect_x * render.resolution_x) / (render.pixel_aspect_y * render.resolution_y)


def get_text_location(generator_scene, y_offset, size=0.18):
    """Return correct (x, y, z) based on chosen alignment"""
    align = generator_scene.snu_slideshow_generator.text_alignment
    
    # Adjust X position based on alignment
    # These positions work with Blender's internal text alignment
    if align == 'LEFT':
        x = -1.6
    elif align == 'RIGHT':
        x = 1.6
    else:  # CENTER
        x = 0.0
    
    return (x, y_offset, 0)


# NEW: Per-slide text data management functions
def load_slide_text_data(image_filepath):
    """Load text data from .txt file corresponding to image file"""
    try:
        # Get the base name without extension
        base_name = os.path.splitext(image_filepath)[0]
        txt_filepath = base_name + '.txt'
        
        if os.path.exists(txt_filepath):
            text_data = {
                'photographer': '',
                'when': '',
                'who': '',
                'where': '',
                'has_text': True
            }
            
            with open(txt_filepath, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                
            # Parse the text file looking for our 4 variables
            for line in lines:
                line = line.strip()
                if line.lower().startswith('photographer:'):
                    text_data['photographer'] = line.split(':', 1)[1].strip()
                elif line.lower().startswith('when:'):
                    text_data['when'] = line.split(':', 1)[1].strip()
                elif line.lower().startswith('who:'):
                    text_data['who'] = line.split(':', 1)[1].strip()
                elif line.lower().startswith('where:'):
                    text_data['where'] = line.split(':', 1)[1].strip()
            
            return text_data
    except Exception as e:
        print(f"Error loading text data for {image_filepath}: {e}")
    
    return {'photographer': '', 'when': '', 'who': '', 'where': '', 'has_text': False}





@bpy.app.handlers.persistent
def typewriter_frame_handler(scene):
    """Frame handler for typewriter animation"""
    
    for obj in scene.objects:
        if (obj.type == 'FONT' and 
            "typewriter_full_text" in obj and 
            "typewriter_start_frame" in obj and
            not obj.data.animation_data):
            
            current_frame = scene.frame_current
            start_frame = obj["typewriter_start_frame"]
            frames_per_char = obj.get("typewriter_frames_per_char", 8)
            full_text = obj["typewriter_full_text"]
            
            elapsed_frames = current_frame - start_frame
            char_count = max(0, min(len(full_text), elapsed_frames // frames_per_char))
            
            obj.data.body = full_text[:int(char_count)]


def add_typewriter_animation_frame_based(text_obj, full_text, scene):
    """Fallback frame-based typewriter animation using frame handlers"""
    
    if text_obj.animation_data:
        text_obj.animation_data_clear()
    
    text_obj["typewriter_full_text"] = full_text
    text_obj["typewriter_start_frame"] = scene.frame_current
    
    fps = get_fps(scene)
    chars_per_second = 8
    frames_per_char = max(1, int(fps / chars_per_second))
    text_obj["typewriter_frames_per_char"] = frames_per_char
    text_obj["typewriter_total_frames"] = len(full_text) * frames_per_char
    
    if typewriter_frame_handler not in bpy.app.handlers.frame_change_pre:
        bpy.app.handlers.frame_change_pre.append(typewriter_frame_handler)


def add_typewriter_animation_robust(text_obj, full_text, scene, start_frame=1):
    """Add robust typewriter animation using custom properties and drivers with start_frame support"""
    
    if not full_text.strip():
        text_obj.data.body = ""
        return
    
    if text_obj.animation_data:
        text_obj.animation_data_clear()
    
    if text_obj.data.animation_data:
        text_obj.data.animation_data.drivers.clear()
    
    sanitized_text = sanitize_text_for_driver(full_text)
    text_obj["typewriter_full_text"] = full_text
    text_obj["typewriter_sanitized_text"] = sanitized_text
    
    text_obj["typewriter_progress"] = 0.0
    
    try:
        text_obj.id_properties_ui("typewriter_progress").update(
            min=0.0,
            max=float(len(full_text)),
            soft_min=0.0,
            soft_max=float(len(full_text)),
            description="Controls typewriter effect progress"
        )
    except AttributeError:
        pass
    
    text_obj.animation_data_create()
    action = bpy.data.actions.new(name=f"{text_obj.name}_typewriter")
    text_obj.animation_data.action = action
    
    fps = get_fps(scene)
    chars_per_second = 8
    frames_per_char = max(1, int(fps / chars_per_second))
    total_frames = len(full_text) * frames_per_char
    
    fcurve = action.fcurves.new(data_path='["typewriter_progress"]')
    
    start_point = fcurve.keyframe_points.insert(frame=start_frame, value=0.0)
    start_point.interpolation = 'LINEAR'
    
    end_frame = start_frame + total_frames
    end_point = fcurve.keyframe_points.insert(frame=end_frame, value=float(len(full_text)))
    end_point.interpolation = 'LINEAR'
    
    try:
        driver = text_obj.data.driver_add("body")
        driver.driver.type = 'SCRIPTED'
        
        var = driver.driver.variables.new()
        var.name = "progress"
        var.type = 'SINGLE_PROP'
        var.targets[0].id = text_obj
        var.targets[0].data_path = '["typewriter_progress"]'
        
        var_text = driver.driver.variables.new()
        var_text.name = "full_text"
        var_text.type = 'SINGLE_PROP'
        var_text.targets[0].id = text_obj
        var_text.targets[0].data_path = '["typewriter_full_text"]'
        
        driver.driver.expression = f"full_text[0:int(max(0, min(progress, len(full_text))))] if full_text else ''"
        
    except Exception as e:
        print(f"Error creating driver for {text_obj.name}: {e}")
        add_typewriter_animation_frame_based(text_obj, full_text, scene)
        return
    
    scene.frame_set(1)
    text_obj["typewriter_progress"] = 0.0
    
    return total_frames





def add_animation_delay_robust(text_obj, delay_frames):
    """Add a delay to the typewriter animation by shifting keyframes or adjusting start frame"""
    
    if text_obj.data.animation_data and text_obj.data.animation_data.action:
        for fcurve in text_obj.data.animation_data.action.fcurves:
            if fcurve.data_path == '["typewriter_progress"]':
                for keyframe in fcurve.keyframe_points:
                    keyframe.co[0] += delay_frames
                    keyframe.handle_left[0] += delay_frames
                    keyframe.handle_right[0] += delay_frames
    elif "typewriter_start_frame" in text_obj:
        text_obj["typewriter_start_frame"] += delay_frames




def add_fade_animation(obj, material, scene, start_frame, duration=20):
    """Animate emission strength fade-out for text and outline."""
    if not material or not material.node_tree:
        return

    # Ensure duration is valid
    if duration is None or duration <= 0:
        duration = 20

    nodes = material.node_tree.nodes
    emission = nodes.get("TextEmission") or nodes.get("OutlineEmission")
    if not emission:
        return

    strength_input = emission.inputs[1]  # Emission Strength
    fade_start = start_frame + duration
    fade_end = fade_start + duration

    # Insert keyframes for fade-out
    strength_input.default_value = 4.0
    strength_input.keyframe_insert("default_value", frame=fade_start)
    strength_input.default_value = 0.0
    strength_input.keyframe_insert("default_value", frame=fade_end)



def create_slide_text_overlay_scene_with_improved_outline(generator_scene, slide, slide_duration):
    """Create a scene with improved outlined text overlays, including a synchronized fade-out animation"""
    
    if not slide.slideshow.enable_text_overlay:
        return None
        
    text_fields = [
        ('text_photographer', 'Photo by'),
        ('text_when', 'When'),
        ('text_who', 'Who'),
        ('text_where', 'Where')
    ]
    
    has_content = any(getattr(slide.slideshow, field[0], '') for field in text_fields)
    if not has_content:
        return None
    
    text_scene_name = f"{generator_scene.snu_slideshow_generator.base_name}-{slide.name}-TextOverlay"
    
    if bpy.data.scenes.find(text_scene_name) != -1:
        bpy.data.scenes.remove(bpy.data.scenes[text_scene_name])
    
    text_scene = create_scene(generator_scene, text_scene_name)
    fps = get_fps(text_scene)
    text_scene.frame_end = int(fps * slide_duration)
    
    text_scene.render.film_transparent = True
    text_scene.eevee.use_taa_reprojection = True
    text_scene.eevee.taa_samples = 16
    
    try:
        if hasattr(text_scene.eevee, 'use_bloom'):
            text_scene.eevee.use_bloom = False
    except AttributeError:
        pass
    
    world = bpy.data.worlds.new(text_scene.name)
    text_scene.world = world
    world.use_nodes = True
    world.node_tree.nodes.clear()
    
    output_node = world.node_tree.nodes.new('ShaderNodeOutputWorld')
    transparent_node = world.node_tree.nodes.new('ShaderNodeBackground')
    transparent_node.inputs[0].default_value = (0, 0, 0, 0)
    transparent_node.inputs[1].default_value = 0
    world.node_tree.links.new(transparent_node.outputs[0], output_node.inputs[0])
    
    text_alignment = generator_scene.snu_slideshow_generator.text_alignment
    
    y_offset = generator_scene.snu_slideshow_generator.text_y_offset
    text_size = generator_scene.snu_slideshow_generator.text_size
    current_start_frame = 1
    delay_between_texts = int(fps * 1.2)
    
    materials_to_fade = []
    fade_start_frame = None
    fade_end_frame = None

    for field_name, label in text_fields:
        field_value = getattr(slide.slideshow, field_name, '')
        if not field_value:
            continue

        text_content = f"{label}: {field_value}"
        main_text_obj, outline_text_obj, main_material, outline_material, animation_duration = create_typewriter_text_with_improved_outline(
            text_scene,
            text_content,
            f"{field_name.title()}_Text",
            location=get_text_location(generator_scene, y_offset, text_size),
            size=text_size,
            alignment=text_alignment,
            start_frame=current_start_frame,
        )

        # ensure animation_duration is valid
        if not animation_duration:
            # fallback: estimate based on length of text or minimum 20 frames
            animation_duration = max(len(text_content) * 2, 20)

        # collect materials
        if main_material:
            materials_to_fade.append((main_text_obj, main_material))
        if outline_material:
            materials_to_fade.append((outline_text_obj, outline_material))

        # compute fade timing relative to last text created
        if fade_start_frame is None:
            fade_start_frame = current_start_frame
        fade_end_frame = current_start_frame + animation_duration

        # update frame & layout offset
        current_start_frame += delay_between_texts
        y_offset -= 0.35

    # apply fade once for all collected text materials
    if materials_to_fade and fade_start_frame is not None and fade_end_frame is not None:
        fade_start = int(fps * slide_duration) - 20  # start fade near end
        for obj, material in materials_to_fade:
            add_fade_animation(obj, material, text_scene, start_frame=fade_start, duration=20)
    
    camera = add_object(text_scene, f"{text_scene.name}_Camera", 'CAMERA')
    camera.location = (0, 0, 5)
    camera.data.clip_start = 0.1
    camera.data.clip_end = 100.0
    text_scene.camera = camera
    
    return text_scene



def get_material_elements(material, image_name):
    tree = material.node_tree
    nodes = tree.nodes
    texture = None
    shadeless = None
    shaded = None
    mix = None
    output = None
    for node in nodes:
        if node.type == 'TEX_IMAGE':
            texture = node
        if node.type == 'EMISSION':
            shadeless = node
        if node.type == 'BSDF_PRINCIPLED':
            shaded = node
        if node.type == 'MIX_SHADER':
            mix = node
        if node.type == 'OUTPUT_MATERIAL':
            output = node
    if texture is None or shadeless is None or shaded is None or mix is None or output is None:
        if texture is not None:
            image = texture.image
        elif image_name in bpy.data.images:
            image = bpy.data.images[image_name]
        else:
            return None
        return setup_material(material, image)
    else:
        material_nodes = {
            'texture': texture,
            'shadeless': shadeless,
            'shaded': shaded,
            'mix': mix,
            'output': output
        }
        return material_nodes


def setup_material(material, image):
    material.use_nodes = True
    tree = material.node_tree
    nodes = tree.nodes
    nodes.clear()

    texture = nodes.new('ShaderNodeTexImage')
    texture.image = image
    texture.image_user.frame_duration = image.frame_duration
    texture.image_user.frame_offset = 0
    texture.image_user.use_auto_refresh = True
    texture.location = (-400, 0)
    shadeless = nodes.new('ShaderNodeEmission')
    shadeless.location = (0, 0)
    shaded = nodes.new('ShaderNodeBsdfPrincipled')
    shaded.location = (-100, -150)
    mix = nodes.new('ShaderNodeMixShader')
    mix.location = (200, 0)
    mix.inputs[0].default_value = 0
    output = nodes.new('ShaderNodeOutputMaterial')
    output.location = (400, 0)

    tree.links.new(texture.outputs[0], shadeless.inputs[0])
    tree.links.new(texture.outputs[0], shaded.inputs[0])
    tree.links.new(shadeless.outputs[0], mix.inputs[1])
    tree.links.new(shaded.outputs[0], mix.inputs[2])
    tree.links.new(mix.outputs[0], output.inputs[0])
    material_nodes = {
        'texture': texture,
        'shadeless': shadeless,
        'shaded': shaded,
        'mix': mix,
        'output': output
    }
    return material_nodes


def import_slideshow_image(image, image_number, slide_length, generator_scene, video=False, last_image=None):
    if len(image.name) > 20:
        image.name = image.name[0:19]
    if video:
        print('Importing video '+str(image_number)+', filename: '+image.name)
    else:
        print('Importing image '+str(image_number)+', filename: '+image.name)

    bpy.context.scene.cursor.location = (0.0, 0.0, 0.0)
    ix = ((image.size[0] / image.size[1])/2)
    iy = 0.5
    verts = [(-ix, iy, 0.0), (ix, iy, 0.0), (ix, -iy, 0.0), (-ix, -iy, 0.0)]
    faces = [(3, 2, 1, 0)]
    image_plane = add_object(generator_scene, image.name, 'MESH', mesh_verts=verts, mesh_faces=faces)
    image_plane.slideshow.name = image_plane.name
    add_constraints(image_plane, 'Plane')

    text_data = load_slide_text_data(bpy.path.abspath(image.filepath))
    image_plane.slideshow.text_photographer = text_data['photographer']
    image_plane.slideshow.text_when = text_data['when']
    image_plane.slideshow.text_who = text_data['who']
    image_plane.slideshow.text_where = text_data['where']
    image_plane.slideshow.has_text_file = text_data['has_text']

    if text_data['has_text'] and any([text_data['photographer'], text_data['when'], 
                                     text_data['who'], text_data['where']]):
        image_plane.slideshow.enable_text_overlay = True

    if video:
        image_plane.slideshow.locklength = True
        image_plane.slideshow.lockextra = True
        image_plane.slideshow.locktransform = True
        image_plane.slideshow.videomaxlength = image.frame_duration
        image_plane.slideshow.videofile = image.filepath
        slide_length = image.frame_duration / get_fps(generator_scene)

    image_material = bpy.data.materials.new(image_plane.name)
    image_plane.data.uv_layers.new()
    image_plane.data.materials.append(image_material)
    setup_material(image_material, image)

    if not video:
        randomized = []
        hidden = generator_scene.snu_slideshow_generator.hidden_transforms.split(";")
        for transform in transforms:
            if transform['name'] not in hidden:
                if last_image:
                    if transform['name'] != last_image.slideshow.transform:
                        randomized.append(transform)
                else:
                    randomized.append(transform)
        if len(randomized) == 0:
            transform = transforms[0]
        else:
            transform = randomized[random.randint(0, (len(randomized) - 1))]

        randomized = []
        hidden = generator_scene.snu_slideshow_generator.hidden_extras.split(";")
        extras = list_extras()
        for extra in extras:
            if extra not in hidden:
                if last_image:
                    if extra != last_image.slideshow.extra:
                        randomized.append(extra)
                else:
                    randomized.append(extra)
        if len(randomized) == 0:
            extra = "None"
        else:
            extra = randomized[random.randint(0, (len(randomized) - 1))]

        randomized = []
        for extra_texture_preset in generator_scene.snu_slideshow_generator.extra_texture_presets:
            if last_image:
                if extra_texture_preset.path != last_image.slideshow.extratexture:
                    randomized.append(extra_texture_preset.path)
            else:
                randomized.append(extra_texture_preset.path)
        if len(randomized) == 0:
            extra_texture = 'None'
        else:
            if len(generator_scene.snu_slideshow_generator.extra_texture_presets) > 1:
                extra_texture = randomized[random.randint(0, (len(randomized) - 1))]
            else:
                extra_texture = generator_scene.snu_slideshow_generator.extra_texture_presets[0].path

        target_empty = add_object(generator_scene, image_plane.name+' Target', 'EMPTY')
        target_empty.parent = image_plane
        target_empty.empty_display_size = 1
        add_constraints(target_empty, 'Target')
        image_plane.slideshow.target = target_empty.name

        view_empty = add_object(generator_scene, image_plane.name+' View', 'EMPTY')
        view_empty.parent = image_plane
        view_empty.empty_display_size = 1
        view_empty.scale = aspect_ratio(generator_scene) / 2, .5, .001
        view_empty.empty_display_type = 'CUBE'
        add_constraints(view_empty, 'View')
        image_plane.slideshow.view = view_empty.name

    index_text = add_object(generator_scene, image_plane.name+' Index', 'FONT')
    index_text.parent = image_plane
    index_text.location = (-1, -.33, 0)
    index_text.data.align_x = 'RIGHT'
    add_constraints(index_text, 'Text')

    if not video:
        transform_text = add_object(generator_scene, image_plane.name+' Transform', 'FONT')
        transform_text.parent = image_plane
        transform_text.location = (1, 0, 0)
        transform_text.scale = .15, .15, 1
        add_constraints(transform_text, 'Text')

        extra_text = add_object(generator_scene, image_plane.name+' Extra', 'FONT')
        extra_text.parent = image_plane
        extra_text.location = (1, -.25, 0)
        extra_text.scale = .15, .15, 1
        add_constraints(extra_text, 'Text')

    length_text = add_object(generator_scene, image_plane.name+' Length', 'FONT')
    length_text.parent = image_plane
    length_text.location = (1, .25, 0)
    length_text.scale = .15, .15, 1
    add_constraints(length_text, 'Text')

    image_group = bpy.data.collections.new(image_plane.name)
    image_group.objects.link(image_plane)
    image_group.objects.link(index_text)
    image_group.objects.link(length_text)
    if not video:
        image_group.objects.link(target_empty)
        image_group.objects.link(transform_text)
        image_group.objects.link(extra_text)
        image_group.objects.link(view_empty)

    image_plane.slideshow.index = image_number + 1
    if not video:
        image_plane.slideshow.length = slide_length
        image_plane.slideshow.transform = transform['name']
        image_plane.slideshow.extra = extra
        image_plane.slideshow.extratexture = extra_texture
    else:
        image_plane.slideshow.videolength = image.frame_duration
    return image_plane


def add_constraints(constraint_object, constraint_type):
    rotation_constraint = constraint_object.constraints.new(type='LIMIT_ROTATION')
    location_constraint = constraint_object.constraints.new(type='LIMIT_LOCATION')
    scale_constraint = constraint_object.constraints.new(type='LIMIT_SCALE')

    rotation_constraint.use_limit_x = True
    rotation_constraint.use_limit_y = True
    if constraint_type != 'View':
        rotation_constraint.use_limit_z = True

    constraint_object.constraints[1].owner_space = 'LOCAL'
    if constraint_type == 'Target' or constraint_type == 'View':
        location_constraint.min_x = -1 * (aspect_ratio(bpy.context.scene)/2)
        location_constraint.max_x = aspect_ratio(bpy.context.scene) / 2
        location_constraint.min_y = -.5
        location_constraint.max_y = .5
    else:
        location_constraint.min_x = constraint_object.location[0]
        location_constraint.max_x = constraint_object.location[0]
        location_constraint.min_y = constraint_object.location[1]
        location_constraint.max_y = constraint_object.location[1]
    location_constraint.use_max_x = True
    location_constraint.use_min_x = True
    if constraint_type != 'Plane':
        location_constraint.use_max_y = True
        location_constraint.use_min_y = True
    location_constraint.use_max_z = True
    location_constraint.use_min_z = True

    scale_constraint.min_x = constraint_object.scale[0]
    scale_constraint.max_x = constraint_object.scale[0]
    scale_constraint.min_y = constraint_object.scale[1]
    scale_constraint.max_y = constraint_object.scale[1]
    scale_constraint.min_z = constraint_object.scale[2]
    scale_constraint.max_z = constraint_object.scale[2]
    if constraint_type != 'View':
        scale_constraint.use_min_x = True
        scale_constraint.use_max_x = True
        scale_constraint.use_min_y = True
        scale_constraint.use_max_y = True
        scale_constraint.use_min_z = True
        scale_constraint.use_max_z = True

    if constraint_type == 'Text':
        limit_location_constraint = constraint_object.constraints.new(type='LIMIT_LOCATION')
        limit_location_constraint.owner_space = 'WORLD'
        limit_location_constraint.use_max_x = True
        limit_location_constraint.use_min_x = True
        limit_location_constraint.min_x = constraint_object.location[0]
        limit_location_constraint.max_x = constraint_object.location[0]


def is_video_file(file):
    file = bpy.path.abspath(file)
    if os.path.isfile(file):
        extensions = bpy.path.extensions_movie
        extension = os.path.splitext(file)[1]
        if extension.lower() in extensions:
            return True
    return False


def clear_sequencer(scene):
    scene.sequence_editor_clear()


def add_object(scene, name, object_type, mesh_verts=[], mesh_faces=[]):
    created = None
    if object_type == 'EMPTY':
        created = bpy.data.objects.new(name=name, object_data=None)
    elif object_type == 'FONT':
        object_data = bpy.data.curves.new(name=name, type='FONT')
        created = bpy.data.objects.new(name=name, object_data=object_data)
    elif object_type == 'MESH':
        mesh = bpy.data.meshes.new(name=name)
        mesh.from_pydata(mesh_verts, [], mesh_faces)
        created = bpy.data.objects.new(name=name, object_data=mesh)
    elif object_type == 'CAMERA':
        camera = bpy.data.cameras.new(name=name)
        created = bpy.data.objects.new(name=name, object_data=camera)
    if created is not None:
        scene.collection.objects.link(created)
    return created


def create_slideshow_slide(image_plane, i, generator_scene, image_scene_start, images, previous_image_clip, previous_image_plane):
    base_name = generator_scene.snu_slideshow_generator.base_name
    image_scene_name = base_name + '-' + image_plane.name

    if not generator_scene.sequence_editor:
        generator_scene.sequence_editor_create()

    if not image_plane.slideshow.videofile:
        print('Generating scene for: '+image_scene_name)
        if bpy.data.scenes.find(image_scene_name) != -1:
            bpy.data.scenes.remove(bpy.data.scenes[image_scene_name])
        image_scene = create_scene(generator_scene, image_scene_name)
        image_scene.snu_slideshow_generator.generator_name = generator_scene.name
        image_scene.snu_slideshow_generator.base_name = base_name
        image_scene.eevee.taa_render_samples = generator_scene.snu_slideshow_generator.render_samples

        image_scene_frames = int(get_fps(image_scene) * image_plane.slideshow.length)
        image_scene.frame_end = image_scene_frames

        target_empty = generator_scene.objects[image_plane.slideshow.target]
        view_empty = generator_scene.objects[image_plane.slideshow.view]
        image_scene.collection.objects.link(image_plane)
        image_scene.collection.objects.link(target_empty)
        image_scene.collection.objects.link(view_empty)

        world = bpy.data.worlds.new(image_scene.name)
        image_scene.world = world
        world.use_nodes = False
        world.color = (0, 0, 0)

        transform_index = get_transform(image_plane.slideshow.transform)
        if transform_index >= 0:
            transform = transforms[transform_index]
        else:
            transform = transforms[0]
        image_scene.cursor.location = (0.0, 0.0, 0.0)
        image_scene.frame_current = 1
        transform_empty = add_object(image_scene, transform['name'], 'EMPTY')
        transform_empty.animation_data_create()
        transform_action = bpy.data.actions.new(transform['name'])
        transform_empty.animation_data.action = transform_action
        aspect = aspect_ratio(image_scene)
        multiplier = 1.375
        if aspect > 1:
            zoffset = aspect * multiplier
        else:
            zoffset = multiplier
        transform_interpolation = image_plane.slideshow.transform_interpolation

        transform_empty.location = (0, 0, zoffset)
        if 'zLoc' in transform.keys():
            locations = len(transform['zLoc'])
            fcurve = transform_action.fcurves.new('location', index=2)
            for index, location in enumerate(transform['zLoc']):
                if locations == 1:
                    pointx = 1
                else:
                    pointx = ((index * image_scene_frames)/(locations - 1)) + 1
                pointy = transform['zLoc'][index][0] + zoffset
                pointsize = (transform['zLoc'][index][1]) * (image_scene_frames / locations / 2)
                point = fcurve.keyframe_points.insert(frame=pointx, value=pointy)
                point.interpolation = transform_interpolation
                point.handle_left_type = 'FREE'
                point.handle_right_type = 'FREE'
                point.handle_left = (pointx - pointsize, pointy)
                point.handle_right = (pointx + pointsize, pointy)
        if 'zRot' in transform.keys():
            locations = len(transform['zRot'])
            fcurve = transform_action.fcurves.new('rotation_euler', index=2)
            for index, location in enumerate(transform['zRot']):
                if locations == 1:
                    pointx = 1
                else:
                    pointx = ((index * image_scene_frames)/(locations - 1)) + 1
                pointy = 3.14159265358979 * (transform['zRot'][index][0]) / 180
                pointsize = (transform['zRot'][index][1]) * (image_scene_frames / locations / 2)
                point = fcurve.keyframe_points.insert(frame=pointx, value=pointy)
                point.interpolation = transform_interpolation
                point.handle_left_type = 'FREE'
                point.handle_right_type = 'FREE'
                point.handle_left = (pointx - pointsize, pointy)
                point.handle_right = (pointx + pointsize, pointy)
        if 'xLoc' in transform.keys():
            locations = len(transform['xLoc'])
            fcurve = transform_action.fcurves.new('location', index=0)
            for index, location in enumerate(transform['xLoc']):
                if locations == 1:
                    pointx = 1
                else:
                    pointx = ((index * image_scene_frames)/(locations - 1)) + 1
                pointy = (transform['xLoc'][index][0]) * aspect_ratio(bpy.context.scene)
                pointsize = (transform['xLoc'][index][1]) * (image_scene_frames / locations / 2)
                point = fcurve.keyframe_points.insert(frame=pointx, value=pointy)
                point.interpolation = transform_interpolation
                point.handle_left_type = 'FREE'
                point.handle_right_type = 'FREE'
                point.handle_left = (pointx - pointsize, pointy)
                point.handle_right = (pointx + pointsize, pointy)
        if 'influence' in transform.keys():
            constraint = transform_empty.constraints.new(type='COPY_LOCATION')
            constraint.use_z = False
            constraint.target = target_empty
            constraint.influence = 0
            locations = len(transform['influence'])
            fcurve = transform_action.fcurves.new('constraints[0].influence')
            for index, location in enumerate(transform['influence']):
                if locations == 1:
                    pointx = 1
                else:
                    pointx = ((index * image_scene_frames)/(locations - 1)) + 1
                pointy = transform['influence'][index][0]
                pointsize = (transform['influence'][index][1]) * (image_scene_frames / locations / 2)
                point = fcurve.keyframe_points.insert(frame=pointx, value=pointy)
                point.interpolation = transform_interpolation
                point.handle_left_type = 'FREE'
                point.handle_right_type = 'FREE'
                point.handle_left = (pointx - pointsize, pointy)
                point.handle_right = (pointx + pointsize, pointy)

        if not transform_empty.animation_data.action_slot:
            transform_empty.animation_data.action_slot = transform_action.slots[0]

        camera = add_object(image_scene, generator_scene.name+' Camera', 'CAMERA')
        camera.parent = transform_empty
        image_scene.camera = camera
        camera.data.dof.focus_object = image_plane
        camera.data.dof.use_dof = False

        camera_scale = add_object(image_scene, generator_scene.name+' Camera Scale', 'EMPTY')
        camera_scale.parent = image_plane
        transform_empty.parent = camera_scale
        camera_scale.location = view_empty.location
        camera_scale.rotation_euler = view_empty.rotation_euler
        camera_scale_value = (view_empty.scale[1] * 2)
        camera_scale.scale = (camera_scale_value, camera_scale_value, camera_scale_value)

        if image_plane.slideshow.extra != 'None':
            extra = get_extra(image_plane.slideshow.extra)
            if extra:
                current_scene = bpy.context.window.scene
                try:
                    folder = os.path.split(extra)[0]
                    file = os.path.splitext(os.path.split(extra)[1])[0]
                    sys.path.insert(0, folder)
                    script = __import__(file)
                    sys.path.remove(folder)
                    image = load_image(bpy.path.abspath(image_plane.slideshow.extratexture))
                    material = image_plane.material_slots[0].material
                    material_nodes = get_material_elements(material, image_plane.slideshow.name)
                    if material_nodes is not None:
                        data = {
                            'image_scene': image_scene,
                            'image_plane': image_plane,
                            'material': material,
                            'material_texture': material_nodes['texture'],
                            'material_shadeless': material_nodes['shadeless'],
                            'material_shaded': material_nodes['shaded'],
                            'material_mix': material_nodes['mix'],
                            'material_output': material_nodes['output'],
                            'target_empty': target_empty,
                            'camera': camera,
                            'extra_amount': image_plane.slideshow.extraamount,
                            'extra_text': image_plane.slideshow.extratext,
                            'extra_texture': image}
                        script.extra(data)
                    del script
                    bpy.context.window.scene = current_scene
                except ImportError:
                    pass

        clip = generator_scene.sequence_editor.sequences.new_scene(scene=image_scene, name=image_scene.name, channel=((i % 2) + 1), frame_start=image_scene_start)

    else:
        print('Importing Clip: '+image_scene_name)
        image_scene_frames = image_plane.slideshow.videolength
        rotate = image_plane.slideshow.rotate

        aspect = aspect_ratio(generator_scene)
        clipx = image_plane.dimensions[0]
        clipy = image_plane.dimensions[1]
        clip_aspect = clipx / clipy
        aspect_difference = abs(aspect - clip_aspect)
        if aspect_difference > 0.1:
            blur_background = image_plane.slideshow.videobackground
        else:
            blur_background = False

        base_channel = ((i % 2) + 1)
        blur_base_channel = base_channel
        if blur_background:
            base_channel = base_channel + 3

        bpy.ops.sequencer.select_all(action='DESELECT')
        clip = generator_scene.sequence_editor.sequences.new_movie(filepath=image_plane.slideshow.videofile, name=image_plane.name, channel=base_channel, frame_start=image_scene_start)
        flipped = False
        if rotate == '90':
            flipped = True
            clip.transform.rotation = 0 - math.pi/2
        elif rotate == '180':
            clip.transform.rotation = math.pi
        elif rotate == '-90':
            flipped = True
            clip.transform.rotation = math.pi / 2
        if blur_background:
            blur_clip = generator_scene.sequence_editor.sequences.new_movie(filepath=image_plane.slideshow.videofile, name=image_plane.name, channel=blur_base_channel, frame_start=image_scene_start)
            blur_clip.transform.rotation = clip.transform.rotation
        else:
            blur_clip = None

        image = get_image(image_plane.slideshow.videofile)
        clip_x = image.size[0]
        clip_y = image.size[1]

        render = generator_scene.render
        scene_x = render.resolution_x
        scene_y = render.resolution_y
        video_aspect = clip_x / clip_y

        if video_aspect <= aspect:
            if not flipped:
                video_scale = scene_y / clip_y
                blur_scale = scene_x / clip_x
            else:
                video_scale = scene_y / clip_x
                blur_scale = scene_x / clip_y
        else:
            if not flipped:
                video_scale = scene_x / clip_x
                blur_scale = scene_y / clip_y
            else:
                video_scale = scene_x / clip_y
                blur_scale = scene_y / clip_x

        clip.transform.scale_x = video_scale
        clip.transform.scale_y = video_scale
        if blur_background:
            blur_clip.transform.scale_x = blur_scale
            blur_clip.transform.scale_y = blur_scale

        speed_clip = None
        audioclip = None
        blur_speed_clip = None
        blur_blur_clip = None
        if image_plane.slideshow.videoaudio:
            audioclip = generator_scene.sequence_editor.sequences.new_sound(filepath=image_plane.slideshow.videofile, name=image_plane.name, channel=base_channel +2, frame_start=image_scene_start)
            if audioclip.frame_duration == 0:
                generator_scene.sequence_editor.sequences.remove(audioclip)
                print('No Audio Found For This Clip')
                audioclip = None

            else:
                generator_scene.frame_current = image_scene_start
                audioclip.volume = 0
                audioclip.keyframe_insert(data_path='volume')
                generator_scene.frame_current = image_scene_start + generator_scene.snu_slideshow_generator.crossfade_length
                audioclip.volume = 1
                audioclip.keyframe_insert(data_path='volume')
                generator_scene.frame_current = audioclip.frame_final_end - generator_scene.snu_slideshow_generator.crossfade_length
                audioclip.keyframe_insert(data_path='volume')
                generator_scene.frame_current = audioclip.frame_final_end
                audioclip.volume = 0
                audioclip.keyframe_insert(data_path='volume')
                length_percent = image_scene_frames / clip.frame_final_duration
                if audioclip.frame_final_duration != clip.frame_final_duration:
                    speed_clip = generator_scene.sequence_editor.sequences.new_effect(name='Speed', type='SPEED', channel=clip.channel+1, seq1=clip, frame_start=clip.frame_final_start)
                    if audioclip.frame_final_duration > 1:
                        clip.frame_final_duration = audioclip.frame_final_duration
                    if blur_background:
                        blur_speed_clip = generator_scene.sequence_editor.sequences.new_effect(name='Speed', type='SPEED', channel=blur_clip.channel+1, seq1=blur_clip, frame_start=blur_clip.frame_final_start)
                        blur_clip.frame_final_duration = clip.frame_final_duration
                image_scene_frames = audioclip.frame_final_duration * length_percent

        if speed_clip:
            apply_transform = speed_clip
            if blur_background:
                blur_apply_transform = blur_speed_clip
            else:
                blur_apply_transform = None
        else:
            apply_transform = clip
            if blur_background:
                blur_apply_transform = blur_clip
            else:
                blur_apply_transform = None
        apply_transform.select = True
        if blur_background:
            blur_apply_transform.select = True
        if blur_background:
            blur_blur_clip = generator_scene.sequence_editor.sequences.new_effect(name='Blur', type='GAUSSIAN_BLUR', channel=blur_apply_transform.channel+1, seq1=blur_apply_transform, frame_start=blur_apply_transform.frame_final_start)
            blur_blur_clip.size_x = 40
            blur_blur_clip.size_y = 40

        generator_scene.sequence_editor.active_strip = clip
        if blur_clip:
            blur_clip.select = True
        if blur_speed_clip:
            blur_speed_clip.select = True
        if blur_blur_clip:
            blur_blur_clip.select = True
        if speed_clip:
            speed_clip.select = True
        if audioclip:
            audioclip.select = True
        clip.select = True

        bpy.ops.sequencer.meta_make()
        clip = generator_scene.sequence_editor.active_strip

        offset = image_plane.slideshow.videooffset
        clip.frame_offset_start = offset
        clip.frame_start = image_scene_start - offset
        if image_plane.slideshow.videolength < clip.frame_final_duration:
            clip.frame_final_duration = image_plane.slideshow.videolength
        if blur_background:
            clip.channel = blur_base_channel
        else:
            clip.channel = base_channel

    if i == 0:
        clip.blend_type = 'ALPHA_OVER'
        generator_scene.frame_current = 1
        clip.blend_alpha = 0
        clip.keyframe_insert(data_path='blend_alpha')
        generator_scene.frame_current = generator_scene.snu_slideshow_generator.crossfade_length
        clip.blend_alpha = 1
        clip.keyframe_insert(data_path='blend_alpha')

    if generator_scene.snu_slideshow_generator.crossfade_length > 0:
        if previous_image_clip and previous_image_plane:
            first_sequence = previous_image_clip
            second_sequence = clip
            if previous_image_plane.slideshow.transition == "GAMMA_CROSS":
                effect = generator_scene.sequence_editor.sequences.new_effect(name=previous_image_clip.name+' to '+clip.name, channel=3, frame_start=second_sequence.frame_final_start, frame_end=first_sequence.frame_final_end, type='GAMMA_CROSS', seq1=first_sequence, seq2=second_sequence)
                effect.frame_still_end = first_sequence.frame_final_end
            elif previous_image_plane.slideshow.transition == "WIPE":
                effect = generator_scene.sequence_editor.sequences.new_effect(name=previous_image_clip.name+' to '+clip.name, channel=3, frame_start=second_sequence.frame_final_start, frame_end=first_sequence.frame_final_end, type='WIPE', seq1=first_sequence, seq2=second_sequence)
                effect.frame_still_end = first_sequence.frame_final_end
                effect.transition_type = previous_image_plane.slideshow.wipe_type
                effect.direction = previous_image_plane.slideshow.wipe_direction
                if previous_image_plane.slideshow.wipe_soft:
                    effect.blur_width = 0.2
                if previous_image_plane.slideshow.wipe_angle == 'RIGHT':
                    effect.angle = 0 - (math.pi / 2)
                elif previous_image_plane.slideshow.wipe_angle == 'LEFT':
                    effect.angle = math.pi / 2
                elif previous_image_plane.slideshow.wipe_angle == 'UP':
                    effect.angle = 0
                    if effect.direction == 'IN':
                        effect.direction = 'OUT'
                    else:
                        effect.direction = 'IN'
                else:
                    effect.angle = 0
            elif previous_image_plane.slideshow.transition == "CUSTOM" and is_video_file(previous_image_plane.slideshow.custom_transition_file):
                effect_channel = first_sequence.channel
                if second_sequence.channel > effect_channel:
                    effect_channel = second_sequence.channel
                if second_sequence.channel > first_sequence.channel:
                    inverted = False
                    start_color = (0, 0, 0)
                    end_color = (1, 1, 1)
                    apply_mask_to = second_sequence
                else:
                    inverted = True
                    start_color = (1, 1, 1)
                    end_color = (0, 0, 0)
                    apply_mask_to = first_sequence
                bpy.ops.sequencer.select_all(action='DESELECT')
                file_path = bpy.path.abspath(previous_image_plane.slideshow.custom_transition_file)
                effect = generator_scene.sequence_editor.sequences.new_movie(filepath=file_path, name=previous_image_plane.name+' Transition', channel=effect_channel + 1, frame_start=second_sequence.frame_final_start + 1)
                effect.frame_final_end = first_sequence.frame_final_end - 1
                if inverted:
                    invert_modifier = effect.modifiers.new(name='Invert Colors', type='CURVES')
                    invert_modifier.curve_mapping.curves[3].points[0].location = (0, 1)
                    invert_modifier.curve_mapping.curves[3].points[1].location = (1, 0)
                effect_speed = generator_scene.sequence_editor.sequences.new_effect(name='Speed', type='SPEED', channel=effect.channel + 1, seq1=effect, frame_start=effect.frame_final_start)
                effect_final = generator_scene.sequence_editor.sequences.new_effect(name='Color', type='COLOR', channel=effect.channel, frame_start=effect.frame_final_end, frame_end=effect.frame_final_end + 1)
                effect_final.frame_final_end = effect_final.frame_final_start + 1
                effect_final.color = end_color
                effect_start = generator_scene.sequence_editor.sequences.new_effect(name='Color', type='COLOR', channel=effect.channel, frame_start=effect.frame_final_start - 1, frame_end=effect.frame_final_start)
                effect_start.frame_final_end = effect_start.frame_final_start + 1
                effect_start.color = start_color
                effect.select = True
                effect_speed.select = True
                effect_final.select = True
                effect_start.select = True
                bpy.ops.sequencer.meta_make()
                effect = generator_scene.sequence_editor.active_strip
                effect.name = previous_image_clip.name+' to '+clip.name
                effect.channel = effect_channel + 1
                effect.mute = True
                apply_mask_to.blend_type = 'ALPHA_OVER'
                modifier = apply_mask_to.modifiers.new(name='Transition from '+first_sequence.name, type='MASK')
                modifier.input_mask_type = 'STRIP'
                modifier.input_mask_strip = effect
            elif previous_image_plane.slideshow.transition == "NONE":
                pass
            else:
                effect = generator_scene.sequence_editor.sequences.new_effect(name=previous_image_clip.name+' to '+clip.name, channel=3, frame_start=second_sequence.frame_final_start, frame_end=first_sequence.frame_final_end, type='CROSS', input1=first_sequence, input2=second_sequence)

    if i == (len(images) - 1):
        clip.blend_type = 'ALPHA_OVER'
        generator_scene.frame_current = int(image_scene_start + image_scene_frames)
        clip.blend_alpha = 0
        clip.keyframe_insert(data_path='blend_alpha')
        generator_scene.frame_current = int(image_scene_start + image_scene_frames - generator_scene.snu_slideshow_generator.crossfade_length)
        clip.blend_alpha = 1
        clip.keyframe_insert(data_path='blend_alpha')
        generator_scene.frame_current = 1

    return clip


def extras_path():
    script_file = os.path.realpath(__file__)
    directory = os.path.dirname(script_file)
    extras_directory = directory+os.path.sep+'Extras'+os.path.sep
    if os.path.exists(extras_directory):
        return extras_directory
    return os.path.split(bpy.data.filepath)[0]+os.path.sep+"Extras"+os.path.sep


def list_extras():
    extras = []
    extraspath = extras_path()
    extrafiles = glob.glob(extraspath+'*')
    for file in extrafiles:
        if os.path.splitext(file)[1] == '.py':
            extras.append(os.path.splitext(os.path.split(file)[1])[0])
    return extras


def get_extra(filename):
    extra = None
    extraspath = extras_path()
    extrafiles = glob.glob(extraspath+'*')
    for file in extrafiles:
        if os.path.splitext(os.path.split(file)[1])[0] == filename:
            extra = file
    return extra


def get_transform(name):
    for index, transform in enumerate(transforms):
        if transform['name'] == name:
            return index
    return -1


def update_slide_length(self, context):
    current_scene = context.scene
    length_text = current_scene.objects[self.name+" Length"]
    length_text.data.body = "Length: "+str(round(self.length, 2))+" Seconds"


def update_video_length(self, context):
    current_scene = context.scene
    length_text = current_scene.objects[self.name+" Length"]
    if self.videolength + self.videooffset > self.videomaxlength:
        self.videolength = self.videomaxlength - self.videooffset
    length_text.data.body = "Length: "+str(self.videolength)+" Frames"


def update_offset(self, context):
    current_scene = context.scene
    image_plane = current_scene.objects[self.name]
    material = image_plane.material_slots[0].material
    material_nodes = get_material_elements(material, image_plane.slideshow.name)
    if material_nodes is None:
        return
    material_nodes['texture'].image_user.frame_offset = self.videooffset
    maxlength = self.videomaxlength - 1
    if self.videooffset > maxlength:
        self.videooffset = maxlength
    if self.videooffset + self.videolength > self.videomaxlength:
        self.videolength = self.videomaxlength - self.videooffset
        return
    update_video_length(self, context)


def update_extra(self, context):
    try:
        current_scene = context.scene
        extra_text = current_scene.objects[self.name+" Extra"]
        extra_text.data.body = "Extra: "+self.extra
    except:
        pass


def update_transform(self, context):
    try:
        current_scene = context.scene
        transform_text = current_scene.objects[self.name+" Transform"]
        transform_text.data.body = "Transform: "+self.transform
    except:
        pass


def update_index(self, context):
    current_scene = context.scene
    image_plane = current_scene.objects[self.name]
    position = -self.index
    image_plane.location = (0.0, position, 0.0)
    index_text = current_scene.objects[self.name+" Index"]
    index_text.data.body = str(self.index + 1)


def update_rotate(self, context):
    current_scene = context.scene
    image_plane = current_scene.objects[self.name]
    mesh = image_plane.data
    material = image_plane.material_slots[0].material
    material_nodes = get_material_elements(material, image_plane.slideshow.name)
    if material_nodes is None:
        return
    image = material_nodes['texture'].image
    iy = 0.5
    if self.rotate == '0':
        ix = ((image.size[0] / image.size[1])/2)
        mesh.vertices[0].co = (-ix, iy, 0)
        mesh.vertices[1].co = (ix, iy, 0)
        mesh.vertices[2].co = (ix, -iy, 0)
        mesh.vertices[3].co = (-ix, -iy, 0)
    elif self.rotate == '-90':
        ix = ((image.size[1] / image.size[0])/2)
        mesh.vertices[0].co = (-ix, -iy, 0)
        mesh.vertices[1].co = (-ix, iy, 0)
        mesh.vertices[2].co = (ix, iy, 0)
        mesh.vertices[3].co = (ix, -iy, 0)
    elif self.rotate == '180':
        ix = ((image.size[0] / image.size[1])/2)
        mesh.vertices[0].co = (ix, -iy, 0)
        mesh.vertices[1].co = (-ix, -iy, 0)
        mesh.vertices[2].co = (-ix, iy, 0)
        mesh.vertices[3].co = (ix, iy, 0)
    else:
        ix = ((image.size[1] / image.size[0])/2)
        mesh.vertices[0].co = (ix, iy, 0)
        mesh.vertices[1].co = (ix, -iy, 0)
        mesh.vertices[2].co = (-ix, -iy, 0)
        mesh.vertices[3].co = (-ix, iy, 0)


def list_slides(scene):
    slides = []
    for slide_object in scene.objects:
        if slide_object.slideshow.name == slide_object.name:
            slides.append(slide_object)
    return slides


def slideshow_length(slides=None, fps=None):
    scene = bpy.context.scene
    if not slides:
        slides = list_slides(scene)
    if not fps:
        fps = get_fps(scene)
    length = 0.0
    crossfade_length = (scene.snu_slideshow_generator.crossfade_length / fps)
    default_length = scene.snu_slideshow_generator.slide_length
    for index, slide in enumerate(slides):
        if hasattr(slide, 'slideshow'):
            if slide.slideshow.videofile:
                length = length + (slide.slideshow.videolength / fps)
            else:
                length = length + slide.slideshow.length
        else:
            length = length + default_length
        if index > 0:
            length = length - crossfade_length
    return length


def update_aspect(slide, scene, aspect):
    try:
        view_empty = scene.objects[slide.slideshow.view]
        scale_basis = view_empty.scale[1]
        new_scale = aspect * scale_basis, scale_basis, .001
        view_empty.scale = new_scale
    except:
        pass


def update_order(mode='none', current_scene=None):
    if not current_scene:
        current_scene = bpy.context.scene
    slides = list_slides(current_scene)

    if mode == 'none':
        changed = False
        oldorder = []
        aspect = round(aspect_ratio(current_scene), 4)
        old_aspect = round(current_scene.snu_slideshow_generator.aspect_ratio, 4)
        for slide in slides:
            if aspect != old_aspect:
                update_aspect(slide, current_scene, aspect)
            loc = -slide.location[1]
            oldorder.append([loc, slide])
        current_scene.snu_slideshow_generator.aspect_ratio = aspect
        neworder = sorted(oldorder, key=lambda x: x[0])
        for i, slide in enumerate(neworder):
            if slide[0] != i:
                slide[1].slideshow.index = i
                changed = True
        if changed:
            update_scene(current_scene)
    else:
        slides.sort(key=lambda x: x.slideshow.index)

        unfrozen_indices, unfrozen_subset = zip(*[(i, e) for i, e in enumerate(slides) if not e.slideshow.lockposition])
        unfrozen_indices = list(unfrozen_indices)
        unfrozen_subset = list(unfrozen_subset)

        if mode == 'random':
            random.shuffle(unfrozen_indices)
        elif mode == 'alphabetical':
            unfrozen_subset.sort(key=lambda x: x.slideshow.name)
        elif mode == 'reverse':
            unfrozen_subset.sort(key=lambda x: x.slideshow.name)
            unfrozen_subset.reverse()

        for i, e in zip(unfrozen_indices, unfrozen_subset):
            slides[i] = e

        for i, slide in enumerate(slides):
            slide.slideshow.index = i


def get_first_3d_view():
    for area in bpy.context.screen.areas:
        if area.type == 'VIEW_3D':
            for space in area.spaces:
                if space.type == 'VIEW_3D':
                    return space
    return None


# PROPERTY GROUPS
class SnuSlideshowExtraTexturePreset(bpy.types.PropertyGroup):
    """A property group for a texture preset for the extra scenes"""
    name: bpy.props.StringProperty(
        name="Texture Name",
        default="None"
    )
    path: bpy.props.StringProperty(
        name="Texture Path",
        default="None"
    )


class SnuSlideshowImage(bpy.types.PropertyGroup):
    """A property group that contains the information needed for a slideshow image"""
    name: bpy.props.StringProperty(
        name="Image Name",
        default="None"
    )
    transform: bpy.props.StringProperty(
        name="Transform Type Name",
        default="None",
        update=update_transform
    )
    transform_interpolation: bpy.props.EnumProperty(
        name="Transform Interpolation",
        default="BEZIER",
        items=[
            ("BEZIER", "Bezier", "", 1), 
            ("LINEAR", "Linear", "", 2)
        ]
    )
    length: bpy.props.FloatProperty(
        name="Slide Length (Seconds)", 
        default=12.0, 
        min=1.0,
        update=update_slide_length,
        description="Slide Length In Seconds"
    )
    videooffset: bpy.props.IntProperty(
        name="Video Offset (Frames)",
        default=0,
        min=0,
        description="Video Offset In Frames",
        update=update_offset
    )
    videoaudio: bpy.props.BoolProperty(
        name="Enable Audio",
        default=True,
        description="Import Audio Track When Importing Video"
    )
    videomaxlength: bpy.props.IntProperty(
        name="Video Maximum Length",
        default=0
    )
    videolength: bpy.props.IntProperty(
        name="Slide Length (Frames)",
        default=1,
        min=0,
        update=update_video_length,
        description="Video Slide Length In Frames"
    )
    videofile: bpy.props.StringProperty(
        name="Video Filename",
        default=""
    )
    extra: bpy.props.StringProperty(
        name="Extra Type", 
        default="None",
        update=update_extra
    )
    imageplane: bpy.props.StringProperty(
        name="Image Plane Name", 
        default="None"
    )
    target: bpy.props.StringProperty(
        name="Target Empty Name", 
        default="None"
    )
    view: bpy.props.StringProperty(
        name="View Window Empty Name", 
        default="None"
    )
    extraamount: bpy.props.FloatProperty(
        name="Amount For The Extra Scene",
        default=0.5,
        max=1.0,
        min=0.0,
        description="Determines the power of the effect for the extra scene - 0.5 is average"
    )
    extratext: bpy.props.StringProperty(
        name="Text For The Extra Scene",
        default="None",
        description="Used for extra scenes with a text object"
    )
    extratexture: bpy.props.StringProperty(
        name="Texture For The Extra Scene",
        default="None",
        description="Used for extra scenes with a video background or overlay"
    )
    index: bpy.props.IntProperty(
        name="Image Index",
        default=0,
        update=update_index
    )
    lockposition: bpy.props.BoolProperty(
        name="Lock Position",
        default=False
    )
    locktransform: bpy.props.BoolProperty(
        name="Lock Transform",
        default=False
    )
    lockextra: bpy.props.BoolProperty(
        name="Lock Extra",
        default=False
    )
    locklength: bpy.props.BoolProperty(
        name="Lock Length",
        default=False
    )
    locktransition: bpy.props.BoolProperty(
        name="Lock Transition",
        default=False
    )
    rotate: bpy.props.EnumProperty(
        name="Rotation",
        items=[
            ('0', '0', '0'), 
            ('90', '90', '90'), 
            ('180', '180', '180'), 
            ('-90', '-90', '-90')
        ],
        update=update_rotate
    )
    videobackground: bpy.props.BoolProperty(
        name="Blurred Background",
        default=True,
        description="When the video is smaller than the render resolution, add a blurred scaled background instead of black"
    )
    transition: bpy.props.EnumProperty(
        name="Transition Type",
        default="CROSS",
        items=[
            ("CROSS", "Crossfade", "", 1), 
            ("GAMMA_CROSS", "Gamma Cross", "", 2), 
            ("WIPE", "Wipe", "", 3), 
            ("CUSTOM", "Custom", "", 4), 
            ("NONE", "None", "", 5)
        ]
    )
    wipe_type: bpy.props.EnumProperty(
        name="Wipe Type",
        default="SINGLE",
        items=[
            ("SINGLE", "Single", "", 1), 
            ("DOUBLE", "Double", "", 2), 
            ("IRIS", "Iris", "", 3), 
            ("CLOCK", "Clock", "", 4)
        ]
    )
    wipe_direction: bpy.props.EnumProperty(
        name="Wipe Direction",
        default="OUT",
        items=[
            ("OUT", "Out", "", 1), 
            ("IN", "In", "", 2)
        ]
    )
    wipe_soft: bpy.props.BoolProperty(
        name="Soft Wipe",
        default=True
    )
    wipe_angle: bpy.props.EnumProperty(
        name="Wipe Angle",
        default="DOWN",
        items=[
            ("DOWN", "Down", "", 1), 
            ("RIGHT", "Right", "", 2), 
            ("UP", "Up", "", 3), 
            ("LEFT", "Left", "", 4)
        ]
    )
    custom_transition_file: bpy.props.StringProperty(
        name="Transition File",
        default="",
        description="Location of custom transition file.",
        subtype='FILE_PATH'
    )
    
    text_photographer: bpy.props.StringProperty(
        name="Photographer",
        default="",
        description="Photographer credit for this slide"
    )
    text_when: bpy.props.StringProperty(
        name="When",
        default="",
        description="When this photo was taken"
    )
    text_who: bpy.props.StringProperty(
        name="Who",
        default="",
        description="Who is in this photo"
    )
    text_where: bpy.props.StringProperty(
        name="Where",
        default="",
        description="Where this photo was taken"
    )
    has_text_file: bpy.props.BoolProperty(
        name="Has Text File",
        default=False,
        description="Whether a corresponding text file was found for this slide"
    )
    enable_text_overlay: bpy.props.BoolProperty(
        name="Enable Text Overlay",
        default=False,
        description="Enable text overlay for this individual slide"
    )


class SnuSlideshowGeneratorSettings(bpy.types.PropertyGroup):
    """Main settings for the slideshow generator"""
    is_generator_scene: bpy.props.BoolProperty(
        default=False
    )
    text_alignment: EnumProperty(
        name="Text Alignment",
        description="Horizontal alignment for overlay text",
        items=[
            ('LEFT', "Left", "Left aligned text"),
            ('CENTER', "Center", "Centered text"),
            ('RIGHT', "Right", "Right aligned text"),
        ],
        default='LEFT'
    )
    text_size: bpy.props.FloatProperty(
        name="Text Size",
        description="Size of the overlay text",
        default=0.10,
        min=0.01,
        max=1.0
    )
    text_y_offset: bpy.props.FloatProperty(
        name="Text Y Offset",
        description="Initial vertical position of the overlay text block",
        default=0.5,
        min=-2.0,
        max=2.0
    )
    hidden_transforms: bpy.props.StringProperty(
        name="Hidden Transforms",
        default="",
        description="List of transforms to not use in randomize operations"
    )
    hidden_extras: bpy.props.StringProperty(
        name="Hidden Extras",
        default="Text Normal Bottom;Text Normal Top;Video Background;Video Background With Shadows;Video Foreground;Compositor Glare;Overlay Curves Left;Overlay Curves Right",
        description="List of extras to not use in randomize operations"
    )
    image_directory: bpy.props.StringProperty(
        name="Image Directory",
        default='/Images/',
        description="Location of images used in slideshow",
        subtype='DIR_PATH'
    )
    slide_length: bpy.props.FloatProperty(
        name="Slide Length (Seconds)",
        default=12.0,
        min=1.0,
        max=20.0,
        description="Slide Scene Length In Seconds"
    )
    crossfade_length: bpy.props.IntProperty(
        name="Crossfade Length (Frames)",
        default=10,
        min=0,
        max=120
    )
    extra_texture: bpy.props.StringProperty(
        name="Extra Texture",
        default="None"
    )
    extra_texture_presets: bpy.props.CollectionProperty(
        type=SnuSlideshowExtraTexturePreset
    )
    audio_enabled: bpy.props.BoolProperty(
        default=False
    )
    audio_track: bpy.props.StringProperty(
        name="Audio Track",
        default="None"
    )
    audio_fade_length: bpy.props.IntProperty(
        name="Fade Out",
        description="Length of audio fade out in frames",
        default=30,
        min=0,
        max=600
    )
    audio_loop_fade: bpy.props.IntProperty(
        name="Loop Overlap",
        description="Length of audio overlap when track is looped in frames",
        default=60,
        min=0,
        max=600
    )
    base_name: bpy.props.StringProperty(
        name="Base Name For Created Scenes",
        default=''
    )
    generator_name: bpy.props.StringProperty(
        name="Generator Scene Name",
        default=''
    )
    generator_workspace: bpy.props.StringProperty(
        name="Generator Scene Workspace",
        default=''
    )
    aspect_ratio: bpy.props.FloatProperty(
        default=0.0
    )
    render_samples: bpy.props.IntProperty(
        min=0,
        default=24,
        max=128
    )


# PANELS
class SSG_PT_VSEPanel(bpy.types.Panel):
    """Panel visible in the VSE of the 'Slideshow' scene"""
    bl_label = "Snu Slideshow Generator"
    bl_space_type = 'SEQUENCE_EDITOR'
    bl_region_type = 'UI'
    bl_category = "Strip"

    @classmethod
    def poll(cls, context):
        if context.scene.snu_slideshow_generator.is_generator_scene:
            try:
                if len(context.scene.sequence_editor.sequences_all) > 0:
                    return True
                else:
                    return False
            except:
                return False
        else:
            return False

    def draw(self, context):
        layout = self.layout
        layout.operator('slideshow.preview_mode', text="Apply 50% Render Size").mode = 'halfsize'
        layout.operator('slideshow.preview_mode', text="Apply 100% Render Size").mode = 'fullsize'
        layout.operator('slideshow.gotogenerator', text="Return To The Generator")


class SSG_PT_Panel(bpy.types.Panel):
    """Main configuration panel for the slideshow generator"""
    bl_label = "Snu Slideshow Generator"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Slideshow"

    def draw(self, context):
        layout = self.layout
        current_scene = context.scene
        fps = get_fps(current_scene)
        
        if is_generator_scene(current_scene):
            slides = list_slides(current_scene)
            row = layout.row()
            if len(slides):
                layout.operator_context = 'INVOKE_SCREEN'
                row.operator('slideshow.create')

                row = layout.row()
                slideshow_seconds = slideshow_length(slides=slides, fps=fps)
                slideshow_length_formatted = format_seconds(slideshow_seconds)
                row.label(text=str(len(slides)) + " Slides, Total Length: "+slideshow_length_formatted)
            else:
                row.label(text="No Slides Found")

            row = layout.row()
            row.prop(context.scene.snu_slideshow_generator, "crossfade_length")
            row = layout.row()
            row.prop(context.scene.snu_slideshow_generator, "render_samples")
            
            row = layout.row()
            box = row.box()
            row = box.row()
            row.prop(context.scene.snu_slideshow_generator, "audio_enabled", text="Enable Audio Track")
            row = box.row()
            split = row.split(factor=.9, align=True)
            split.prop(context.scene.snu_slideshow_generator, "audio_track", text="Audio Track")
            split.operator('slideshow.open_audio', text="", icon='FILEBROWSER')
            if not context.scene.snu_slideshow_generator.audio_enabled:
                row.enabled = False
            row = box.row()
            row.prop(context.scene.snu_slideshow_generator, "audio_loop_fade")
            row.prop(context.scene.snu_slideshow_generator, "audio_fade_length")
            if not context.scene.snu_slideshow_generator.audio_enabled:
                row.enabled = False
            
            row = layout.row()
            row.separator()
            
            box = layout.box()
            row = box.row()
            row.label(text="Text Overlay Settings:")
            row = box.row()
            row.prop(context.scene.snu_slideshow_generator, "text_alignment")
            row = box.row()
            row.prop(context.scene.snu_slideshow_generator, "text_size")
            row.prop(context.scene.snu_slideshow_generator, "text_y_offset")

            if len(slides):
                row = layout.row(align=True)
                row.label(text='Sort:')
                row.operator('slideshow.update_order', text='Randomize').mode = 'random'
                row.operator('slideshow.update_order', text='Alphabetical').mode = 'alphabetical'
                row.operator('slideshow.update_order', text='Reverse Alpha').mode = 'reverse'
                row = layout.row(align=True)
                row.label(text='Randomize:')
                row.operator('slideshow.apply_transform', text='Transforms').transform = 'Random'
                row.operator('slideshow.apply_extra', text='Extras').extra = 'Random'

            row = layout.row(align=True)
            row.operator('slideshow.add_slide')

            if context.selected_objects:
                row.operator('slideshow.delete_slide')

        else:
            row = layout.row()
            row.prop(context.scene.snu_slideshow_generator, "image_directory")
            row = layout.row()
            row.prop(context.scene.snu_slideshow_generator, "slide_length")
            row = layout.row()
            row.operator('slideshow.generator', text='New Slideshow Scene').mode = 'new'
            row = layout.row()
            row.operator('slideshow.generator', text='Slideshow In This Scene').mode = 'direct'
            
            image_types = get_extensions_image()
            image_list = []
            for image_type in image_types:
                image_list.extend(glob.glob(bpy.path.abspath(context.scene.snu_slideshow_generator.image_directory)+'*'+image_type))
            video_types = get_extensions_video()
            for video_type in video_types:
                image_list.extend(glob.glob(bpy.path.abspath(context.scene.snu_slideshow_generator.image_directory)+'*'+video_type))
            if not image_list:
                row = layout.row()
                row.label(text="Image Directory Invalid Or Empty")
            else:
                row = layout.row()
                slideshow_seconds = slideshow_length(slides=image_list, fps=fps)
                slideshow_length_formatted = format_seconds(slideshow_seconds)
                row.label(text=str(len(image_list)) + " Images In Directory")
                row = layout.row()
                row.label(text="Estimated Length: "+slideshow_length_formatted)

            row = layout.row()
            row.separator()
            box = layout.box()
            row = box.row()
            row.menu('SSG_MT_transforms_menu', text="Toggle Transforms")
            row = box.row()
            row.menu('SSG_MT_extra_menu', text="Toggle Extras")
            row = layout.row()
            row.separator()
            box = layout.box()
            row = box.split(factor=0.8)
            split = row.split(factor=.9, align=True)
            split.prop(context.scene.snu_slideshow_generator, "extra_texture", text='Extra Texture')
            split.operator('slideshow.open_extra_texture', text="", icon='FILEBROWSER').target = 'scene'
            split = row.split(factor=1, align=True)
            split.operator('slideshow.add_extra_texture').texture = context.scene.snu_slideshow_generator.extra_texture
            row = box.row()
            row.menu('SSG_MT_extra_texture_menu', text="Extra Texture Presets")


class SSG_PT_SlidePanel(bpy.types.Panel):
    """Panel containing settings for the currently selected slideshow image"""
    bl_label = "Slideshow Image"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Slideshow"

    @classmethod
    def poll(cls, context):
        current_scene = context.scene
        if is_generator_scene(current_scene):
            if context.active_object:
                return True
        return False

    def draw(self, context):
        layout = self.layout

        selected = context.active_object
        if hasattr(selected, 'slideshow') and selected.slideshow.name != "None":
            current_slide = selected.slideshow
            row = layout.row()
            row.label(text="Image: "+current_slide.name)
            row = layout.row()
            row.prop(current_slide, 'rotate')
            row = layout.row()
            split = row.split(factor=.5)
            subsplit = split.split(align=True)
            subsplit.label(text=""+str(current_slide.index + 1))
            subsplit.operator("slideshow.move_slide", text="", icon="REW").move = "beginning"
            subsplit.operator("slideshow.move_slide", text="", icon="PLAY_REVERSE").move = "backward"
            subsplit.operator("slideshow.move_slide", text="", icon="PLAY").move = "forward"
            subsplit.operator("slideshow.move_slide", text="", icon="FF").move = "end"
            split = split.split()
            split.prop(current_slide, "lockposition")
            
            if current_slide.has_text_file:
                innerbox = layout.box()
                row = innerbox.row()
                row.label(text="Text Overlay (Auto-detected)", icon='FILE_TEXT')
                row = innerbox.row()
                row.prop(current_slide, "enable_text_overlay", text="Enable Text Overlay for This Slide")
                
                if current_slide.enable_text_overlay:
                    if current_slide.text_photographer:
                        row = innerbox.row()
                        row.label(text=f"Photographer: {current_slide.text_photographer}")
                    if current_slide.text_when:
                        row = innerbox.row()
                        row.label(text=f"When: {current_slide.text_when}")
                    if current_slide.text_who:
                        row = innerbox.row()
                        row.label(text=f"Who: {current_slide.text_who}")
                    if current_slide.text_where:
                        row = innerbox.row()
                        row.label(text=f"Where: {current_slide.text_where}")
                    
                    row = innerbox.row()
                    row.label(text="Edit Text Data:")
                    row = innerbox.row()
                    row.prop(current_slide, "text_photographer", text="Photographer")
                    row = innerbox.row()
                    row.prop(current_slide, "text_when", text="When")
                    row = innerbox.row()
                    row.prop(current_slide, "text_who", text="Who")
                    row = innerbox.row()
                    row.prop(current_slide, "text_where", text="Where")
            
            innerbox = layout.box()
            row = innerbox.row()
            if current_slide.videofile:
                row.prop(current_slide, "videolength")
            else:
                row.prop(current_slide, "length")
                row = innerbox.row()
                row.operator('slideshow.apply_slide_length', text="Apply To Selected").mode = 'Selected'
                row.operator('slideshow.apply_slide_length').mode = 'None'
                row.prop(current_slide, "locklength")

            if not current_slide.videofile:
                innerbox = layout.box()
                row = innerbox.row()
                row.label(text="Transform: "+current_slide.transform)
                row = innerbox.row()
                row.menu('SSG_MT_transforms_menu', text="Change Transform")
                row = innerbox.row()
                row.operator('slideshow.apply_transform', text="Apply To Selected").transform = 'Selected'
                row.operator('slideshow.apply_transform').transform = 'None'
                row.prop(current_slide, "locktransform")
                innerbox = layout.box()
                row = innerbox.row()
                row.label(text="Extra: "+current_slide.extra)
                row = innerbox.row()
                row.menu('SSG_MT_extra_menu', text="Change Extra")
                row = innerbox.row()
                row.operator('slideshow.apply_extra', text="Apply To Selected").extra = 'Selected'
                row.operator('slideshow.apply_extra').extra = 'None'
                row.prop(current_slide, "lockextra")
                row = innerbox.row()
                row.separator()
                row = innerbox.row()
                row.prop(current_slide, "extratext", text='Extra Text')
                row = innerbox.split(factor=0.8)
                split = row.split(factor=.9, align=True)
                split.prop(current_slide, "extratexture", text='Extra Texture')
                split.operator('slideshow.open_extra_texture', text="", icon='FILEBROWSER').target = 'slide'
                split = row.split(factor=1, align=True)
                split.operator('slideshow.add_extra_texture').texture = current_slide.extratexture
                row = innerbox.row()
                row.menu('SSG_MT_extra_texture_menu', text="Apply Extra Texture Preset")
                row = innerbox.row()
                row.prop(current_slide, "extraamount", text='Extra Amount')

            else:
                innerbox = layout.box()
                row = innerbox.row()
                row.prop(current_slide, "videooffset", text='Video Offset')
                row = innerbox.row()
                row.prop(current_slide, "videoaudio", text='Import Audio From Video File')
                row = innerbox.row()
                row.prop(current_slide, "videobackground", text='Add Blurred Background If Needed')
            innerbox = layout.box()
            row = innerbox.row()
            row.label(text="Transition To Next Slide:")
            row = innerbox.row()
            row.prop(current_slide, "transition", text="")
            row = innerbox.row()
            row.operator('slideshow.apply_transition', text="Apply To Selected").transition = 'Selected'
            row.operator('slideshow.apply_transition').transition = 'None'
            row.prop(current_slide, "locktransition")
            transition = current_slide.transition
            if transition == "WIPE":
                row = innerbox.row()
                row.prop(current_slide, "wipe_type", text='Type')
                row.prop(current_slide, 'wipe_soft', toggle=True)
                row = innerbox.row()
                row.prop(current_slide, "wipe_direction", expand=True)
                row = innerbox.row()
                row.prop(current_slide, 'wipe_angle', expand=True)
            if transition == "CUSTOM":
                row = innerbox.row()
                row.prop(current_slide, 'custom_transition_file', text='Transition Video')
            row = layout.row()
            row.separator()
            row = layout.box()
            row.label(text="Drag an image up or down to rearrange it in the timeline.")

        elif 'View' in selected.name:
            row = layout.box()
            row.label(text="The rectangle is the area the camera will see.")
            row.label(text="It can be scaled down to crop the image,")
            row.label(text="or rotated to rotate the camera,")
            row.label(text="or moved to focus on a specific area.")

        elif 'Target' in selected.name:
            row = layout.box()
            row.label(text="The cross is the target for transforms like zoom in.")
            row.label(text="It can be moved around the image.")

        else:
            row = layout.box()
            row.label(text="Select An Image To Customize It")


# OPERATORS
class SnuSlideshowGotoGenerator(bpy.types.Operator):
    """Return to the slideshow generator scene"""
    bl_idname = 'slideshow.gotogenerator'
    bl_label = "Return To The Generator Scene"

    def execute(self, context):
        workspace_name = context.scene.snu_slideshow_generator.generator_workspace
        if workspace_name in bpy.data.workspaces:
            workspace = bpy.data.workspaces[workspace_name]
            context.window.workspace = workspace
        return{'FINISHED'}


class SnuSlideshowPreviewMode(bpy.types.Operator):
    """Enable or disable 'preview' mode on all scene strips"""
    bl_idname = 'slideshow.preview_mode'
    bl_label = 'Enable or Disable Preview On All Scenes'

    mode: bpy.props.StringProperty()

    def execute(self, context):
        sequences = context.scene.sequence_editor.sequences_all
        for sequence in sequences:
            if sequence.type == 'SCENE':
                scene = sequence.scene
                if self.mode == 'halfsize':
                    sequence.transform.scale_x = 2
                    sequence.transform.scale_y = 2
                    scene.render.resolution_percentage = 50
                elif self.mode == 'fullsize':
                    sequence.transform.scale_x = 1
                    sequence.transform.scale_y = 1
                    scene.render.resolution_percentage = 100
        return{'FINISHED'}


class SnuSlideshowMoveSlide(bpy.types.Operator):
    """Move the active slideshow slide up or down in the generator scene"""
    bl_idname = 'slideshow.move_slide'
    bl_label = "Move The Active Slide"

    move: bpy.props.StringProperty()

    def execute(self, context):
        selected = context.active_object
        slide = selected.slideshow
        slides = list_slides(context.scene)
        if self.move == "forward":
            selected.location[1] = selected.location[1] - 1.1
            update_order()
        elif self.move == "backward":
            selected.location[1] = selected.location[1] + 1.1
            update_order()
        elif self.move == "beginning":
            slide.index = -1
        elif self.move == "end":
            slide.index = len(slides) + 1
        return {'FINISHED'}


class SnuSlideshowOpenExtraTexture(bpy.types.Operator):
    """Open a filebrowser to select an extra texture file"""
    bl_idname = 'slideshow.open_extra_texture'
    bl_label = 'Browse For An Image Or Video File'

    filepath: bpy.props.StringProperty()
    target: bpy.props.StringProperty()

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def draw(self, context):
        context.space_data.params.use_filter = True
        context.space_data.params.use_filter_image = True
        context.space_data.params.use_filter_movie = True
        context.space_data.params.use_filter_folder = True

    def execute(self, context):
        if self.target == 'slide':
            current_slide = context.active_object
            current_slide.slideshow.extratexture = self.filepath
        else:
            context.scene.snu_slideshow_generator.extra_texture = self.filepath
        return{'FINISHED'}


class SnuSlideshowOpenAudio(bpy.types.Operator):
    """Open a filebrowser to select an audio file"""
    bl_idname = 'slideshow.open_audio'
    bl_label = 'Browse For An Audio File'

    filepath: bpy.props.StringProperty()

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def draw(self, context):
        context.space_data.params.use_filter = True
        context.space_data.params.use_filter_sound = True
        context.space_data.params.use_filter_folder = True

    def execute(self, context):
        generator_scene = context.scene
        generator_scene.snu_slideshow_generator.audio_track = self.filepath
        return{'FINISHED'}


class SnuSlideshowAddSlide(bpy.types.Operator):
    """Add new slide(s) to the slideshow generator scene"""
    bl_idname = 'slideshow.add_slide'
    bl_label = 'Add New Slide(s)'

    files: bpy.props.CollectionProperty(
        name="File Path",
        type=bpy.types.OperatorFileListElement
    )
    directory: bpy.props.StringProperty(
        subtype="DIR_PATH"
    )

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def draw(self, context):
        context.space_data.params.use_filter = True
        context.space_data.params.use_filter_image = True
        context.space_data.params.use_filter_movie = True
        context.space_data.params.use_filter_folder = True

    def execute(self, context):
        generator_scene = context.scene
        import os

        last_image = None
        for fileelement in self.files:
            filename = os.path.join(self.directory, fileelement.name)
            if os.path.isfile(filename):
                extension = os.path.splitext(filename)[1].lower()
                if extension in get_extensions_image():
                    image = load_image(filename)
                    image_number = len(list_slides(generator_scene))
                    last_image = import_slideshow_image(image, image_number, generator_scene.snu_slideshow_generator.slide_length, generator_scene, video=False, last_image=last_image)
                elif extension in get_extensions_video():
                    image = load_image(filename)
                    image_number = len(list_slides(generator_scene))
                    last_image = import_slideshow_image(image, image_number, generator_scene.snu_slideshow_generator.slide_length, generator_scene, video=True, last_image=last_image)
                else:
                    self.report({'WARNING'}, os.path.split(filename)[1]+' Is Not An Image')
        select_plane(last_image, generator_scene)
        return{'FINISHED'}


class SnuSlideshowExtraMenu(bpy.types.Menu):
    """Popup menu for selecting or toggling extras"""
    bl_idname = 'SSG_MT_extra_menu'
    bl_label = 'List of available extras'

    def draw(self, context):
        scene = context.scene
        layout = self.layout
        split = layout.split()
        column = split.column()

        is_generator = is_generator_scene(scene)
        if is_generator:
            column.operator("slideshow.change_extra", text="None").extra = "None"
        else:
            column.operator("slideshow.hide_extra", text="None").extra = "None"
        extras = list_extras()

        for extra in extras:
            if extra != 'None':
                if is_generator:
                    column.operator("slideshow.change_extra", text=extra).extra = extra
                else:
                    column.operator("slideshow.hide_extra", text=extra).extra = extra
        column = split.column()

        hidden = scene.snu_slideshow_generator.hidden_extras.split(";")

        if "None" in hidden:
            column.operator("slideshow.hide_extra", text="", icon="CHECKBOX_DEHLT").extra = "None"
        else:
            column.operator("slideshow.hide_extra", text="", icon="CHECKBOX_HLT").extra = "None"

        for extra in extras:
            if extra != 'None':
                if extra in hidden:
                    column.operator("slideshow.hide_extra", text="", icon="CHECKBOX_DEHLT").extra = extra
                else:
                    column.operator("slideshow.hide_extra", text="", icon="CHECKBOX_HLT").extra = extra

        column.operator("slideshow.hide_all_extras", text="Toggle All")


class SnuSlideshowHideAllExtras(bpy.types.Operator):
    """Toggle all extras on and off"""
    bl_idname = 'slideshow.hide_all_extras'
    bl_label = 'Toggle Hide All Extras From Randomize Operations'
    bl_description = 'Toggle Hide All Extras From Randomize Operations'

    def execute(self, context):
        scene = context.scene
        if len(scene.snu_slideshow_generator.hidden_extras) == 0:
            hidden = list_extras()
            scene.snu_slideshow_generator.hidden_extras = ';'.join(hidden)
        else:
            scene.snu_slideshow_generator.hidden_extras = ""
        return{'FINISHED'}


class SnuSlideshowHideExtra(bpy.types.Operator):
    """Toggle an extra in the hidden list"""
    bl_idname = 'slideshow.hide_extra'
    bl_label = 'Hide Extra From Randomize Operations'
    bl_description = 'Hide Extra From Randomize Operations'

    extra: bpy.props.StringProperty()

    def execute(self, context):
        scene = context.scene
        hidden = scene.snu_slideshow_generator.hidden_extras.split(';')
        if self.extra in hidden:
            hidden.remove(self.extra)
        else:
            hidden.append(self.extra)
        scene.snu_slideshow_generator.hidden_extras = ';'.join(hidden)
        return{'FINISHED'}


class SnuSlideshowChangeExtra(bpy.types.Operator):
    """Change the extra in the currently selected object"""
    bl_idname = 'slideshow.change_extra'
    bl_label = 'Change Extra'

    extra: bpy.props.StringProperty()

    def execute(self, context):
        current_image = context.active_object
        current_image.slideshow.extra = self.extra
        return{'FINISHED'}


class SnuSlideshowTransformsMenu(bpy.types.Menu):
    """Menu of transforms with enable/disable options"""
    bl_idname = 'SSG_MT_transforms_menu'
    bl_label = 'List of available transforms'

    def draw(self, context):
        scene = context.scene
        layout = self.layout
        split = layout.split()
        column = split.column()

        is_generator = is_generator_scene(scene)
        for index, transform in enumerate(transforms):
            if is_generator:
                column.operator("slideshow.change_transform", text=transform['name']).transform = transform['name']
            else:
                column.operator("slideshow.hide_transform", text=transform['name']).transform = transform['name']

        column = split.column()
        hidden = scene.snu_slideshow_generator.hidden_transforms.split(';')

        for index, transform in enumerate(transforms):
            if transform['name'] in hidden:
                column.operator("slideshow.hide_transform", text="", icon="CHECKBOX_DEHLT").transform = transform['name']
            else:
                column.operator("slideshow.hide_transform", text="", icon="CHECKBOX_HLT").transform = transform['name']
        column.operator("slideshow.hide_all_transforms", text="Toggle All")


class SnuSlideshowHideAllTransforms(bpy.types.Operator):
    """Toggle all transforms on and off"""
    bl_idname = 'slideshow.hide_all_transforms'
    bl_label = 'Toggle Hide All Transforms From Randomize Operations'
    bl_description = 'Toggle Hide All Transforms From Randomize Operations'

    def execute(self, context):
        scene = context.scene
        if len(scene.snu_slideshow_generator.hidden_transforms) == 0:
            hidden = []
            for transform in transforms:
                hidden.append(transform['name'])
            scene.snu_slideshow_generator.hidden_transforms = ';'.join(hidden)
        else:
            scene.snu_slideshow_generator.hidden_transforms = ""
        return{'FINISHED'}


class SnuSlideshowHideTransform(bpy.types.Operator):
    """Toggle a transform in the hidden list"""
    bl_idname = 'slideshow.hide_transform'
    bl_label = 'Hide Transform From Randomize Operations'
    bl_description = 'Hide Transform From Randomize Operations'

    transform: bpy.props.StringProperty()

    def execute(self, context):
        scene = context.scene
        hidden = scene.snu_slideshow_generator.hidden_transforms.split(';')
        if self.transform in hidden:
            hidden.remove(self.transform)
        else:
            hidden.append(self.transform)
        scene.snu_slideshow_generator.hidden_transforms = ';'.join(hidden)
        return{'FINISHED'}


class SnuSlideshowChangeTransform(bpy.types.Operator):
    """Change the transform in the currently selected object"""
    bl_idname = 'slideshow.change_transform'
    bl_label = 'Change Transform'

    transform: bpy.props.StringProperty()

    def execute(self, context):
        current_image = context.active_object
        current_image.slideshow.transform = self.transform
        return{'FINISHED'}


class SnuSlideshowApplyExtra(bpy.types.Operator):
    """Apply an extra or randomize extras on all slides"""
    bl_idname = 'slideshow.apply_extra'
    bl_label = 'Apply To All'
    bl_description = 'Applies an extra to all slides'

    extra: bpy.props.StringProperty()

    def execute(self, context):
        update_order()
        current_scene = context.scene
        slides = list_slides(current_scene)
        slides.sort(key=lambda x: x.slideshow.index)
        extras = list_extras()
        hidden = context.scene.snu_slideshow_generator.hidden_extras.split(";")
        randomized = []
        current_slide = context.active_object

        if self.extra == 'Selected':
            objects = current_scene.objects
            for scene_object in objects:
                if scene_object.select_get():
                    if scene_object.slideshow.name != "None":
                        if not scene_object.slideshow.lockextra:
                            scene_object.slideshow.extra = current_slide.slideshow.extra
                            scene_object.slideshow.extraamount = current_slide.slideshow.extraamount
                            scene_object.slideshow.extratexture = current_slide.slideshow.extratexture
                            scene_object.slideshow.extratext = current_slide.slideshow.extratext

        else:
            for extra in extras:
                if extra not in hidden and extra != "None":
                    randomized.append(extra)
            if "None" not in hidden:
                randomized.append("None")
            lastextra = ""
            lastextratexture = ""

            extratextures = []
            for extra_texture_preset in current_scene.snu_slideshow_generator.extra_texture_presets:
                extratextures.append(extra_texture_preset.path)

            for slide in slides:
                if not slide.slideshow.lockextra:
                    if self.extra == 'Random':
                        if len(randomized) > 0:
                            lessrandomized = [x for x in extratextures if x != lastextratexture]
                            if len(lessrandomized) > 0:
                                newextratexture = lessrandomized[random.randint(0, (len(lessrandomized)-1))]
                                slide.slideshow.extratexture = newextratexture

                            if len(randomized) > 1:
                                lessrandomized = [x for x in randomized if x != lastextra]
                                newextra = lessrandomized[random.randint(0, (len(lessrandomized)-1))]
                                slide.slideshow.extra = newextra
                                slide.slideshow.extraamount = 0.5
                                lastextra = newextra
                            else:
                                slide.slideshow.extra = randomized[0]
                                slide.slideshow.extraamount = 0.5
                    else:
                        slide.slideshow.extra = current_slide.slideshow.extra
                        slide.slideshow.extraamount = current_slide.slideshow.extraamount
                        slide.slideshow.extratexture = current_slide.slideshow.extratexture
                        slide.slideshow.extratext = current_slide.slideshow.extratext

        return{'FINISHED'}


class SnuSlideshowApplyTransform(bpy.types.Operator):
    """Apply a transform or randomize transforms on all slides"""
    bl_idname = 'slideshow.apply_transform'
    bl_label = 'Apply To All'
    bl_description = 'Applies a transform to all slides'

    transform: bpy.props.StringProperty()

    def execute(self, context):
        update_order()
        current_scene = context.scene
        current_slide = context.active_object
        slides = list_slides(current_scene)
        slides.sort(key=lambda x: x.slideshow.index)
        hidden = context.scene.snu_slideshow_generator.hidden_transforms.split(";")
        randomized = []

        if self.transform == 'Selected':
            objects = current_scene.objects
            for scene_object in objects:
                if scene_object.select_get():
                    if scene_object.slideshow.name != "None":
                        if not scene_object.slideshow.locktransform:
                            scene_object.slideshow.transform = current_slide.slideshow.transform

        else:
            for transform in transforms:
                if transform['name'] not in hidden:
                    randomized.append(transform)
            lasttransform = {"name": ""}

            for slide in slides:
                if not slide.slideshow.locktransform:
                    if self.transform == 'Random':
                        if len(randomized) > 0:
                            if len(randomized) > 1:
                                lessrandomized = [x for x in randomized if x['name'] != lasttransform['name']]
                                newtransform = lessrandomized[random.randint(0, (len(lessrandomized)-1))]
                                slide.slideshow.transform = newtransform['name']
                                lasttransform = newtransform
                            else:
                                slide.slideshow.transform = randomized[0]['name']
                    else:
                        slide.slideshow.transform = current_slide.slideshow.transform

        return{'FINISHED'}


class SnuSlideshowApplyTransition(bpy.types.Operator):
    """Apply a transition to all slides"""
    bl_idname = 'slideshow.apply_transition'
    bl_label = 'Apply To All'
    bl_description = 'Applies a transition to all slides'

    transition: bpy.props.StringProperty()

    def apply_transition(self, selected, target):
        target.transition = selected.transition
        target.wipe_type = selected.wipe_type
        target.wipe_direction = selected.wipe_direction
        target.wipe_soft = selected.wipe_soft
        target.wipe_angle = selected.wipe_angle
        target.custom_transition_file = selected.custom_transition_file

    def execute(self, context):
        update_order()
        current_scene = context.scene
        current_slide = context.active_object
        slides = list_slides(current_scene)
        slides.sort(key=lambda x: x.slideshow.index)

        for slide in slides:
            if not slide.slideshow.locktransition:
                if (self.transition == 'Selected' and slide.select_get()) or self.transition != 'Selected':
                    self.apply_transition(current_slide.slideshow, slide.slideshow)

        return{'FINISHED'}


class SnuSlideshowApplySlideLength(bpy.types.Operator):
    """Apply a slide length to all slides"""
    bl_idname = 'slideshow.apply_slide_length'
    bl_label = 'Apply To All'
    bl_description = 'Applies current slide length to all slides'

    mode: bpy.props.StringProperty()

    def execute(self, context):
        current_scene = context.scene
        current_slide = context.active_object
        if self.mode == 'Selected':
            objects = current_scene.objects
            for scene_object in objects:
                if scene_object.select_get():
                    if scene_object.slideshow.name != "None":
                        if not scene_object.slideshow.locklength:
                            scene_object.slideshow.length = current_slide.slideshow.length
        else:
            slides = list_slides(current_scene)
            for slide in slides:
                if not slide.slideshow.locklength:
                    slide.slideshow.length = current_slide.slideshow.length
        return{'FINISHED'}


class SnuSlideshowUpdateOrder(bpy.types.Operator):
    """Update slide order"""
    bl_idname = 'slideshow.update_order'
    bl_label = 'Update Slide Order'

    mode: bpy.props.StringProperty()

    def execute(self, context):
        update_order(self.mode)
        return{'FINISHED'}


class SnuSlideshowDeleteSlide(bpy.types.Operator):
    """Remove all selected slides from the generator scene"""
    bl_idname = 'slideshow.delete_slide'
    bl_label = 'Delete Selected Slide(s)'
    bl_description = 'Deletes selected slides and rearranges the list'

    def execute(self, context):
        selected_objects = context.selected_objects

        selected_slides = []
        for selected in selected_objects:
            if len(selected_objects) == 1 and selected.slideshow.name == "None" and selected.parent:
                selected = selected.parent

            if selected.slideshow.name != "None":
                selected_slides.append(selected)
        bpy.ops.object.select_all(action='DESELECT')
        for selected in selected_slides:
            context.view_layer.objects.active = selected
            selected.select_set(True)
            bpy.ops.object.select_grouped(extend=True, type='CHILDREN_RECURSIVE')
        bpy.ops.object.delete()
        update_order()
        return{'FINISHED'}


class SnuSlideshowAddExtraTexture(bpy.types.Operator):
    """Add a texture preset to the extra textures"""
    bl_idname = 'slideshow.add_extra_texture'
    bl_label = '+'
    bl_description = 'Adds a texture preset to the extra textures'

    texture: bpy.props.StringProperty()

    def execute(self, context):
        texturename = os.path.split(self.texture)[1]
        if texturename != 'None':
            if context.scene.snu_slideshow_generator.extra_texture_presets.find(texturename) == -1:
                newtexture = context.scene.snu_slideshow_generator.extra_texture_presets.add()
                newtexture.name = texturename
                newtexture.path = self.texture
                self.report({'INFO'}, "Added Preset: "+texturename)
            else:
                self.report({'INFO'}, "Preset Already Exists: "+texturename)
        return{'FINISHED'}


class SnuSlideshowRemoveExtraTexture(bpy.types.Operator):
    """Remove a texture preset from the list"""
    bl_idname = 'slideshow.remove_extra_texture'
    bl_label = '-'
    bl_description = 'Removes a texture preset from the extra textures'

    texture: bpy.props.StringProperty()

    def execute(self, context):
        remove = os.path.split(self.texture)[1]
        index = context.scene.snu_slideshow_generator.extra_texture_presets.find(remove)
        if index >= 0:
            context.scene.snu_slideshow_generator.extra_texture_presets.remove(index)
            self.report({'INFO'}, "Removed Preset: "+remove)
        else:
            self.report({'INFO'}, "Could Not Find Preset: "+remove)
        return{'FINISHED'}


class SnuSlideshowExtraTextureMenu(bpy.types.Menu):
    """Menu to list extra texture presets"""
    bl_idname = 'SSG_MT_extra_texture_menu'
    bl_label = 'List of saved extra textures'

    def draw(self, context):
        layout = self.layout
        split = layout.split()
        column = split.column()
        for texture in context.scene.snu_slideshow_generator.extra_texture_presets:
            column.operator("slideshow.change_extra_texture", text=texture.name).texture = texture.path
        column.separator()
        column.operator("slideshow.change_extra_texture", text="None").texture = "None"
        column = split.column()
        for texture in context.scene.snu_slideshow_generator.extra_texture_presets:
            column.operator('slideshow.remove_extra_texture', text='X').texture = texture.path


class SnuSlideshowChangeExtraTexture(bpy.types.Operator):
    """Set the extra texture for the currently active slide"""
    bl_idname = 'slideshow.change_extra_texture'
    bl_label = 'Change Extra Texture'

    texture: bpy.props.StringProperty()

    def execute(self, context):
        current_scene = context.scene
        if is_generator_scene(current_scene):
            current_image = context.active_object
            current_image.slideshow.extratexture = self.texture
        else:
            current_scene.snu_slideshow_generator.extra_texture = self.texture
        return{'FINISHED'}


class SnuSlideshowCreate(bpy.types.Operator):
    """Create a slideshow scene and all the image scenes from the generator scene"""
    bl_idname = 'slideshow.create'
    bl_label = 'Create Slideshow'
    bl_description = 'Turns the Slideshow Generator scene into a full slideshow'

    def execute(self, context):
        generator_scene = context.scene
        generator_scene.snu_slideshow_generator.generator_workspace = context.workspace.name

        clear_sequencer(generator_scene)
        image_scene_start = 1

        active = context.active_object
        selected = []
        for scene_object in context.scene.objects:
            if scene_object.select_get():
                selected.append(scene_object)

        images = list_slides(generator_scene)
        images.sort(key=lambda x: x.slideshow.index)
        previous_image_clip = None
        previous_image_plane = None
        for i, image_plane in enumerate(images):
            previous_image_clip = create_slideshow_slide(image_plane, i, generator_scene, image_scene_start, images, previous_image_clip, previous_image_plane)
            previous_image_plane = image_plane
            image_scene_start = previous_image_clip.frame_final_end - generator_scene.snu_slideshow_generator.crossfade_length
            
            if image_plane.slideshow.enable_text_overlay and image_plane.slideshow.has_text_file:
                text_scene = create_slide_text_overlay_scene_with_improved_outline(generator_scene, image_plane, image_plane.slideshow.length)
                if text_scene:
                    text_clip = generator_scene.sequence_editor.sequences.new_scene(
                        scene=text_scene, 
                        name=f"{text_scene.name}_Text", 
                        channel=5, 
                        frame_start=previous_image_clip.frame_final_start
                    )
                    text_clip.frame_final_end = previous_image_clip.frame_final_end
                    text_clip.blend_type = 'ALPHA_OVER'

        self.report({'INFO'}, "Slideshow created")

        generator_scene.frame_end = image_scene_start + generator_scene.snu_slideshow_generator.crossfade_length
        generator_scene.sync_mode = 'AUDIO_SYNC'

        if generator_scene.snu_slideshow_generator.audio_enabled:
            filename = os.path.realpath(bpy.path.abspath(generator_scene.snu_slideshow_generator.audio_track))
            if os.path.exists(filename):
                extension = os.path.splitext(generator_scene.snu_slideshow_generator.audio_track)[1].lower()
                if extension in bpy.path.extensions_audio:
                    audio_frame_end = 0
                    i = 0
                    audio_sequence = None
                    while audio_frame_end < generator_scene.frame_end:
                        if audio_frame_end == 0:
                            frame_start = 1
                        else:
                            frame_start = audio_frame_end+1-generator_scene.snu_slideshow_generator.audio_loop_fade

                        audio_sequence = generator_scene.sequence_editor.sequences.new_sound(name='Audio', filepath=filename, channel=6+(i % 2), frame_start=frame_start)

                        if audio_sequence.frame_duration > 0:
                            audio_frame_end = audio_sequence.frame_final_end
                        else:
                            audio_frame_end = generator_scene.frame_end
                        i += 1

                    if audio_sequence:
                        audio_sequence.frame_final_end = generator_scene.frame_end
                        generator_scene.frame_current = generator_scene.frame_end - generator_scene.snu_slideshow_generator.audio_fade_length
                        audio_sequence.keyframe_insert(data_path='volume')
                        generator_scene.frame_current = generator_scene.frame_end
                        audio_sequence.volume = 0
                        audio_sequence.keyframe_insert(data_path='volume')

        try:
            context.window.workspace = bpy.data.workspaces['Video Editing']
        except KeyError:
            pass

        generator_scene.render.sequencer_gl_preview = 'MATERIAL'
        try:
            generator_scene.render.use_sequencer_gl_preview = True
        except:
            pass

        for scene_object in context.scene.objects:
            if scene_object in selected:
                scene_object.select_set(True)
            else:
                scene_object.select_set(False)

        return{'FINISHED'}


class SnuSlideshowGenerator(bpy.types.Operator):
    """Import images and create the slideshow generator scene"""
    bl_idname = 'slideshow.generator'
    bl_label = 'Create Slideshow Generator'
    bl_description = 'Imports images and creates a scene for setting up the slideshow'

    mode: bpy.props.StringProperty()

    def execute(self, context):
        if self.mode != 'direct':
            generator_name = context.scene.name + ' Slideshow Generator'
            if bpy.data.scenes.find(generator_name) != -1:
                self.report({'WARNING'}, 'Slideshow Generator Scene Already Exists')
                return{'CANCELLED'}

        slide_length = context.scene.snu_slideshow_generator.slide_length
        image_directory = context.scene.snu_slideshow_generator.image_directory
        image_types = get_extensions_image()
        video_types = get_extensions_video()

        image_list = []
        video_list = []
        for image_type in image_types:
            image_list.extend(glob.glob(bpy.path.abspath(image_directory)+'*'+image_type))
        for video_type in video_types:
            video_list.extend(glob.glob(bpy.path.abspath(image_directory)+'*'+video_type))

        imports = []
        for image in image_list:
            imports.append([image, False])
        for video in video_list:
            imports.append([video, True])
        total_images = len(imports)
        imports.sort(key=lambda x: x[0])

        self.report({'INFO'}, 'Importing '+str(total_images)+' images')

        if self.mode == 'direct':
            generator_scene = context.scene
            generator_scene.snu_slideshow_generator.base_name = generator_scene.name
            generator_scene.snu_slideshow_generator.is_generator_scene = True
            generator_scene.snu_slideshow_generator.crossfade_length = 10
        else:
            oldscene = context.scene
            generator_scene = create_scene(oldscene, generator_name)
            generator_scene.snu_slideshow_generator.base_name = oldscene.name
            generator_scene.snu_slideshow_generator.is_generator_scene = True
            bpy.context.window.scene = generator_scene
            generator_scene.snu_slideshow_generator.crossfade_length = 10
            generator_scene.snu_slideshow_generator.slide_length = slide_length
            generator_scene.snu_slideshow_generator.hidden_transforms = oldscene.snu_slideshow_generator.hidden_transforms
            generator_scene.snu_slideshow_generator.hidden_extras = oldscene.snu_slideshow_generator.hidden_extras
            for extra_texture_preset in oldscene.snu_slideshow_generator.extra_texture_presets:
                new_preset = generator_scene.snu_slideshow_generator.extra_texture_presets.add()
                new_preset.name = extra_texture_preset.name
                new_preset.path = extra_texture_preset.path

        space = get_first_3d_view()
        if space:
            if space.shading.type not in ['MATERIAL', 'RENDERED']:
                space.shading.type = 'MATERIAL'
            space.region_3d.view_rotation = (1.0, 0, 0, 0)
            space.region_3d.view_perspective = 'ORTHO'
            space.overlay.show_floor = False
            space.overlay.show_cursor = False
            space.overlay.show_relationship_lines = False
            space.lock_cursor = True

        instructions = add_object(generator_scene, 'Instructions', 'FONT')
        instructions.location = (-1, 1.25, 0.0)
        instructions.scale = (.15, .15, .15)
        instructions.data.body = "Select an image and see the Scene tab in the properties area for details.\nDrag an image to rearrange it in the timeline.\nThe center cross on each image represents the focal point for transformations.\nThe box surrounding each image represents the viewable area for the camera.\nMove, scale, and rotate this to change the viewable area."

        image_number = 1
        last_image = None
        for import_data in imports:
            image_file, is_video = import_data
            image = load_image(image_file)
            last_image = import_slideshow_image(image, image_number, slide_length, generator_scene, video=is_video, last_image=last_image)
            image_number += 1

        select_plane(last_image, generator_scene)
        context.scene.cursor.location = (0, 0, 0)
        print("Now displaying images, this may take a while...")

        update_scene(generator_scene)
        update_order(current_scene=generator_scene)

        return{'FINISHED'}


# REGISTRATION
classes = [
    SnuSlideshowExtraTexturePreset, 
    SnuSlideshowImage, 
    SnuSlideshowGeneratorSettings,
    SSG_PT_VSEPanel, 
    SSG_PT_Panel, 
    SSG_PT_SlidePanel, 
    SnuSlideshowGotoGenerator,
    SnuSlideshowPreviewMode, 
    SnuSlideshowMoveSlide, 
    SnuSlideshowOpenExtraTexture,
    SnuSlideshowOpenAudio, 
    SnuSlideshowAddSlide, 
    SnuSlideshowExtraMenu, 
    SnuSlideshowHideAllExtras,
    SnuSlideshowHideExtra, 
    SnuSlideshowChangeExtra, 
    SnuSlideshowTransformsMenu, 
    SnuSlideshowHideAllTransforms,
    SnuSlideshowHideTransform, 
    SnuSlideshowChangeTransform, 
    SnuSlideshowApplyExtra, 
    SnuSlideshowApplyTransform,
    SnuSlideshowApplySlideLength, 
    SnuSlideshowApplyTransition, 
    SnuSlideshowUpdateOrder, 
    SnuSlideshowDeleteSlide,
    SnuSlideshowAddExtraTexture, 
    SnuSlideshowRemoveExtraTexture, 
    SnuSlideshowExtraTextureMenu,
    SnuSlideshowChangeExtraTexture, 
    SnuSlideshowCreate, 
    SnuSlideshowGenerator
]

def cleanup_typewriter_handlers():
    """Remove typewriter frame handlers"""
    if typewriter_frame_handler in bpy.app.handlers.frame_change_pre:
        bpy.app.handlers.frame_change_pre.remove(typewriter_frame_handler)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.Scene.snu_slideshow_generator = bpy.props.PointerProperty(type=SnuSlideshowGeneratorSettings)
    bpy.types.Object.slideshow = bpy.props.PointerProperty(type=SnuSlideshowImage)

    handlers = bpy.app.handlers.depsgraph_update_post
    for handler in handlers:
        if " slideshow_autoupdate " in str(handler):
            handlers.remove(handler)
    handlers.append(slideshow_autoupdate)

def unregister():
    cleanup_typewriter_handlers()
    handlers = bpy.app.handlers.depsgraph_update_post
    for handler in handlers:
        if " slideshow_autoupdate " in str(handler):
            handlers.remove(handler)
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()

# --- Replace create_text_material ---
def create_text_material(name="TextMaterial"):
    """Create (or copy-unique) a material for text objects. Always returns a unique material
       so fades/keyframes do not affect other text objects."""
    if name in bpy.data.materials:
        original = bpy.data.materials[name]
        material = original.copy()
        material.name = f"{name}_{bpy.app.handlers.frame_change_pre.__hash__() % 100000}_{len(bpy.data.materials)}"
    else:
        material = bpy.data.materials.new(name=name)

    material.use_nodes = True
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    nodes.clear()

    emission_node = nodes.new('ShaderNodeEmission')
    emission_node.name = "TextEmission"
    emission_node.inputs[0].default_value = (1.0, 1.0, 1.0, 1.0)
    emission_node.inputs[1].default_value = 2.0
    emission_node.location = (0, 0)

    output_node = nodes.new('ShaderNodeOutputMaterial')
    output_node.location = (200, 0)
    links.new(emission_node.outputs[0], output_node.inputs[0])

    return material

# --- Replace create_outline_material ---
def create_outline_material(name="TextOutlineMaterial"):
    """Create (or copy-unique) a material for text outline."""
    if name in bpy.data.materials:
        original = bpy.data.materials[name]
        material = original.copy()
        material.name = f"{name}_{bpy.app.handlers.frame_change_pre.__hash__() % 100000}_{len(bpy.data.materials)}"
    else:
        material = bpy.data.materials.new(name=name)

    material.use_nodes = True
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    nodes.clear()

    emission_node = nodes.new('ShaderNodeEmission')
    emission_node.name = "OutlineEmission"
    emission_node.inputs[0].default_value = (0.0, 0.0, 0.0, 1.0)
    emission_node.inputs[1].default_value = 1.5
    emission_node.location = (0, 0)

    output_node = nodes.new('ShaderNodeOutputMaterial')
    output_node.location = (200, 0)
    links.new(emission_node.outputs[0], output_node.inputs[0])

    return material

# --- Replace add_synchronized_fade ---

def add_synchronized_fade(materials, fps, total_frames, start_frame=1, fade_pct_start=0.75, fade_seconds=0.5):
    """Apply a synchronized fade-out to all given materials.
    - materials: iterable of bpy.types.Material
    - fps: frames-per-second for the scene
    - total_frames: integer total frames of the text scene / slide
    - start_frame: frame where the text animation starts (so fade is offset correctly)
    """
    if not materials or total_frames is None or fps is None:
        return

    fade_offset = int(total_frames * float(fade_pct_start))
    fade_length_frames = max(1, int(fps * float(fade_seconds)))
    fade_start = int(start_frame) + fade_offset
    fade_end = fade_start + fade_length_frames

    for mat in materials:
        if not mat or not getattr(mat, "node_tree", None):
            continue

        node = mat.node_tree.nodes.get("TextEmission") or mat.node_tree.nodes.get("OutlineEmission")
        if node is None:
            # nothing to animate
            continue

        strength_input = node.inputs[1]

        # Build the data_path used by node socket fcurves
        dpath = f'nodes[\"{node.name}\"].inputs[1].default_value'

        # Remove previous fcurves on both material.animation_data and material.node_tree.animation_data
        try:
            nta = getattr(mat, "node_tree", None)
            if nta and nta.animation_data and nta.animation_data.action:
                act = nta.animation_data.action
                for fc in list(act.fcurves):
                    if fc.data_path == dpath:
                        act.fcurves.remove(fc)
        except Exception:
            pass

        try:
            if mat.animation_data and mat.animation_data.action:
                act2 = mat.animation_data.action
                for fc in list(act2.fcurves):
                    if fc.data_path == dpath:
                        act2.fcurves.remove(fc)
        except Exception:
            pass

        # Insert keyframes on the node input (this will create/attach animation to material.node_tree)
        try:
            initial_strength = float(strength_input.default_value)
            strength_input.default_value = initial_strength
            strength_input.keyframe_insert(data_path="default_value", frame=max(1, fade_start - 1))
            strength_input.default_value = 0.0
            strength_input.keyframe_insert(data_path="default_value", frame=fade_end)
        except Exception:
            # fallback: try inserting keyframes on material sockets via node_tree path
            try:
                if mat.node_tree:
                    mat.node_tree.animation_data_create()
                    # not much else we can do here generically
            except Exception:
                pass

        # Ensure interpolation is linear for this node's fcurve(s)
        try:
            if mat.node_tree and mat.node_tree.animation_data and mat.node_tree.animation_data.action:
                act = mat.node_tree.animation_data.action
                for fc in act.fcurves:
                    if fc.data_path == dpath:
                        for kp in fc.keyframe_points:
                            kp.interpolation = 'LINEAR'
        except Exception:
            pass


def create_typewriter_text_with_improved_outline(scene, text_content, name, location=(0, 0, 0), size=1.0, alignment='LEFT', start_frame=1, total_frames=None):
    """Improved version with unique materials and synchronized fade."""
    safe_scene_name = getattr(scene, "name", "Scene").replace(" ", "_")
    outline_mat_name = f"{safe_scene_name}_{name}_OutlineMaterial"
    main_mat_name = f"{safe_scene_name}_{name}_MainMaterial"

    main_curve = bpy.data.curves.new(name=name, type='FONT')
    main_obj = bpy.data.objects.new(name=name, object_data=main_curve)
    scene.collection.objects.link(main_obj)

    outline_curve = bpy.data.curves.new(name=f"{name}_Outline", type='FONT')
    outline_obj = bpy.data.objects.new(name=f"{name}_Outline", object_data=outline_curve)
    scene.collection.objects.link(outline_obj)

    text_align = alignment
    for curve in (main_curve, outline_curve):
        curve.body = ""
        curve.size = size
        curve.extrude = 0.0
        curve.bevel_depth = 0.0
        curve.space_character = 1.15
        curve.space_word = 1.25
        curve.space_line = 1.15
        curve.align_x = text_align
        curve.align_y = 'CENTER'
        curve.resolution_u = 4
        curve.render_resolution_u = 4
        curve.use_fill_caps = True

    base_loc = Vector(location)
    main_obj.location = base_loc.copy()
    outline_obj.location = base_loc.copy()

    base_offset = size * 0.02
    if text_align == 'LEFT':
        offset_x = base_offset
    elif text_align == 'RIGHT':
        offset_x = -base_offset
    else:
        offset_x = 0.0
    offset_y = -abs(base_offset)

    outline_obj.location = main_obj.location + Vector((offset_x, offset_y, -0.001))
    outline_obj.rotation_euler = main_obj.rotation_euler
    outline_obj.scale = main_obj.scale

    outline_material = create_outline_material(outline_mat_name)
    main_material = create_text_material(main_mat_name)

    outline_obj.data.materials.clear()
    main_obj.data.materials.clear()
    outline_obj.data.materials.append(outline_material)
    main_obj.data.materials.append(main_material)

    try:
        outline_emission = outline_material.node_tree.nodes.get("OutlineEmission")
        main_emission = main_material.node_tree.nodes.get("TextEmission")
        if outline_emission and main_emission:
            outline_emission.inputs[0].default_value = (0.0, 0.0, 0.0, 1.0)
            outline_emission.inputs[1].default_value = 3.0
            main_emission.inputs[0].default_value = (1.0, 1.0, 1.0, 1.0)
            main_emission.inputs[1].default_value = 4.0
    except Exception:
        pass

    scene.view_layers.update()

    animation_duration = add_typewriter_animation_robust(main_obj, text_content, scene, start_frame)
    add_typewriter_animation_robust(outline_obj, text_content, scene, start_frame)

    if total_frames:
        fps = get_fps(scene)
        add_synchronized_fade([main_material, outline_material], fps, total_frames, start_frame=start_frame)

    return main_obj, outline_obj, main_material, outline_material, animation_duration