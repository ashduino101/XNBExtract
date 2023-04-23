import argparse
import gzip
import io
import json
import os.path
import struct
import sys

from PIL import Image

TARGET_PLATFORMS = {
    b'w': 'Microsoft Windows',
    b'm': 'Windows Phone 7',
    b'x': 'Xbox 360'
}
FMT_VERSIONS = {5: 'XNA Game Studio 4.0'}
SURFACE_FORMATS = [
    'Color',
    'Bgr565',
    'Bgra5551',
    'Bgra4444',
    'Dxt1',
    'Dxt3',
    'Dxt5',
    'NormalizedByte2',
    'NormalizedByte4',
    'Rgba1010102',
    'Rg32',
    'Rgba64',
    'Alpha8',
    'Single',
    'Vector2',
    'Vector4',
    'HalfSingle',
    'HalfVector2',
    'HalfVector4',
    'HdrBlendable'
]

indent = 0


def info(msg, *fmt_args, **fmt_kwargs):
    global indent
    print(f'[INFO] {" " * indent}{msg.format(*fmt_args, **fmt_kwargs)}')  # noqa - who cares


def warn(msg, *fmt_args, **fmt_kwargs):
    global indent
    print(f'\x1b[1m\x1b[1;33m[WARN] {" " * indent}{msg.format(*fmt_args, **fmt_kwargs)}\x1b[0m')  # noqa


def error(msg, *fmt_args, **fmt_kwargs):
    global indent
    print(f'\x1b[31m[ERROR] {" " * indent}{msg.format(*fmt_args, **fmt_kwargs)}\x1b[0m')  # noqa


class ObjectReader:
    def __init__(self, fp, object_type, save_base):
        self.fp = fp
        self.type = object_type
        self.save_base = save_base
        self.parsers = {
            # PRIMITIVE
            'Microsoft.Xna.Framework.Content.ByteReader': self.read_byte,
            'Microsoft.Xna.Framework.Content.SByteReader': self.read_sbyte,
            'Microsoft.Xna.Framework.Content.Int16Reader': self.read_int16,
            'Microsoft.Xna.Framework.Content.UInt16Reader': self.read_uint16,
            'Microsoft.Xna.Framework.Content.Int32Reader': self.read_int32,
            'Microsoft.Xna.Framework.Content.UInt32Reader': self.read_uint32,
            'Microsoft.Xna.Framework.Content.Int64Reader': self.read_int64,
            'Microsoft.Xna.Framework.Content.UInt64Reader': self.read_uint64,
            'Microsoft.Xna.Framework.Content.SingleReader': self.read_single,
            'Microsoft.Xna.Framework.Content.DoubleReader': self.read_double,
            'Microsoft.Xna.Framework.Content.BooleanReader': self.read_boolean,
            'Microsoft.Xna.Framework.Content.CharReader': self.read_char,
            'Microsoft.Xna.Framework.Content.StringReader': self.read_string,
            'Microsoft.Xna.Framework.Content.ObjectReader': self.read_object,

            # SYSTEM
            'Microsoft.Xna.Framework.Content.EnumReader': self.read_enum,
            'Microsoft.Xna.Framework.Content.NullableReader': self.read_nullable,
            'Microsoft.Xna.Framework.Content.ArrayReader': self.read_array,
            'Microsoft.Xna.Framework.Content.ListReader': self.read_list,
            'Microsoft.Xna.Framework.Content.DictionaryReader': self.read_dictionary,
            'Microsoft.Xna.Framework.Content.TimeSpanReader': self.read_timespan,
            'Microsoft.Xna.Framework.Content.DateTimeReader': self.read_datetime,
            'Microsoft.Xna.Framework.Content.DecimalReader': self.read_decimal,
            'Microsoft.Xna.Framework.Content.ExternalReferenceReader': self.read_external_reference,
            'Microsoft.Xna.Framework.Content.ReflectiveReader': self.read_reflective,

            # MATH
            'Microsoft.Xna.Framework.Content.Vector2Reader': self.read_vector2,
            'Microsoft.Xna.Framework.Content.Vector3Reader': self.read_vector3,
            'Microsoft.Xna.Framework.Content.Vector4Reader': self.read_vector4,
            'Microsoft.Xna.Framework.Content.MatrixReader': self.read_matrix,
            'Microsoft.Xna.Framework.Content.QuaternionReader': self.read_quaternion,
            'Microsoft.Xna.Framework.Content.ColorReader': self.read_color,
            'Microsoft.Xna.Framework.Content.PlaneReader': self.read_plane,
            'Microsoft.Xna.Framework.Content.PointReader': self.read_point,
            'Microsoft.Xna.Framework.Content.RectangleReader': self.read_rectangle,
            'Microsoft.Xna.Framework.Content.BoundingBoxReader': self.read_bounding_box,
            'Microsoft.Xna.Framework.Content.BoundingSphereReader': self.read_bounding_sphere,
            'Microsoft.Xna.Framework.Content.BoundingFrustumReader': self.read_bounding_frustum,
            'Microsoft.Xna.Framework.Content.RayReader': self.read_ray,
            'Microsoft.Xna.Framework.Content.CurveReader': self.read_curve,

            # GRAPHICS
            'Microsoft.Xna.Framework.Content.TextureReader': lambda: None,
            'Microsoft.Xna.Framework.Content.Texture2DReader': self.read_texture2d,
            'Microsoft.Xna.Framework.Content.Texture3DReader': self.read_texture3d,
            'Microsoft.Xna.Framework.Content.TextureCubeReader': self.read_texture_cube,
            'Microsoft.Xna.Framework.Content.IndexBufferReader': self.read_index_buffer,
            'Microsoft.Xna.Framework.Content.VertexBufferReader': self.read_vertex_buffer,
            'Microsoft.Xna.Framework.Content.VertexDeclarationReader': self.read_vertex_declaration,
            'Microsoft.Xna.Framework.Content.EffectReader': self.read_effect,
            'Microsoft.Xna.Framework.Content.EffectMaterialReader': self.read_effect_material,
            'Microsoft.Xna.Framework.Content.BasicEffectReader': self.read_basic_effect,
            'Microsoft.Xna.Framework.Content.AlphaTestEffectReader': self.read_alpha_test_effect,
            'Microsoft.Xna.Framework.Content.DualTextureEffectReader': self.read_dual_texture_effect,
            'Microsoft.Xna.Framework.Content.EnvironmentMapEffectReader': self.read_environment_map_effect,
            'Microsoft.Xna.Framework.Content.SkinnedEffectReader': self.read_skinned_effect,
            'Microsoft.Xna.Framework.Content.SpriteFontReader': self.read_sprite_font,
            'Microsoft.Xna.Framework.Content.ModelReader': self.read_model,

            # MEDIA
            'Microsoft.Xna.Framework.Content.SoundEffectReader': self.read_sound_effect,
            'Microsoft.Xna.Framework.Content.SongReader': self.read_song,
            'Microsoft.Xna.Framework.Content.VideoReader': self.read_video
        }

    def _read_one(self, fmt, sz):
        return struct.unpack(fmt, self.fp.read(sz))[0]

    def parse(self):
        return (self.parsers.get(self.type) or (lambda: None))()

    def read_object(self):
        o = ObjectReader(self.fp, self.read_string(), self.save_base)
        return o.parse()

    # PRIMITIVE ---

    def read_byte(self):
        return self._read_one('B', 1)

    def read_sbyte(self):
        return self._read_one('b', 1)

    def read_int16(self):
        return self._read_one('h', 2)

    def read_uint16(self):
        return self._read_one('H', 2)

    def read_int32(self):
        return self._read_one('i', 4)

    def read_uint32(self):
        return self._read_one('I', 4)

    def read_int64(self):
        return self._read_one('q', 8)

    def read_uint64(self):
        return self._read_one('Q', 8)

    def read_single(self):
        return self._read_one('f', 4)

    def read_double(self):
        return self._read_one('d', 8)

    def read_boolean(self):
        return self.read_byte() != 0

    def read_char(self):
        return chr(self.read_byte())

    def read_string(self):
        return self.fp.read(read_leb128(self.fp)).decode('utf-8')

    # SYSTEM ---

    def read_enum(self):
        return self.read_int32()

    def read_nullable(self, reader_fn):
        is_present = self.read_boolean()
        if is_present:
            return reader_fn()

    def read_list(self, reader_fn):
        length = self.read_uint32()
        res = []
        for _ in range(length):
            res.append(reader_fn())

        return res

    read_array = read_list

    def read_dictionary(self, key_reader, value_reader):
        count = self.read_uint32()
        d = {}
        for _ in range(count):
            d[key_reader] = value_reader

        return d

    def read_timespan(self):  # (as C# ticks)
        ticks = self.read_int64()

        if ticks < 0:
            ticks = -ticks

        return {'ticks': ticks}

    def read_datetime(self):
        value = self.read_int64()
        kind = value >> 62
        ticks = value & ~(3 << 62)
        return {
            'kind': kind,
            'ticks': ticks
        }

    def read_decimal(self):
        return [self.read_int32() for _ in range(4)]

    def read_external_reference(self):
        return {
            'asset_name': self.read_string()
        }

    @staticmethod
    def read_reflective():
        error('Reflective readers unfortunately cannot be implemented in Python.')
        error('It is impossible to load a C# class into this program without issues, ')
        error('so to add your own types, add a reader to the ObjectReader class.')
        sys.exit(-1)

    # MATH ---

    def read_vector2(self):
        return {
            'x': self.read_single(),
            'y': self.read_single()
        }

    def read_vector3(self):
        return {
            'x': self.read_single(),
            'y': self.read_single(),
            'z': self.read_single()
        }

    def read_vector4(self):
        return {
            'x': self.read_single(),
            'y': self.read_single(),
            'z': self.read_single(),
            'w': self.read_single()
        }

    def read_matrix(self):
        return tuple(tuple(self.read_single() for _ in range(4)) for _ in range(4))

    def read_quaternion(self):
        return {
            'x': self.read_single(),
            'y': self.read_single(),
            'z': self.read_single(),
            'w': self.read_single()
        }

    def read_color(self):
        return {
            'red': self.read_byte(),
            'green': self.read_byte(),
            'blue': self.read_byte(),
            'alpha': self.read_byte()
        }

    def read_plane(self):
        return {
            'normal': self.read_vector3(),
            'd': self.read_single()
        }

    def read_point(self):
        return {
            'x': self.read_int32(),
            'y': self.read_int32()
        }

    def read_rectangle(self):
        return {
            'x': self.read_int32(),
            'y': self.read_int32(),
            'width': self.read_int32(),
            'height': self.read_int32()
        }

    def read_bounding_box(self):
        return {
            'min': self.read_vector3(),
            'max': self.read_vector3()
        }

    def read_bounding_sphere(self):
        return {
            'center': self.read_vector3(),
            'radius': self.read_single()
        }

    def read_bounding_frustum(self):
        return {'frustum_matrix': self.read_matrix()}

    def read_ray(self):
        return {
            'position': self.read_vector3(),
            'direction': self.read_vector3()
        }

    def read_curve(self):
        values = ['Constant', 'Cycle', 'CycleOffset', 'Oscillate', 'Linear']
        pre_loop = values[self.read_int32()]
        post_loop = values[self.read_int32()]
        key_count = self.read_uint32()
        keys = []
        for _ in range(key_count):
            keys.append({
                'position': self.read_single(),
                'value': self.read_single(),
                'tangent_in': self.read_single(),
                'tangent_out': self.read_single(),
                'continuity': 'Step' if self.read_int32() else 'Smooth'
            })
        return {
            'pre_loop': pre_loop,
            'post_loop': post_loop,
            'keys': keys
        }

    # GRAPHICS ---

    def _col_as_rgba(self, typ):
        if typ == 'Color':
            return tuple(self.read_byte() for _ in range(4))
        if typ == 'Bgr565':
            color = self.read_uint16()
            r = (color & 0xF800) >> 8
            g = (color & 0x07E0) >> 3
            b = (color & 0x001F) << 3
            return r, g, b, 0xFF
        if typ == 'Bgra5551':
            color = self.read_uint16()
            r = (color & 0x7C00) >> 7
            g = (color & 0x03E0) >> 2
            b = (color & 0x001F) << 3
            a = 0xFF if (color & 0x8000) == 0x8000 else 0x00
            return r, g, b, a
        if typ == 'Bgra4444':
            color = self.read_uint16()
            r = (color & 0x0F00) >> 4
            g = (color & 0x00F0)
            b = (color & 0x000F) << 4
            a = (color & 0xF000) >> 8
            return r, g, b, a
        if typ == 'Dxt1' or typ == 'Dxt3' or typ == 'Dxt5':
            error('Dxt1/Dxt3/Dxt5 compression is currently not supported!')
            sys.exit(1)
        if typ == 'NormalizedByte2':
            c = self.read_byte()
            return c, c, c, self.read_byte()
        if typ == 'NormalizedByte4':
            return tuple(self.read_byte() for _ in range(4))
        if typ == 'Rgba1010102':
            color = self.read_uint32()
            r = (color & 0x3FF00000) >> 20
            g = (color & 0x000FFC00) >> 10
            b = (color & 0x000003FF)
            a = (
                0xFF if (color & 0xC0000000) == 0xC0000000
                else (
                    0x80 if (color & 0xC0000000) == 0x80000000
                    else 0x00
                )
            )
            return r, g, b, a
        if typ == 'Rg32':
            return self.read_byte(), self.read_uint32(), 0x00, 0xFF
        if typ == 'Rgba64':
            return tuple(self.read_uint16() // 2 for _ in range(4))
        if typ == 'Alpha8':
            return 0, 0, 0, self.read_byte()
        if typ == 'Single':
            c = self.read_single()
            return c, c, c, c
        if typ == 'Vector2':
            return self.read_single(), self.read_single(), 0x00, 0xFF
        if typ == 'Vector4':
            return tuple(self.read_single() for _ in range(4))
        if typ == 'HalfSingle':
            c = struct.unpack('e', self.fp)[0]
            return c, c, c, c
        if typ == 'HalfVector2':
            return struct.unpack('e', self.fp)[0], struct.unpack('e', self.fp)[0], 0x00, 0xFF
        if typ == 'HalfVector4':
            return tuple(struct.unpack('e', self.fp)[0] for _ in range(4))
        if typ == 'HdrBlendable':
            c = self.read_uint16() // 2
            return c, c, c, self.read_uint16() // 2
        error('Unknown pixel format {0}!', typ)

    def read_texture2d(self):
        global indent
        fmt = SURFACE_FORMATS[self.read_int32()]
        info('Format: {0}', fmt)
        width = self.read_uint32()
        info('Width: {0}', width)
        height = self.read_uint32()
        info('Height: {0}', height)
        mip_count = self.read_uint32()
        info('Mip count: {0}', mip_count)

        indent += 2
        for i in range(mip_count):
            info('Mip {0}', i)
            indent += 2
            im = Image.new('RGBA', (width, height))  # We convert the pixels to RGBA
            size = self.read_uint32()
            info('Size: {0}', size)
            pixels = []
            for y in range(height):
                for x in range(width):
                    pxl = self._col_as_rgba(fmt)
                    pixels.append(pxl)

            im.putdata(pixels)
            im.save(self.save_base + f'_mip{i}.png')
            indent -= 2
        indent -= 2

        return {
            'original_format': fmt,
            'width': width,
            'height': height,
            'mip_count': mip_count
        }

    def read_texture3d(self):
        global indent
        fmt = SURFACE_FORMATS[self.read_int32()]
        info('Format: {0}', fmt)
        width = self.read_uint32()
        info('Width: {0}', width)
        height = self.read_uint32()
        info('Height: {0}', height)
        depth = self.read_uint32()
        info('Depth: {0}', depth)
        mip_count = self.read_uint32()
        info('Mip count: {0}', mip_count)

        indent += 2
        for i in range(mip_count):
            info('Mip {0}', i)
            indent += 2
            size = self.read_uint32()
            info('Size: {0}', size)
            for z in range(depth):
                im = Image.new('RGBA', (width, height))
                pixels = []
                for y in range(height):
                    for x in range(width):
                        pxl = self._col_as_rgba(fmt)
                        pixels.append(pxl)

                im.putdata(pixels)

                im.save(self.save_base + f'_mip{i}_z{z}.png')

            indent -= 2
        indent -= 2

        return {
            'original_format': fmt,
            'width': width,
            'height': height,
            'depth': depth,
            'mip_count': mip_count,
        }

    def read_texture_cube(self):
        global indent
        fmt = SURFACE_FORMATS[self.read_int32()]
        info('Format: {0}', fmt)
        size = self.read_uint32()
        info('Size: {0}', size)
        mip_count = self.read_uint32()
        info('Mip count: {0}', mip_count)

        indent += 2
        for face in range(6):
            info('Face {0}', face)
            indent += 2
            for i in range(mip_count):
                info('Mip {0}', i)
                indent += 2

                im = Image.new('RGBA', (size, size))
                data_size = self.read_uint32()
                info('Data size: {0}', data_size)
                pixels = []
                for y in range(size):
                    for x in range(size):
                        pxl = self._col_as_rgba(fmt)
                        pixels.append(pxl)

                im.putdata(pixels)
                im.save(self.save_base + f'_mip{i}_face{face}.png')

                indent -= 2
            indent -= 2
        indent -= 2

        return {
            'original_format': fmt,
            'size': size,
            'mip_count': mip_count,
        }

    def read_index_buffer(self):
        is_short = self.read_boolean()
        info('Is short: {0}', is_short)
        size = self.read_uint32()
        info('Data size: {0}', size)
        # TODO: is this correct? not sure if size is in bytes or values
        return [(self.read_int16() if is_short else self.read_int32()) for _ in range(size // (2 if is_short else 4))]

    def read_vertex_buffer(self):
        decl = self.read_vertex_declaration()
        vertex_count = self.read_uint32()
        info('Vertex count: {0}', vertex_count)
        return {
            'vertex_declaration': decl,
            'vertex_count': vertex_count,
            'vertex_data': self.fp.read(vertex_count * decl['vertex_stride'])
        }

    def read_vertex_declaration(self):
        stride = self.read_uint32()
        info('Vertex stride: {0}', stride)
        elem_count = self.read_uint32()
        info('Element count: {0}', elem_count)
        formats = [
            'Single',
            'Vector2', 'Vector3', 'Vector4',
            'Color',
            'Byte4',
            'Short2', 'Short4',
            'NormalizedShort2', 'NormalizedShort4',
            'HalfVector2', 'HalfVector4'
        ]
        usage = [
            'Position',
            'Color',
            'TextureCoordinate',
            'Normal',
            'Binormal',
            'Tangent',
            'BlendIndices',
            'BlendWeight',
            'Depth',
            'Fog',
            'PointSize',
            'Sample',
            'TessellateFactor'
        ]
        elems = []
        for _ in range(elem_count):
            offset = self.read_uint32()
            elem_format = formats[self.read_int32()]
            elem_usage = usage[self.read_int32()]
            usage_index = self.read_uint32()
            elems.append({
                'offset': offset,
                'element_format': elem_format,
                'element_usage': elem_usage,
                'usage_index': usage_index
            })
        return {
            'vertex_stride': stride,
            'element_count': elem_count,
            'elements': elems
        }

    def read_effect(self):
        size = self.read_uint32()
        return self.fp.read(size)  # Compiled effect bytecode

    def read_effect_material(self):
        return {
            'effect': self.read_external_reference(),
            'parameters': self.read_object()
        }

    def read_basic_effect(self):
        return {
            'texture': self.read_external_reference(),
            'diffuse_color': self.read_vector3(),
            'emissive_color': self.read_vector3(),
            'specular_color': self.read_vector3(),
            'specular_power': self.read_single(),
            'alpha': self.read_single(),
            'vertex_color_enabled': self.read_boolean()
        }

    def read_alpha_test_effect(self):
        compare_functions = [
            'true',
            'false',
            'a < b',
            'a <= b',
            'a == b',
            'a >= b',
            'a > b',
            'a != b'
        ]
        return {
            'texture': self.read_external_reference(),
            'compare_function': compare_functions[self.read_int32()],
            'reference_alpha': self.read_uint32(),
            'diffuse_color': self.read_vector3(),
            'alpha': self.read_single(),
            'vertex_color_enabled': self.read_boolean()
        }

    def read_dual_texture_effect(self):
        return {
            'texture1': self.read_external_reference(),
            'texture2': self.read_external_reference(),
            'diffuse_color': self.read_vector3(),
            'alpha': self.read_single(),
            'vertex_color_enabled': self.read_boolean()
        }

    def read_environment_map_effect(self):
        return {
            'texture': self.read_external_reference(),
            'environment_map': self.read_external_reference(),
            'environment_map_amount': self.read_single(),
            'environment_map_specular': self.read_vector3(),
            'fresnel_factor': self.read_single(),
            'diffuse_color': self.read_vector3(),
            'emissive_color': self.read_vector3(),
            'alpha': self.read_single()
        }

    def read_skinned_effect(self):
        return {
            'texture': self.read_external_reference(),
            'weights_per_vertex': self.read_uint32(),
            'diffuse_color': self.read_vector3(),
            'emissive_color': self.read_vector3(),
            'specular_color': self.read_vector3(),
            'specular_power': self.read_single(),
            'alpha': self.read_single()
        }

    def read_sprite_font(self):
        return {
            'texture': self.read_texture2d(),
            'glyphs': self.read_list(self.read_rectangle),
            'cropping': self.read_list(self.read_rectangle),
            'character_map': self.read_list(self.read_char),
            'vertical_line_spacing': self.read_int32(),
            'horizontal_spacing': self.read_single(),
            'kerning': self.read_list(self.read_vector3),
            'default_char': self.read_nullable(self.read_char)
        }

    def read_model(self):
        bone_count = self.read_uint32()
        if bone_count < 255:
            reference_reader = self.read_byte
        else:
            reference_reader = self.read_uint32
        bone_meta = []
        for _ in range(bone_count):
            name = self.read_string()
            transform = self.read_matrix()
            bone_meta.append({
                'name': name,
                'transform': transform
            })

        bone_refs = []
        for _ in range(bone_count):
            parent = reference_reader()
            child_count = self.read_uint32()
            children = [reference_reader() for _ in range(child_count)]
            bone_refs.append({
                'parent': parent,
                'children': children
            })

        mesh_count = self.read_uint32()
        meshes = []
        for _ in range(mesh_count):
            name = self.read_string()
            parent_bone = reference_reader()
            bounds = self.read_bounding_sphere()
            tag = self.read_object()
            part_count = self.read_uint32()
            parts = []
            for _ in range(part_count):
                parts.append({
                    'vertex_offset': self.read_uint32(),
                    'num_vertices': self.read_uint32(),
                    'start_index': self.read_uint32(),
                    'primitive_count': self.read_uint32(),
                    'mesh_part_tag': self.read_object(),
                    'vertex_buffer': self.read_vertex_buffer(),
                    'index_buffer': self.read_index_buffer(),
                    'effect': self.read_effect()
                })
            meshes.append({
                'name': name,
                'parent_bone': parent_bone,
                'bounds': bounds,
                'tag': tag,
                'parts': parts
            })
        return {
            'meshes': meshes,
            'root_bone': reference_reader(),
            'model_tag': self.read_object()
        }

    def read_sound_effect(self):
        self.read_uint32()  # Format size - unneeded, it's really just a WAVE "fmt " chunk

        waveformatex = self.fp.read(18)[:-2]

        data_size = self.read_uint32()
        data = self.fp.read(data_size)

        # Convert to WAV
        wav = (b'RIFF' + (data_size + 36).to_bytes(4, 'little') +
               b'WAVEfmt \x10\x00\x00\x00' + waveformatex +
               b'data' + data_size.to_bytes(4, 'little') + data)

        with open(self.save_base + '.wav', 'wb') as f:
            f.write(wav)

        loop_start = self.read_int32()
        loop_length = self.read_int32()
        duration = self.read_int32()

        return {
            'loop_start': loop_start,
            'loop_length': loop_length,
            'duration': duration
        }

    def read_song(self):
        return {
            'filename': self.read_string(),
            'duration': self.read_int32()
        }

    def read_video(self):
        return {
            'filename': self.read_string(),
            'duration': self.read_int32(),
            'width': self.read_int32(),
            'height': self.read_int32(),
            'fps': self.read_single(),
            'soundtrack_type': ['Music', 'Dialog', 'MusicAndDialog'][self.read_int32()]
        }


def read_leb128(fp):
    result = 0
    i = 0
    while True:
        byte = fp.read(1)[0]
        result |= (byte & 0x7f) << (7 * i)
        if byte & 0x80 == 0:
            break
    return result


def read_uint32(fp):
    return struct.unpack('I', fp.read(4))[0]


def read_int32(fp):
    return struct.unpack('i', fp.read(4))[0]


def read_qualified_name(fp):
    return fp.read(read_leb128(fp)).decode('utf-8')


def parse_object(fp, readers, save_dir):
    type_id = read_leb128(fp) - 1  # 1-indexed
    if type_id == -1:
        info('Null')
        return None, type_id, None

    try:
        reader = ObjectReader(fp, readers[type_id]['name'], save_dir)
    except IndexError:
        error('Reader out of range!')
        return 1, readers[type_id]['name'], None

    res = reader.parse()
    return None, type_id, res


def parse(fp, outdir):
    global indent

    if os.path.exists(outdir) and os.path.isdir(outdir):
        res = input('Output directory already exists. Overwrite? [y/N] ')
        if res.lower() not in ('y', 'yes'):
            sys.exit(1)

    if fp.read(3) != b'XNB':
        error('File is not an XNB file')
        return 1

    os.makedirs(outdir, exist_ok=True)
    tree = {}

    tp = fp.read(1)
    target_platform = TARGET_PLATFORMS.get(tp)
    if target_platform:
        info('Target platform: {0}', target_platform)
    else:
        warn('Unknown target platform {0}!', tp)

    fv = fp.read(1)[0]
    format_version = FMT_VERSIONS.get(fv)
    if format_version:
        info('Format version: {0}', format_version)
    else:
        warn('Unknown format version {0}!', fv)

    flags = fp.read(1)[0]

    is_hidef, is_compressed = (flags & 0x01) == 0x01, (flags & 0x80) == 0x80
    info('For profile: {0}', 'HiDef' if is_hidef else 'Reach')
    info('Is compressed: {0}', is_compressed)
    if is_compressed:
        error('At this time, compressed XNB files are not supported.')
        return 1

    compressed_size = read_uint32(fp)
    info(f'{"Compressed size" if is_compressed else "Size"}: {compressed_size}')

    if is_compressed:  # will never be true at the moment - TODO: decompression
        decompressed_size = read_uint32(fp)
        info('Decompressed size: {0}', decompressed_size)

    count = read_leb128(fp)
    info('Type reader count: {0}', count)
    indent += 2
    readers = []
    for i in range(count):
        info('Reader {0}', i)
        indent += 2
        type_reader_name = read_qualified_name(fp)
        info('Type reader name: {0}', type_reader_name)
        reader_version = read_int32(fp)
        info('Reader version: {0}', reader_version)

        readers.append({
            'name': type_reader_name,
            'version': reader_version
        })

        indent -= 2

    shared_resource_count = read_leb128(fp)

    indent -= 2
    info('Primary asset:')
    indent += 2

    res, type_id, obj = parse_object(fp, readers, os.path.join(outdir, 'primary'))
    if res is not None:
        return res

    tree['primary'] = obj

    indent -= 2
    info('Shared resources:')
    indent += 2

    tree['shared'] = []

    if shared_resource_count == 0:
        info('<none>')

    for i in range(shared_resource_count):
        info('Resource {0}:', i)
        indent += 2
        res, type_id, obj = parse_object(fp, readers, os.path.join(outdir, f'resource_{i}'))
        if res is not None:
            return res
        info('Type: {0}', type_id)
        tree['shared'].append(obj)
        indent -= 2
    indent -= 2

    with open(os.path.join(outdir, 'index.json'), 'w') as j:
        json.dump(tree, j)
        info('Wrote JSON')

    return 0


def main():
    p = argparse.ArgumentParser()
    p.add_argument('input', help='Valid XNB file to process')
    p.add_argument('-o', '--output',
                   default=None,
                   help='Output directory for resources, defaults to "xnb_output"')
    p.add_argument('-z', '--gzipped', action='store_true', help='Assumes the input file is GZip-compressed')
    args = p.parse_args()

    with open(args.input, 'rb') as f:
        if args.gzipped:
            parse(io.BytesIO(gzip.decompress(f.read())), args.output or './xnb_output')
        else:
            parse(f, args.output or './xnb_output')


if __name__ == '__main__':
    sys.exit(main())
