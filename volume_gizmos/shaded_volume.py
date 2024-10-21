
"""
Colorized index volume with shading.
"""

import numpy as np
from H5Gizmos import Html, serve, get, do, Stack, Slider, Text
from . import VolumeSuper, loaders, color_list
import os

class ShadedVolume(VolumeSuper.VolumeGizmo):

    def __init__(self, array, hex_colors=None, size=512, dI=1, dJ=1, dK=1, ratio=0.7, rotate=True):
        self.ratio = ratio
        self.orbiting = rotate
        self.array = array
        if hex_colors is None:
            hex_colors = [0] + color_list.get_hex_colors(array.max())
        self.hex_colors = np.array(hex_colors, dtype=np.uint32)
        self.size = size
        dash = self.make_dashboard()
        self.configure_dashboard(dash)
        self.dI = dI
        self.dJ = dJ
        self.dK = dK

    def make_dashboard(self):
        size = self.size
        self.shade_canvas = self.canvas_component("shade_canvas", size, size)
        self.status_text = Text("Status")
        self.dash = Stack([
            self.shade_canvas,
            self.status_text,
        ])
        return self.dash
    
    def status(self, text):
        self.status_text.text(text)
    
    async def link(self):
        await self.dash.link()
        await self.async_connect_dashboard(self.dash, self.load_volume_async)

    async def show(self):
        await self.dash.show()
        self.status("dashboard shown")
        await self.async_connect_dashboard(self.dash, self.load_volume_async)
        self.status("connected")

    async def load_volume_async(self):
        web_gpu_volume = self.web_gpu_volume
        context = self.context
        dash = self.dash
        cpu_volume = await self.async_load_array_to_js(self.array, dash)
        [dK, dJ, dI] = [self.dK, self.dJ, self.dI]
        gpu_volume = dash.cache("gpu_volume", cpu_volume.gpu_volume(context, dK, dJ, dI))
        view_init = dash.new(web_gpu_volume.MixView.Mix, gpu_volume, self.hex_colors, self.ratio)
        self.mix_view = dash.cache("mix_view", view_init)
        do(self.mix_view.paint_on(self.shade_canvas.element[0], self.orbiting))
        self.status("loaded")

async def test_shaded_volume():
    array = np.random.randint(0, 256, (64, 64, 64), dtype=np.uint8)
    gizmo = ShadedVolume(array)
    await gizmo.show()

if __name__ == "__main__":
    serve(test_shaded_volume)
