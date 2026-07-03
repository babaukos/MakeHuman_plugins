#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import OpenGL.GL as GL
import glmodule
from core import G


class AxisTripodRenderer:
    def __init__(self, app):
        self.app = app
        self.size = 25

        self._original_draw = glmodule.draw
        glmodule.draw = self._wrapped_draw

    def _wrapped_draw(self, *args, **kwargs):
        production = False
        if args:
            production = bool(args[0])
        elif 'productionRender' in kwargs:
            production = bool(kwargs['productionRender'])

        result = self._original_draw(*args, **kwargs)

        if not production and self._should_render_gizmo():
            self._render_gizmo()

        return result

    def _should_render_gizmo(self):
        try:
            task = self.app.currentTask
            if task is None or task.category is None:
                return True
            if task.category.name == 'Rendering':
                return False
        except Exception:
            pass
        return True
    
    def _render_gizmo(self):
        GL.glPushAttrib(GL.GL_ENABLE_BIT | GL.GL_CURRENT_BIT)
        GL.glDisable(GL.GL_DEPTH_TEST)
        GL.glDisable(GL.GL_LIGHTING)
        GL.glDisable(GL.GL_TEXTURE_2D)

        width = G.windowWidth
        height = G.windowHeight

        GL.glMatrixMode(GL.GL_PROJECTION)
        GL.glPushMatrix()
        GL.glLoadIdentity()
        GL.glOrtho(0, width, 0, height, -200, 200)

        GL.glMatrixMode(GL.GL_MODELVIEW)
        GL.glPushMatrix()
        GL.glLoadIdentity()

        # позиція гізмо в кутку екрана
        GL.glTranslatef(45, 45, 0)

        # --- синхронізація з обертанням камери ---
        try:
            rot = self.app.modelCamera.getRotation()
            # порядок/знак можуть відрізнятись залежно від версії MH —
            # якщо орієнтація виглядить "дзеркальною", поміняй місцями
            # рядки нижче або зміни знак (-rot[0] / -rot[1])
            GL.glRotatef(rot[0], 1.0, 0.0, 0.0)
            GL.glRotatef(rot[1], 0.0, 1.0, 0.0)
        except Exception:
            pass  # якщо камера ще не ініціалізована — просто без обертання

        GL.glLineWidth(1.5)

        s = self.size
        # --- осі ---
        GL.glBegin(GL.GL_LINES)
        GL.glColor3f(1.0, 0.0, 0.0)
        GL.glVertex3f(0, 0, 0); GL.glVertex3f(s, 0, 0)
        GL.glColor3f(0.0, 1.0, 0.0)
        GL.glVertex3f(0, 0, 0); GL.glVertex3f(0, s, 0)
        GL.glColor3f(0.0, 0.0, 1.0)
        GL.glVertex3f(0, 0, 0); GL.glVertex3f(0, 0, s)
        GL.glEnd()

        # --- підписи X / Y / Z (прості штрихові літери) ---
        off = s + 10
        self._draw_label(off, 0, 0, (1.0, 0.0, 0.0), self._GLYPH_X)
        self._draw_label(0, off, 0, (0.0, 1.0, 0.0), self._GLYPH_Y)
        self._draw_label(0, 0, off, (0.0, 0.0, 1.0), self._GLYPH_Z)

        GL.glPopMatrix()
        GL.glMatrixMode(GL.GL_PROJECTION)
        GL.glPopMatrix()
        GL.glPopAttrib()

    # прості "векторні" літери, набір відрізків (x1,y1,x2,y2)
    _GLYPH_X = [(-3, -3, 3, 3), (-3, 3, 3, -3)]
    _GLYPH_Y = [(-3, 3, 0, 0), (3, 3, 0, 0), (0, 0, 0, -3)]
    _GLYPH_Z = [(-3, 3, 3, 3), (3, 3, -3, -3), (-3, -3, 3, -3)]

    def _draw_label(self, x, y, z, color, glyph_lines):
        GL.glColor3f(*color)
        GL.glLineWidth(1.5)
        GL.glBegin(GL.GL_LINES)
        for (x1, y1, x2, y2) in glyph_lines:
            GL.glVertex3f(x + x1, y + y1, z)
            GL.glVertex3f(x + x2, y + y2, z)
        GL.glEnd()

    def restore(self):
        glmodule.draw = self._original_draw


def load(app):
    app.axis_tripod = AxisTripodRenderer(app)
    print("Axis Tripod: hooked into glmodule.draw()")


def unload(app):
    if hasattr(app, 'axis_tripod'):
        app.axis_tripod.restore()
        del app.axis_tripod