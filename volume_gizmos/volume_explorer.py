
import H5Gizmos as h5
import numpy as np
import asyncio

class Indexer:

    def __init__(self, label, dim, size, screen_width, voxel_width, change_callback=None, index=None):
        if index is None:
            index = size // 2
        self.dim = dim
        self.index = index
        self.change_callback = change_callback
        self.size = size
        self.screen_width = screen_width
        self.voxel_width = voxel_width
        self.delta = int(voxel_width / 2)
        self.stride = max(1, int(size / screen_width))
        self.dash = self.dashboard(label=label)

    def change_index(self, index=None, callback=True):
        if index is None:
            index = self.index
        self.index = int(index)
        if callback and self.change_callback is not None:
            self.change_callback(self.index)
        self.input.set_value(str(self.index))

    def offsets(self, index=None):
        if index is None:
            index = self.index
        index = min(self.size - 1, max(0, index))
        minimum = max(0, index - self.delta)
        maximum = min(self.size, index + self.delta)
        return dict(minimum=minimum, maximum=maximum, stride=self.stride)
    
    def dashboard(self, label):
        textlabel = h5.Text(label)
        self.input = h5.Input(initial_value=str(self.index))
        def on_input_change(*ignored):
            try:
                index = int(self.input.value)
            except ValueError:
                self.index.set_value(str(self.index))
            else:
                if index != self.index:
                    self.change_index(index)
        self.input.on_enter(on_input_change)
        def increment(*ignored):
            self.change_index(self.index + 1)
        def decrement(*ignored):
            self.change_index(self.index - 1)
        self.add_one = h5.Button("+1", on_click=increment)
        self.minus_one = h5.Button("-1", on_click=decrement)
        dash = h5.Shelf([
            textlabel, self.input, self.add_one, self.minus_one,
        ])
        return dash
    
    def overview_slice(self):
        return slice(0, self.size, self.stride)
    
    def pixel2overview(self, pixel):
        return int(pixel * self.stride)
    
    def overview2pixel(self, index):
        return int(index // self.stride)

    def detail_slice(self):
        return slice(self.offsets()["minimum"], self.offsets()["maximum"])
    
    def pixel2detail(self, pixel):
        return int(pixel + self.offsets()["minimum"])
    
    def detail2pixel(self, index):
        return int(index - self.offsets()["minimum"]) // self.stride

    
class Slicer:

    outline = True
    shift = True

    def __init__(self, label, explorer, dim):
        self.label = label
        self.explorer = explorer
        self.dim = dim
        #self.indices = self.location2d()
        self.indices = self.explorer.locate()
        self.dash = self.dashboard()
    async def update_if_needed(self):
        #indices = self.location2d()
        indices = self.explorer.locate()
        if indices != self.indices:
            self.indices = indices
            await self.update()
    def dashboard(self):
        width = self.explorer.screen_width
        overview = self.overview_slice()
        detail = self.detail_slice()
        self.overview_image = h5.Image(array=overview, height=width, width=width)
        self.overview_image.css({"image-rendering": "pixelated"})
        self.overview_image.on_pixel(self.overview_click)
        self.detail_image = h5.Image(array=detail, height=width, width=width)
        self.detail_image.css({"image-rendering": "pixelated"})
        self.detail_image.on_pixel(self.detail_click)
        label_text = h5.Text(self.label)
        self.location_text = h5.Text(self.location_info())
        dash = h5.Stack([
            [
                label_text,
                self.location_text,
            ],
            [
                self.overview_image,
                self.detail_image,
            ],
        ])
        return dash
    async def update(self):
        self.location_text.text("updating")
        await asyncio.sleep(0)
        self.overview_image.change_array(self.overview_slice())
        await asyncio.sleep(0)
        self.detail_image.change_array(self.detail_slice())
        self.location_text.text(self.location_info())
    def location_info(self):
        location = self.location2d()
        value = self.explorer.volume[self.explorer.locate()]
        return str(location) + " : " + str(value)
    def location2d(self):
        location = []
        # store the indexers for the other two dimensions
        self.indexers = []
        for dim in range(3):
            if dim != self.dim:
                indexer = self.explorer.indexers[dim]
                index = indexer.index
                self.indexers.append(indexer)
                location.append(index)
        return tuple(location)
    def detail_click(self, event, update=True):
        column = event["pixel_column"]
        row = event["pixel_row"]
        for (pixel, indexer) in zip((row, column), self.indexers):
            index = indexer.pixel2detail(pixel)
            # store the value without callback
            indexer.index = index
        if update:
            #self.update()
            self.explorer.update()
    def overview_click(self, event, update=True):
        column = event["pixel_column"]
        row = event["pixel_row"]
        for (pixel, indexer) in zip((row, column), self.indexers):
            index = indexer.pixel2overview(pixel)
            # store the value without callback
            indexer.index = index
        if update:
            #self.update()
            self.explorer.update()

    def overview_slice(self):
        slices = []
        indexers = []
        for dim in range(3):
            indexer = self.explorer.indexers[dim]
            if dim != self.dim:
                islice = indexer.overview_slice()
                slices.append(islice)
                indexers.append(indexer)
            else:
                slices.append(indexer.index)
        sliced = self.explorer.volume[tuple(slices)].copy()
        # apply an outline
        if self.outline:
            # convert from grayscale to RGB
            sliced = np.stack([sliced] * 3, axis=-1)
            [i1, i2] = indexers
            i1offsets = i1.offsets()
            i2offsets = i2.offsets()
            i1min = i1.overview2pixel(i1offsets["minimum"])
            i1max = i1.overview2pixel(i1offsets["maximum"])-1
            i2min = i2.overview2pixel(i2offsets["minimum"])
            i2max = i2.overview2pixel(i2offsets["maximum"])-1
            sliced[i1min:i1max, i2min, 0] = 255
            sliced[i1min:i1max, i2max, 0] = 255
            sliced[i1min, i2min:i2max, 0] = 255
            sliced[i1max, i2min:i2max, 0] = 255
        return sliced
        
    def detail_slice(self):
        slices = []
        for dim in range(3):
            indexer = self.explorer.indexers[dim]
            if dim != self.dim:
                islice = indexer.detail_slice()
                slices.append(islice)
            else:
                slices.append(indexer.index)
        sliced = self.explorer.volume[tuple(slices)]
        #print("slices", slices)
        if self.shift:
            indexer = self.explorer.indexers[self.dim]
            shifts = []
            if indexer.index > 0:
                slices[self.dim] = indexer.index - 1
                #print("before slices", slices)
                shifted = self.explorer.volume[tuple(slices)]
                shifts.append(shifted)
            else:
                shifts.append(sliced)
            shifts.append(sliced)
            if indexer.index < indexer.size - 1:
                slices[self.dim] = indexer.index + 1
                #print("after slices", slices)
                shifted = self.explorer.volume[tuple(slices)]
                shifts.append(shifted)
            else:
                shifts.append(sliced)
            sliced = np.stack(shifts, axis=-1)
        return sliced

class Explorer:

    def __init__(self, volume, screen_width, voxel_width=None):
        if voxel_width is None:
            voxel_width = screen_width
        self.volume = volume
        self.screen_width = screen_width
        self.voxel_width = voxel_width
        sh = (I, J, K) = volume.shape
        M = max(I, J, K)
        widths = (np.array(sh) * (voxel_width/M)).astype(int)
        self.I_indexer = Indexer("I", 0, I, screen_width, widths[0], self.update)
        self.J_indexer = Indexer("J", 1, J, screen_width, widths[1], self.update)
        self.K_indexer = Indexer("K", 2, K, screen_width, widths[2], self.update)
        self.indexers = [self.I_indexer, self.J_indexer, self.K_indexer]
        self.I_slicer = Slicer("JK", self, 0)
        self.J_slicer = Slicer("IK", self, 1)
        self.K_slicer = Slicer("IJ", self, 2)
        self.slicers = [self.I_slicer, self.J_slicer, self.K_slicer]
        self.dash = self.dashboard()

    def dashboard(self):
        dash = h5.Stack([
            self.I_indexer.dash,
            self.I_slicer.dash,
            self.J_indexer.dash,
            self.J_slicer.dash,
            self.K_indexer.dash,
            self.K_slicer.dash,
        ])
        return dash
    
    def update(self, *ignored):
        h5.schedule_task(self.update_async(*ignored))
    
    async def update_async(self, *ignored):
        from H5Gizmos.python.gz_jQuery import WarningContextManager
        async with WarningContextManager(self.dash, delay_ms=1000):
            for slicer in self.slicers:
                await slicer.update_if_needed()
            for indexer in self.indexers:
                indexer.change_index(callback=False)
            #await asyncio.sleep(10) # for testing

    def locate(self, *ignored):
        location = []
        for dim in range(3):
            index = self.indexers[dim].index
            location.append(index)
        return tuple(location)

class LayersExplorer:

    """
    Explorer optimized for viewing layers of a large volume.
    """

    label = "Layers Explorer"

    def __init__(self, volume, screen_width, voxel_width):
        self.volume = volume
        # pixel width for overview and detail
        self.screen_width = screen_width
        # size of detail
        self.voxel_width = voxel_width
        (I, J, K) = volume.shape
        self.minJKlimit = np.array([0,0], dtype=int)
        self.maxJKlimit = np.array([J - voxel_width, K - voxel_width], dtype=int)
        self.nlayers = I
        self.height = J
        self.width = K
        self.stride = max(1, self.width // self.screen_width)
        self.screen_height = self.height // self.stride
        self.current_layer = self.nlayers // 2
        self.cached_image = None
        self.minJK = np.array([J//2,K//2], dtype=int)
        self.get_slice(layer=self.current_layer)
        self.dash = self.dashboard()

    def setMinJK(self, minJK):
        minJK = np.array(minJK, dtype=int)
        minJK = np.maximum(self.minJKlimit, minJK)
        minJK = np.minimum(self.maxJKlimit, minJK)
        self.minJK = minJK

    def get_slice(self, layer=None, minJK=None):
        # copy in case we are accessing a memmapped array
        print("get_slice", layer, minJK, "current_layer", self.current_layer)
        if layer is None:
            layer = self.current_layer
        if layer != self.current_layer or self.cached_image is None:
            print("loading layer", layer)
            img = self.cached_image = self.volume[layer].copy()
            self.current_layer = layer
            self.minval = img.min()
            self.maxval = max(img.max(), self.minval+1)
        if minJK is not None:
            self.minJK = np.array(minJK, dtype=int)
        img = self.cached_image
        print("get_slice using minJK", self.minJK, "stride", self.stride)
        minJK = self.minJK
        maxJK = minJK + self.voxel_width
        [mJ, jK] = minJK
        [MJ, MK] = maxJK
        stride = self.stride
        self.layer_detail = self.asbytes(img[mJ:MJ, jK:MK])
        layer_overview = self.asbytes(img[::stride, ::stride])
        # add a red border around layer_overview detail area
        color_overview = np.stack([layer_overview]*3, axis=-1)
        sminJK = minJK // stride
        smaxJK = maxJK // stride
        [smJ, smK] = sminJK
        [sMJ, sMK] = smaxJK
        red = np.array([255, 0, 0], dtype=np.uint8)
        color_overview[ smJ:sMJ, smK] = red
        color_overview[ smJ:sMJ, sMK-1] = red
        color_overview[ smJ, smK:sMK] = red
        color_overview[ sMJ-1, smK:sMK] = red
        self.layer_overview = color_overview
        return self.layer_overview, self.layer_detail

    def asbytes(self, array):
        array = array.astype(np.float32)
        normalized = (array - self.minval) / (self.maxval - self.minval)
        norm256 = normalized * 255
        return np.clip(norm256, 0, 255).astype(np.uint8)
    
    def location_info(self):
        return f"Layer: {self.current_layer}  JK min: {self.minJK.tolist()}"

    def dashboard(self):
        overview = self.layer_overview
        detail = self.layer_detail
        self.overview_image = h5.Image(array=overview, height=self.screen_height, width=self.screen_width)
        self.overview_image.css({"image-rendering": "pixelated"})
        self.overview_image.on_pixel(self.overview_click)
        self.detail_image = h5.Image(array=detail, height=self.screen_width, width=self.screen_width)
        self.detail_image.css({"image-rendering": "pixelated"})
        self.detail_image.on_pixel(self.detail_click)
        label_text = h5.Text(self.label)
        self.location_text = h5.Text(self.location_info())
        self.label_slider = h5.Slider(
            minimum=0,
            maximum=self.nlayers - 1,
            step=1,
            value=self.current_layer,
            on_change=self.layer_change,
        )
        self.label_slider.resize(width=self.screen_width)
        dash = h5.Stack([
            [
                label_text,
                self.location_text,
            ],
            [
                self.label_slider,
            ],
            [
                self.overview_image,
                self.detail_image,
            ],
            "click on the image to change the focus area",
            "adjust the layer with the slider above",
        ])
        return dash
    
    def redraw(self, layer=None, minJK=None):
        try:
            if minJK is not None:
                self.minJK = minJK
            print("redraw", layer, minJK)
            overview, detail = self.get_slice(layer=layer, minJK=self.minJK)
            print("redraw got slices")
            self.overview_image.change_array(overview, url=False)
            print("redraw changed overview")
            self.detail_image.change_array(detail, url=False)
            print("redraw changed detail")
            self.location_text.text(self.location_info())
            print("redraw updated location text")
        except Exception as e:
            print("redraw exception:", e)
            self.location_text.text("Error: " + str(e))
            raise e

    def layer_change(self, event):
        print("layer change event")
        layer = self.label_slider.value
        print("layer change", layer)
        #self.current_layer = layer
        self.redraw(layer=layer)

    def detail_click(self, event, update=True):
        column = event["pixel_column"]
        row = event["pixel_row"]
        print("detail click", row, column)
        offset = np.array([row, column], dtype=int)
        minJK = self.minJK + offset
        self.setMinJK(minJK)
        if update:
            self.redraw()

    def overview_click(self, event, update=True):
        column = event["pixel_column"]
        row = event["pixel_row"]
        print("overview click", row, column)
        self.setMinJK([row * self.stride, column * self.stride])
        if update:
            self.redraw()
