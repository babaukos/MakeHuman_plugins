#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import math
import OpenGL.GL as GL
import glmodule
from core import G

def _rotate_y(v, deg):
    rad = math.radians(deg)
    c, s = math.cos(rad), math.sin(rad)
    x, y, z = v
    return (c * x + s * z, y, -s * x + c * z)

def _rotate_x(v, deg):
    rad = math.radians(deg)
    c, s = math.cos(rad), math.sin(rad)
    x, y, z = v
    return (x, c * y - s * z, s * y + c * z)

def _apply_rotation(v, rotX, rotY):
    v = _rotate_y(v, rotY)
    v = _rotate_x(v, rotX)
    return v

_FACES = [
    ('right', (1, 0, 0)), ('left', (-1, 0, 0)),
    ('top', (0, 1, 0)), ('bottom', (0, -1, 0)),
    ('front', (0, 0, 1)), ('back', (0, 0, -1)),
]

_NEGATIVE = {'left', 'bottom', 'back'}
_AXIS_COLOR = {
    'right': (1.0, 0.0, 0.0), 'left': (1.0, 0.0, 0.0),
    'top': (0.0, 1.0, 0.0), 'bottom': (0.0, 1.0, 0.0),
    'front': (0.0, 0.0, 1.0), 'back': (0.0, 0.0, 1.0),
}

_GLYPH_X = [(-3, -3, 3, 3), (-3, 3, 3, -3)]
_GLYPH_Y = [(-3, 3, 0, 0), (3, 3, 0, 0), (0, 0, 0, -3)]
_GLYPH_Z = [(-3, 3, 3, 3), (3, 3, -3, -3), (-3, -3, 3, -3)]
_GLYPHS = {'right': _GLYPH_X, 'left': _GLYPH_X, 'top': _GLYPH_Y, 
           'bottom': _GLYPH_Y, 'front': _GLYPH_Z, 'back': _GLYPH_Z}

_CUBE_GRAY = (0.55, 0.55, 0.55)
_EDGE_COLOR = (0.05, 0.05, 0.05)
_FACE_FILL_THRESHOLD = 0.05

class NavCubeRenderer:
    def __init__(self, app):
        self.app = app
        self.half_size = 18
        self.margin = 40
        self._original_draw = glmodule.draw
        glmodule.draw = self._wrapped_draw
        self._canvas = app.mainwin.canvas
        self._original_mouse_press = self._canvas.mousePressEvent
        self._canvas.mousePressEvent = self._on_mouse_press

    def _wrapped_draw(self, *args, **kwargs):
        production = bool(args[0]) if args else kwargs.get('productionRender', False)
        result = self._original_draw(*args, **kwargs)
        if not production and self._should_render(): self._render_cube()
        return result

    def _should_render(self):
        task = self.app.currentTask
        return not (task and task.category and task.category.name == 'Rendering')

    def _gizmo_origin(self): return G.windowWidth - self.margin, G.windowHeight - self.margin

    def _current_rotation(self):
        try: return self.app.modelCamera.getRotation()[:2]
        except: return 0.0, 0.0

    def _render_cube(self):
        GL.glPushAttrib(GL.GL_ENABLE_BIT | GL.GL_CURRENT_BIT)
        GL.glDisable(GL.GL_DEPTH_TEST)
        GL.glDisable(GL.GL_LIGHTING)
        GL.glMatrixMode(GL.GL_PROJECTION)
        GL.glPushMatrix()
        GL.glLoadIdentity()
        GL.glOrtho(0, G.windowWidth, 0, G.windowHeight, -200, 200)
        GL.glMatrixMode(GL.GL_MODELVIEW)
        GL.glPushMatrix()
        GL.glLoadIdentity()
        ox, oy = self._gizmo_origin()
        GL.glTranslatef(ox, oy, 0)
        rotX, rotY = self._current_rotation()
        GL.glRotatef(rotX, 1.0, 0.0, 0.0)
        GL.glRotatef(rotY, 0.0, 1.0, 0.0)

        s = self.half_size
        # Малюємо грані
        GL.glColor3f(*_CUBE_GRAY)
        GL.glBegin(GL.GL_QUADS)
        for name, normal in _FACES:
            rn = _apply_rotation(normal, rotX, rotY)
            if rn[2] > _FACE_FILL_THRESHOLD:
                for v in self._face_quad(s, name): GL.glVertex3f(*v)
        GL.glEnd()
        
        self._draw_edges(s)

        # Малюємо підписи
        for name, normal in _FACES:
            rn = _apply_rotation(normal, rotX, rotY)
            
            # Корекція: центр грані у 3D просторі (співвідношення s)
            # Ми додаємо невеликий зсув по нормалі (rn), щоб текст був "над" гранню
            offset = 1.0 
            cx, cy, cz = rn[0] * (s + offset), rn[1] * (s + offset), rn[2] * (s + offset)
            
            # Передаємо обернену нормаль (rn) у функцію, щоб вона могла 
            # правильно зорієнтувати відступ
            self._draw_label(cx, cy, cz, _AXIS_COLOR[name], _GLYPHS[name], name in _NEGATIVE, rn)
        
        GL.glPopMatrix()
        GL.glMatrixMode(GL.GL_PROJECTION)
        GL.glPopMatrix()
        GL.glPopAttrib()

    def _draw_label(self, x, y, z, color, glyph_lines, negative, rn):
        GL.glColor3f(*color)
        GL.glLineWidth(1.5)
        GL.glBegin(GL.GL_LINES)
        
        # negative флаг для мінуса
        if negative:
            # Мінус зміщуємо відносно нормалі, щоб він завжди був зліва від літери
            GL.glVertex3f(x - 9, y, z); GL.glVertex3f(x - 5, y, z)
            
        for (x1, y1, x2, y2) in glyph_lines:
            # Тут важливо: ми додаємо x1, y1 до вже зміщених x, y
            # Літери будуть центровані відносно cx, cy, cz (центру грані)
            GL.glVertex3f(x + x1, y + y1, z); GL.glVertex3f(x + x2, y + y2, z)
        GL.glEnd()

    def _face_quad(self, s, name):
        quads = {
            'right': [(s, -s, -s), (s, s, -s), (s, s, s), (s, -s, s)],
            'left': [(-s, -s, s), (-s, s, s), (-s, s, -s), (-s, -s, -s)],
            'top': [(-s, s, -s), (-s, s, s), (s, s, s), (s, s, -s)],
            'bottom': [(-s, -s, s), (-s, -s, -s), (s, -s, -s), (s, -s, s)],
            'front': [(-s, -s, s), (s, -s, s), (s, s, s), (-s, s, s)],
            'back': [(s, -s, -s), (-s, -s, -s), (-s, s, -s), (s, s, -s)],
        }
        return quads[name]

    def _draw_edges(self, s):
        GL.glColor3f(*_EDGE_COLOR)
        GL.glLineWidth(1.5)
        corners = [(-s, -s, -s), (s, -s, -s), (s, s, -s), (-s, s, -s), (-s, -s, s), (s, -s, s), (s, s, s), (-s, s, s)]
        edges = [(0, 1), (1, 2), (2, 3), (3, 0), (4, 5), (5, 6), (6, 7), (7, 4), (0, 4), (1, 5), (2, 6), (3, 7)]
        GL.glBegin(GL.GL_LINES)
        for a, b in edges: GL.glVertex3f(*corners[a]); GL.glVertex3f(*corners[b])
        GL.glEnd()

    def _on_mouse_press(self, event):
        try:
            if not self._try_handle_click(event): self._original_mouse_press(event)
        except: self._original_mouse_press(event)

    def _try_handle_click(self, event):
        if not self._should_render(): return False
        dx, dy = event.x() - self._gizmo_origin()[0], (self._canvas.height() - event.y()) - self._gizmo_origin()[1]
        s = self.half_size
        if abs(dx) > s * 1.6 or abs(dy) > s * 1.6: return False
        rotX, rotY = self._current_rotation()
        best_name, best_dist = None, None
        for name, normal in _FACES:
            rn = _apply_rotation(normal, rotX, rotY)
            dist = (dx - rn[0] * s) ** 2 + (dy - rn[1] * s) ** 2
            if best_dist is None or dist < best_dist:
                best_dist, best_name = dist, name
        if best_dist is not None and best_dist < (s * 1.3) ** 2:
            self._snap_to_view(best_name); return True
        return False

    def _snap_to_view(self, name):
        mapping = {'front': self.app.frontView, 'back': self.app.backView, 'left': self.app.leftView,
                   'right': self.app.rightView, 'top': self.app.topView, 'bottom': self.app.bottomView}
        if mapping.get(name): mapping[name]()

    def restore(self):
        glmodule.draw = self._original_draw
        self._canvas.mousePressEvent = self._original_mouse_press

def load(app): app.nav_cube = NavCubeRenderer(app)
def unload(app):
    if hasattr(app, 'nav_cube'): app.nav_cube.restore(); del app.nav_cube