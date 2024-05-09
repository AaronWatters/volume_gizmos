
import numpy as np
from H5Gizmos import Html, serve, get, do, Stack, Slider, Text
from . import VolumeSuper, loaders, color_list
import os

class SegmentationQuad(VolumeSuper.VolumeGizmo):

    def __init__(self, labels, intensities, size=512, dI=1, dJ=1, dK=1):
        assert labels.max() < 256 and labels.min() >= 0, "Labels must be 8-bit."
        self.labels = labels.astype(np.ubyte)
        self.intensities = loaders.scale_to_bytes(intensities)
        nlabels = self.labels.max()
        hex_colors = [0] + list(color_list.get_hex_colors(nlabels))
        #print("hex_colors", list(map(hex, hex_colors)))
        self.colors = np.array(hex_colors, dtype=np.uint32)
        self.size = size
        dash = self.make_dashboard()
        self.configure_dashboard(dash)
        self.dI = dI
        self.dJ = dJ
        self.dK = dK

    def make_dashboard(self):
        size = self.size
        self.seg_slice_canvas = self.canvas_component("seg_slice_canvas", size, size)
        self.seg_shade_canvas = self.canvas_component("seg_shade_canvas", size, size)
        self.int_slice_canvas = self.canvas_component("int_slice_canvas", size, size)
        self.max_int_canvas = self.canvas_component("max_int_canvas", size, size)
        self.seg_slice_text = Text("Segmentation Slice")
        self.seg_shade_text = Text("Segmentation Shaded")
        self.int_slice_text = Text("Intensity Slice")
        self.max_int_text = Text("Max Intensity")
        self.depth_slider = Slider(minimum=0, maximum=255, step=1, value=128, on_change=self.depth_slide)
        self.dash = Stack([
            [
                [self.seg_slice_canvas, self.seg_slice_text],
                [self.seg_shade_canvas, self.seg_shade_text],
            ],
            [
                [self.int_slice_canvas, self.int_slice_text, self.depth_slider],
                [self.max_int_canvas, self.max_int_text],
            ],
        ])
        return self.dash
    
    async def link(self):
        await self.dash.link()
        self.connect_dashboard(self.dash, self.load_volumes)

    async def show(self):
        await self.dash.show()
        self.connect_dashboard(self.dash, self.load_volumes)

    def load_volumes(self):
        web_gpu_volume = self.web_gpu_volume
        context = self.context
        dash = self.dash
        cpu_seg = self.load_array_to_js(self.labels, dash, name="cpu_seg")
        cpu_int = self.load_array_to_js(self.intensities, dash, name="cpu_int")
        #cpu_colors = self.load_array_to_js(self.colors, dash, name="cpu_colors")
        [dK, dJ, dI] = [self.dK, self.dJ, self.dI]
        gpu_seg = dash.cache("gpu_seg", cpu_seg.gpu_volume(context, dK, dJ, dI))
        gpu_int = dash.cache("gpu_int", cpu_int.gpu_volume(context, dK, dJ, dI))
        #gpu_colors = dash.cache("gpu_colors", cpu_colors.gpu_volume(context, dK, dJ, dI))
        view_init = dash.new(
            web_gpu_volume.SegmentationQuad.SegmentationQuad, 
            gpu_seg, 
            gpu_int, 
            self.colors,
            self.range_callback
        )
        self.quad = dash.cache("quad", view_init)
        orbiting = True
        do(self.quad.paint_on_canvases(
            self.seg_slice_canvas.element[0],  
            self.max_int_canvas.element[0],
            self.int_slice_canvas.element[0],
            self.seg_shade_canvas.element[0], 
            orbiting
        ))

    def depth_slide(self, *ignored):
        depth = self.depth_slider.value
        do(self.quad.change_depth(depth))

    def range_callback(self, min_value, max_value):
        self.depth_slider.set_range(minimum=min_value, maximum=max_value)

async def quad(labels_path, intensities_path, size=512, show=True):
    "Load a segmentation quad from files."
    def get_array(path):
        expanded_path = os.path.expanduser(path)
        #print("loading volume", expanded_path)
        return loaders.load_volume(expanded_path)
    labels = get_array(labels_path)
    intensities = get_array(intensities_path)
    quad = SegmentationQuad(labels=labels, intensities=intensities, size=size)
    if show:
        await quad.show()
    return quad

def script(debug=True):
    import argparse
    import os

    parser = argparse.ArgumentParser(description='Display source volume and segmentation.')
    parser.add_argument('--seg', type=str, help='File path to the segmentation', required=True)
    parser.add_argument('--int', type=str, help='File path to the intensities', required=True)
    parser.add_argument('--size', type=int, help='canvas size', default=512)

    args = parser.parse_args()
    expanded_int = os.path.expanduser(args.int)
    expanded_seg = os.path.expanduser(args.seg)
    if debug:
        print("int path:", expanded_int)
        print("seg path:", expanded_seg)
        print("size:", args.size)
    print("loading intensity volume")
    ar_int = loaders.load_volume(expanded_int)
    print("loading segmentation volume")
    ar_seg = loaders.load_volume(expanded_seg)
    print("loaded volumes", ar_int.shape, ar_seg.shape, ar_int.dtype, ar_seg.dtype)
    quad = SegmentationQuad(labels=ar_seg, intensities=ar_int, size=args.size)
    serve(quad.link())
