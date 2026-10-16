"""Choose one neutral, 50%-opacity color per geometric line from shaded RGB."""
import numpy as np


def edge_colors(points, matrix, rgb):
    segments = np.asarray(points).reshape(-1, 2, 3)
    # Sample several interior positions, avoiding endpoint intersections.
    t = np.array([.2, .5, .8])[None, :, None]
    samples = segments[:, :1] * (1-t) + segments[:, 1:] * t
    homogeneous = np.concatenate((samples, np.ones(samples.shape[:-1]+(1,))), axis=2)
    clip = homogeneous @ matrix.T
    valid = clip[..., 3] > 1e-10
    ndc = clip[..., :3] / np.maximum(clip[..., 3:4], 1e-10)
    valid &= np.all(np.abs(ndc) <= 1, axis=2)
    h, w = rgb.shape[:2]
    x = np.clip((ndc[..., 0]+1)*.5*w, 0, w-1).astype(int)
    y = np.clip((ndc[..., 1]+1)*.5*h, 0, h-1).astype(int)
    luminance = np.zeros(x.shape)
    # Small spatial average suppresses texture noise. RGB is bottom-up GL data.
    for dx, dy in ((0,0),(-1,0),(1,0),(0,-1),(0,1)):
        color = rgb[np.clip(y+dy,0,h-1), np.clip(x+dx,0,w-1)] / 255.
        luminance += color @ np.array([.2126,.7152,.0722]) / 5
    count = valid.sum(axis=1)
    mean = np.where(count > 0, (luminance*valid).sum(axis=1)/np.maximum(count,1), .5)
    # Shift away from the background, not toward a fixed middle gray.
    target = np.clip(mean + np.where(mean < .5, .44, -.44), 0, 1)
    colors = np.ones((len(segments),4), dtype=np.float32)
    colors[:,:3] = target[:,None]
    colors[:,3] = .7
    return np.repeat(colors, 2, axis=0)
