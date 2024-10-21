

import importlib.resources
from H5Gizmos import do, Html, js_await

class VolumeGizmo:
    """Base class for volume gizmos"""

    def configure_dashboard(self, dash):
        "load js resources"
        # This must be called before the gizmo is "started" (before Html page load).
        import sys
        if (sys.version_info[0], sys.version_info[1]) < (3, 8):
            import pkg_resources# -- deprecated
            modules_path = pkg_resources.resource_filename('volume_gizmos', 'node_modules')
        else:
            import importlib
            fs = importlib.resources.files('volume_gizmos')
            modules_path = str(fs / 'node_modules')  # xxx this should be standardized.
        dash.load_node_modules(modules_path, "nm")
        dash.load_module("webgpu_volume")

    def connect_dashboard(self, dash, connect_callback): # xxx old version
        # This must be called after the gizmo is "started" (after Html page load).
        self.web_gpu_volume = dash.gizmo.modules.webgpu_volume
        self.context = dash.cache("context", self.web_gpu_volume.context())
        do(self.context.connect_then_call(connect_callback))

    async def async_connect_dashboard(self, dash, async_connect_callback): # xxx old version
        # This must be called after the gizmo is "started" (after Html page load).
        self.web_gpu_volume = dash.gizmo.modules.webgpu_volume
        self.context = dash.cache("context", self.web_gpu_volume.context())
        #do(self.context.connect_then_call(connect_callback))
        await js_await(self.context.connect(), get_result=False)
        await async_connect_callback()

    def canvas_component(self, identity, width, height):
        tag = f'<canvas id="{identity}" width="{width}" height="{height}"></canvas>'
        return Html(tag)
    
    def load_array_to_js(self, array, dash, name="cpu_volume"): # xxx old version
        # xxxx should optimize using POST method?
        # component.store_array in 
        # https://github.com/AaronWatters/H5Gizmos/blob/main/doc/Javascript/README.md
        web_gpu_volume = self.web_gpu_volume
        init_volume = dash.new(web_gpu_volume.CPUVolume.Volume, array.shape, array.ravel())
        cpu_volume = dash.cache(name, init_volume )
        return cpu_volume
    
    async def async_load_array_to_js(self, array, dash, name="cpu_volume"):
        buffer_name = name + "_buffer"
        buffer_reference = dash.cache(buffer_name, array.ravel())
        web_gpu_volume = self.web_gpu_volume
        #init_volume = dash.new(web_gpu_volume.CPUVolume.Volume, array.shape, array.ravel())
        init_volume = dash.new(web_gpu_volume.CPUVolume.Volume, array.shape, buffer_reference)
        cpu_volume = dash.cache(name, init_volume )
        return cpu_volume
