
"""
simulated wormholes in np volume arrays.
"""

import numpy as np
import random

def ball(radius):
    """
    Create a ball of radius r in a 3d volume.
    """
    r = radius
    d = 2*r + 1
    x = np.linspace(-r, r, d)
    y = np.linspace(-r, r, d)
    z = np.linspace(-r, r, d)
    xx, yy, zz = np.meshgrid(x, y, z)
    mask = (xx**2 + yy**2 + zz**2) <= r**2
    return mask

def ball255(radius):
    return ball(radius).astype(np.ubyte) * 255

def boolean_blur(array, radius=1):
    result = array.copy()
    result[:-1] |= array[1:]
    result[1:] |= array[:-1]
    result[:,:-1] |= array[:,1:]
    result[:,1:] |= array[:,:-1]
    result[:,:,:-1] |= array[:,:,1:]
    result[:,:,1:] |= array[:,:,:-1]
    return result

def sphere(radius):
    """
    Create a hollow sphere of radius r in a 3d volume.
    """
    outer = ball(radius)
    surr = ~outer
    collapsed = boolean_blur(surr, 1)
    result = outer & collapsed
    # omit xyz planes through the center
    result[radius, :, :] = 0
    result[:, radius, :] = 0
    result[:, :, radius] = 0
    return result

def sphere255(radius):
    return sphere(radius).astype(np.ubyte) * 255

def sphere0(radius):
    """
    Create a hollow sphere of radius r in a 3d volume.
    """
    outer = ball(radius)
    inner = ball(radius-2)
    common = outer[2:-2, 2:-2, 2:-2]
    common[:] = common & ~inner
    return outer

def true_indices(mask, randomize=True):
    """
    Return the index offsets of the true values in a boolean mask.
    Offset by the mask center.
    Suitable for use with fancy indexing.
    """
    if mask.dtype != bool:
        mask = (mask != 0)
    center = np.array(mask.shape) // 2
    aw = np.argwhere(mask) - center
    if randomize:
        # randomize the rows
        np.random.shuffle(aw)
    return (aw[:,0], aw[:,1], aw[:,2])

class IndexSetter:

    def __init__(self, mask):
        self.center = np.array(mask.shape) // 2
        self.mask = mask
        self.indices = true_indices(mask)
        self.index = 0

    def indices_in_direction(self, direction):
        (II, JJ, KK) = self.indices
        product = II * direction[0] + JJ * direction[1] + KK * direction[2]
        mask = product >= 0
        return (II[mask], JJ[mask], KK[mask])

    def mask_indices(self, array, ijk, direction=None):
        if direction is None:
            indices = self.indices
        else:
            indices = self.indices_in_direction(direction)
        (I, J, K) = array.shape
        (i, j, k) = ijk
        (II, JJ, KK) = indices
        (ii, jj, kk) = (i + II, j + JJ, k + KK)
        mask = (0 <= ii) & (ii < I) & (0 <= jj) & (jj < J) & (0 <= kk) & (kk < K)
        return (ii[mask], jj[mask], kk[mask])

    def set(self, array, ijk, value=True, direction=None):
        # only set value at indices that are in range
        (ii, jj, kk) = self.mask_indices(array, ijk, direction)
        array[ii, jj, kk] = value

    def get(self, array, ijk, direction=None):
        (ii, jj, kk) = self.mask_indices(array, ijk, direction)
        return array[ii, jj, kk]
    
    def intersection_penalty(self, array, ijk, direction=None):
        """
        Return the avg of the values in the array at the intersection of the mask and the array.
        """
        got = self.get(array, ijk, direction)
        if got.size == 0:
            return np.inf
        return np.mean(got.astype(float))
    
    def random_offset(self):
        i = np.random.randint(0, len(self.indices[0]))
        return np.array([self.indices[0][i], self.indices[1][i], self.indices[2][i]])
    
    def random_index(self):
        return self.center + self.random_offset()
    
class WormSphere:

    def __init__(self, universe_size=100, big_radius=15, small_radius=8, n_worms=4, border=True, fill=False):
        self.universe_size = universe_size
        self.big_radius = big_radius
        self.small_radius = small_radius
        self.universe_mask = ball(universe_size)
        if border:
            universe_sphere = sphere(universe_size)
            self.universe_tester = IndexSetter(universe_sphere)
        else:
            self.universe_tester = IndexSetter(self.universe_mask)
        self.space = ~self.universe_mask
        self.big_sphere = sphere(big_radius)
        self.small_ball = ball(small_radius)
        self.small_sphere = sphere(small_radius)
        self.small_tester = IndexSetter(self.small_sphere)
        self.small_setter = IndexSetter(self.small_ball)
        if fill:
            big_ball = sphere(big_radius)
            self.small_setter.set(big_ball, np.array(big_ball.shape) // 2)
            self.big_tester = IndexSetter(big_ball)
        else:
            big = ball(big_radius)
            self.big_tester = IndexSetter(big)
        self.n_worms = n_worms
        #self.search_offsets = list(zip(*self.small_tester.indices))
        self.search_offsets = list(map(tuple, zip(*self.small_tester.indices)))
        self.choices = {}

    def init_space(self):
        self.space = (~self.universe_mask).astype(np.uint8) * 256
        self.trace = np.zeros(self.space.shape, dtype=np.uint8)

    def init_space_from_volume(self, volume, boundary=5, boundary_value=255):
        # make space from volume embedded in a box
        embedded_shape = np.array(volume.shape) + 2 * boundary
        self.space = np.zeros(embedded_shape, dtype=volume.dtype)
        self.space[:] = boundary_value
        self.space[boundary:-boundary, boundary:-boundary, boundary:-boundary] = volume
        #self.space[boundary:-boundary, boundary:-boundary, boundary:-boundary] = 0 # debug only
        self.trace = np.zeros(self.space.shape, dtype=np.uint8)

    def initialize_universe(self):
        # choose random locations for the worm locations inside the universe_mask
        self.init_space()
        self.worm_locations = []
        for i in range(self.n_worms):
            location = self.universe_tester.random_index()
            #print ("worm", i, "init location", location)
            self.worm_locations.append(location)
            self.small_setter.set(self.space, location)
        # set a small offset for each worm, randomly
        for location in self.worm_locations:
            offset = self.big_tester.random_offset()
            self.small_setter.set(self.space, location + offset)

    def init_center(self, with_space=True):
        if with_space:
            self.init_space()
        #self.init_space()
        self.worm_locations = []
        for i in range(self.n_worms):
            location = np.array(self.space.shape) // 2
            self.worm_locations.append(location)
            self.small_setter.set(self.space, location)

    def worm_sphere(self, radius, expand=1):
        S = sphere(radius)
        Ind = IndexSetter(S)
        space = self.space
        (I, J, K) = space.shape
        center = np.array(space.shape) // 2
        (ci, cj, ck) = center
        (II, JJ, KK) = Ind.indices
        (ii, jj, kk) = (ci + expand * II, cj + expand * JJ, ck + expand * KK)
        mask = (0 <= ii) & (ii < I) & (0 <= jj) & (jj < J) & (0 <= kk) & (kk < K)
        self.n_worms = len(mask)
        self.worm_locations = []
        for i in range(self.n_worms):
            location = np.array([ii[i], jj[i], kk[i]])
            print ("worm", i, "init location", location)
            self.worm_locations.append(location)
            self.small_setter.set(self.space, location)

    def move_worms(self, count=1, value=255, verbose=False):
        # randomize the search order
        search_offsets = self.search_offsets
        choices = self.choices
        #random.shuffle(search_offsets)
        for i in range(self.n_worms):
            #small_radius = self.small_radius
            location = self.worm_locations[i]
            # try all offsets in small ball, choose the lowest intersection penalty
            best_penalty = None
            best_move = None
            best_offset = None
            random.shuffle(search_offsets)
            for offset0 in search_offsets:
                offset = np.array(offset0)# - small_radius
                move = location + offset
                penalty = self.big_tester.intersection_penalty(self.space, move, offset)
                if verbose:
                    print ("    penalty", penalty, "for move", move, "offset", offset)
                if best_penalty is None:
                    best_penalty = penalty
                    best_move = move
                    best_offset = offset0
                elif penalty <= best_penalty:
                    # move some the time, to make it more interesting
                    #if np.random.random() < 0.1:
                        best_penalty = penalty
                        best_move = move
                        best_offset = offset0
            # move the worm
            #self.small_setter.set(self.space, best_move, True)
            # set at all intermediage positions between location and best_move
            diff = best_move - location
            n_steps = np.max(np.abs(diff))
            for j in range(n_steps+1):
                intermediate = location + j * diff // n_steps
                self.small_setter.set(self.space, intermediate, value)
                self.small_setter.set(self.trace, intermediate, count)
            self.worm_locations[i] = best_move
            choices[best_offset] = choices.get(best_offset, 0) + 1
            if verbose:
                print("worm", i, "moved to", best_move, "penalty", best_penalty)

    def choices_volume(self):
        result = np.zeros(self.small_tester.mask.shape, dtype=np.int32)
        for (offset, count) in self.choices.items():
            result[offset] = count
        return result

    def do_moves(self, n_moves, initialize=True, verbose=True, value=255):
        if initialize:
            self.initialize_universe()
        for i in range(n_moves):
            print ("move", i)
            self.move_worms(n_moves - i + 1, value)
        #self.worm_trails = (self.space & self.universe_mask).astype(np.uint8) * 255

    async def show_trails(self):
        from volume_gizmos import Triptych
        T = Triptych.Triptych(self.trace, 1.0, 1.0, 1.0, 512, name="Worm Trails")
        await T.link()
    