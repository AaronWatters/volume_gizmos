
"""
Load a volume from a file of various formats.
"""

import numpy as np

def load_volume(fn):
    """
    Load a volume from a file of various formats.
    """
    if fn.endswith(".npz"):
        return load_npz(fn)
    elif fn.endswith(".npy"):
        ar = np.load(fn)
    elif fn.endswith(".h5"):
        ar = load_h5(fn)
    elif fn.endswith(".tif") or fn.endswith(".tiff"):
        return load_tiff(fn)
    elif fn.endswith(".klb"):
        return load_klb(fn)
    elif fn.endswith(".nii") or fn.endswith(".nii.gz"):
        return load_nii(fn)
    else:
        raise ValueError("Unknown file format: " + fn)
    return ar

def load_npz(fn):
    """
    Load a volume from a numpy npz file.
    """
    data = np.load(fn)
    # look for the first 3d volume in the file
    for key in data.keys():
        ar = data[key]
        if hasattr(ar, "shape") and len(ar.shape) == 3:
            return ar
        
def load_tiff(tiff_path):
    """
    Load a volume from a tiff file.
    """
    # copied from mouse_embryo_labeller.tools
    from PIL import Image, ImageSequence
    im = Image.open(tiff_path)
    L = []
    for i, page in enumerate(ImageSequence.Iterator(im)):
        a = np.array(page)
        # only the first channel
        if len(a.shape) == 3:
            a = a[:, :, 0]
        # flip j and k
        a = a.transpose()
        L.append(a)
    All = np.zeros( (len(L),) + L[0].shape, dtype=a.dtype)
    for (i, aa) in enumerate(L):
        All[i] = aa
    return All
        
def load_h5(fn):
    """
    Load a volume from an HDF5 file.
    """
    raise NotImplementedError("HDF5 loading not implemented yet.")
    #import h5py
    #with h5py.File(fn, "r") as f:
    #    ar = f["data"][:]
    #return ar

def load_klb(fn):
    """
    Load a volume from a KLB file.
    """
    try:
        import pyklb
    except ImportError:
        print ("Please install pyklb or fix any install problems.")
        print ("Install problem fix at: https://github.com/bhoeckendorf/pyklb/issues/3")
        raise
    ar = pyklb.readfull(fn)
    return ar

def load_nii(fn):
    """
    Load a volume from a Nifti file.
    """
    try:
        import nibabel as nib
    except ImportError:
        print ("The nibabel package is required for Nifti file loading.")
        print ("It is not automatically installed with this package.")
        print ("  pip install nibabel")
        print ("Please install nibabel.")
        raise
    img = nib.load(fn)
    ar = img.get_fdata()
    return ar

def scale_to_bytes(array):
    """
    Scale an array to bytes for transfer.
    """
    mn = array.min()
    mx = array.max()
    array1 = (array.astype(float) - mn) / (mx - mn)
    array8 = (array1 * 255).astype(np.uint8)
    return array8
