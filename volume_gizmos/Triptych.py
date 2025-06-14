
from H5Gizmos import Html, serve, get, do, Stack, Slider, Text, ClickableText
from . import VolumeSuper, loaders
import os

class Triptych(VolumeSuper.VolumeGizmo):

    def __init__(self, array, dK=1, dJ=1, dI=1, size=512, orbiting=True, name="Triptych"):
        self.array = array
        self.dK = dK
        self.dJ = dJ
        self.dI = dI
        self.size = size
        self.name = name
        self.orbiting = orbiting
        dash = self.make_dashboard()
        self.configure_dashboard(dash)

    async def link(self):
        await self.dash.link()
        await self.async_connect_dashboard(self.dash, self.load_volume_async)

    async def show(self):
        await self.dash.show()
        await self.async_connect_dashboard(self.dash, self.load_volume_async)

    async def load_volume_async(self):
        self.set_status("Loading volume... " + repr(self.array.shape))
        web_gpu_volume = self.web_gpu_volume
        context = self.context
        dash = self.dash
        #cpu_volume = self.load_array_to_js(self.array, dash)
        cpu_volume = await self.async_load_array_to_js(self.array, dash)
        [dK, dJ, dI] = [self.dK, self.dJ, self.dI]
        gpu_volume = dash.cache("gpu_volume", cpu_volume.gpu_volume(context, dK, dJ, dI))
        view_init = dash.new(web_gpu_volume.Triptych.Triptych, gpu_volume, self.range_callback)
        orbiting = True
        self.triptych = dash.cache("triptych", view_init)
        do(self.triptych.paint_on_canvases(
            self.iso_canvas.element[0], 
            self.max_canvas.element[0], 
            self.slice_canvas.element[0], 
            orbiting)
        )
        self.set_status(repr(self.name) + " loaded async.")

    def make_dashboard(self):
        size = self.size
        self.iso_canvas = self.canvas_component("iso-canvas", size, size)
        #self.iso_canvas = Html('<canvas id="iso-canvas" width="512" height="512"></canvas>')
        self.level_text = Text("Level")
        mn = float(self.array.min())
        mx = float(self.array.max())
        md = (mn + mx) / 2
        step = 1
        if mx - mn > 1e-6:
            step = (mx - mn) / 255
        else:
            mx = mn + 1
        self.level_slider = Slider(minimum=mn, maximum=mx, step=step, value=md, on_change=self.threshold_slide)
        self.max_canvas = self.canvas_component("max-canvas", size, size)
        self.status_text = Text("Status")
        self.depth_text = Text("Depth")
        self.depth_slider = Slider(minimum=0, maximum=255, step=1, value=128, on_change=self.depth_slide)
        self.slice_canvas = self.canvas_component("slice-canvas", size, size)
        self.colorize = ClickableText("Colorize", on_click=self.colorize_click)
        self.colorize.css(color="blue")
        self.colorized = False
        self.dash = Stack([
            [
                [self.iso_canvas, self.level_text, self.level_slider],
                [self.max_canvas, self.colorize, self.status_text], 
                [self.slice_canvas, self.depth_text, self.depth_slider],
            ],
        ])
        return self.dash
    
    def set_status(self, text):
        self.status_text.text(text)

    def colorize_click(self, *ignored):
        self.colorized = not self.colorized
        do(self.triptych.set_colorize(self.colorized))
        if self.colorized:
            self.colorize.text("Uncolorize")
        else:
            self.colorize.text("Colorize")

    def range_callback(self, min_value, max_value):
        self.depth_slider.set_range(minimum=min_value, maximum=max_value)
    
    def threshold_slide(self, *ignored):
        level = self.level_slider.value
        do(self.triptych.change_threshold(level))
        self.level_text.text("Level: " + str(level))

    def depth_slide(self, *ignored):
        depth = self.depth_slider.value
        do(self.triptych.change_depth(depth))
        self.depth_text.text("Depth: " + str(depth))

async def panels(volume_path, dK=1.0, dJ=1.0, dI=1.0, size=512, show=True):
    expanded_volume = os.path.expanduser(volume_path)
    print("Loading volume", repr(volume_path))
    array = loaders.load_volume(expanded_volume)
    print("loaded", array.shape, array.dtype)
    name = os.path.split(expanded_volume)[-1]
    triptych = Triptych(array, dK, dJ, dI, size, name=name)
    if show:
        await triptych.show()
    return triptych
    
def script(debug=True):
    import argparse
    import os

    # Create an ArgumentParser object
    parser = argparse.ArgumentParser(description='Display iso-surface, slice, and max-values for a 3d volume array.')

    # Add the file path argument
    parser.add_argument('--volume', type=str, help='File path to the volume', required=True)

    # Add the three float arguments
    parser.add_argument('--dI', type=float, help='voxel width', default=1.0)
    parser.add_argument('--dJ', type=float, help='voxel height', default=1.0)
    parser.add_argument('--dK', type=float, help='voxel depth', default=1.0)
    parser.add_argument('--size', type=int, help='canvas size', default=512)

    # Parse the arguments from the command line
    args = parser.parse_args()

    expanded_volume = os.path.expanduser(args.volume)
    if debug:
        print("File path:", expanded_volume)
        print("width (dI):", args.dI)
        print("height (dJ):", args.dJ)
        print("depth (dK):", args.dK)
        print("canvas size:", args.size)

    print("Loading volume", repr(args.volume))
    array = loaders.load_volume(expanded_volume)
    print("loaded", array.shape, array.dtype)
    arrayf32 = array.astype('float32')
    name = os.path.split(expanded_volume)[-1]
    #arrayf32 = arrayf32[::5, ::5, ::5]
    triptych = Triptych(arrayf32, args.dK, args.dJ, args.dI, args.size, name=name)
    serve(triptych.link())
