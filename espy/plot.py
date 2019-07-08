# -*- coding: utf-8 -*-
"""
Created on Tue May 14 13:10:01 2019

@author: lau05219
"""

import matplotlib.pyplot as plt
import numpy as np
from mpl_toolkits.mplot3d.art3d import Line3DCollection, Poly3DCollection

from espy import get


def set_axes_radius(ax, origin, radius):
    ax.set_xlim3d([origin[0] - radius, origin[0] + radius])
    ax.set_ylim3d([origin[1] - radius, origin[1] + radius])
    ax.set_zlim3d([origin[2] - radius, origin[2] + radius])


def set_axes_equal(ax):
    '''Make axes of 3D plot have equal scale so that spheres appear as spheres,
    cubes as cubes, etc..  This is one possible solution to Matplotlib's
    ax.set_aspect('equal') and ax.axis('equal') not working for 3D.

    Input
      ax: a matplotlib axis, e.g., as output from plt.gca().
    '''

    limits = np.array([
        ax.get_xlim3d(),
        ax.get_ylim3d(),
        ax.get_zlim3d(),
    ])

    origin = np.mean(limits, axis=1)
    radius = 0.5 * np.max(np.abs(limits[:, 1] - limits[:, 0]))
    set_axes_radius(ax, origin, radius)


def cuboid_data(o, size=(1, 1, 1)):
    """Calculate cuboid data from origin and size."""
    # code taken from
    # https://stackoverflow.com/a/35978146/4124317
    # suppose axis direction: x: to left; y: to inside; z: to upper
    # get the length, width, and height
    l, w, h = size

    areas = [l * w, l * h, w * h]
    idx_max = np.argmax(areas)
    if idx_max == 0:
        area_cross_vertices = [
            [o[0], o[1], o[2] + h / 2],
            [o[0] + l, o[1], o[2] + h / 2],
            [o[0] + l, o[1] + w, o[2] + h / 2],
            [o[0], o[1] + w, o[2] + h / 2],
        ]
    elif idx_max == 1:
        area_cross_vertices = [
            [o[0], o[1] + w / 2, o[2]],
            [o[0] + l, o[1] + w / 2, o[2]],
            [o[0] + l, o[1] + w / 2, o[2] + h],
            [o[0], o[1] + w / 2, o[2] + h],
        ]
    elif idx_max == 2:
        area_cross_vertices = [
            [o[0] + l / 2, o[1] + w, o[2]],
            [o[0] + l / 2, o[1], o[2]],
            [o[0] + l / 2, o[1], o[2] + h],
            [o[0] + l / 2, o[1] + w, o[2] + h],
        ]
    else:
        print("Cannot find cross-section of cuboid")

    # Thickness of construction
    d = l * w * h / np.max(areas)

    x = [
        [o[0], o[0] + l, o[0] + l, o[0], o[0]],
        [o[0], o[0] + l, o[0] + l, o[0], o[0]],
        [o[0], o[0] + l, o[0] + l, o[0], o[0]],
        [o[0], o[0] + l, o[0] + l, o[0], o[0]],
    ]
    y = [
        [o[1], o[1], o[1] + w, o[1] + w, o[1]],
        [o[1], o[1], o[1] + w, o[1] + w, o[1]],
        [o[1], o[1], o[1], o[1], o[1]],
        [o[1] + w, o[1] + w, o[1] + w, o[1] + w, o[1] + w],
    ]
    z = [
        [o[2], o[2], o[2], o[2], o[2]],
        [o[2] + h, o[2] + h, o[2] + h, o[2] + h, o[2] + h],
        [o[2], o[2], o[2] + h, o[2] + h, o[2]],
        [o[2], o[2], o[2] + h, o[2] + h, o[2]],
    ]
    return np.array(x), np.array(y), np.array(z), area_cross_vertices, l * w * h, d


def plot_cuboid(pos=(0, 0, 0), size=(1, 1, 1), ax=None, **kwargs):
    # Plotting a cube element at position pos
    if ax != None:
        X, Y, Z, _, _, _ = cuboid_data(pos, size)
        ax.plot_surface(X, Y, Z, rstride=1, cstride=1, **kwargs)


def plot_predef_ents(vis, vertices):
    """Plot visual entities and mass geometry"""

    fig = plt.figure()
    axis = fig.gca(projection="3d")
    axis.set_aspect("equal")
    for i, ent in enumerate(vis):
        plot_cuboid(pos=ent[0:3], size=ent[3:6], ax=axis, color="crimson", alpha=0.2)
        plot_zone_surface(vertices[i], ax=axis)
    set_axes_equal(axis)
    plt.axis("off")
    plt.grid(b=None)
    plt.show()


def plot_zone_surface(vertices, ax=None, facecolour=None, alpha=0.2):
    """Plots a surface on the current axes from a list of vertices
    """
    # Close path
    vertices = vertices + [vertices[0]]
    # Extract x,y,z
    x = [vertex[0] for vertex in vertices]
    y = [vertex[1] for vertex in vertices]
    z = [vertex[2] for vertex in vertices]
    verts = [list(zip(x, y, z))]
    if facecolour is None:
        surf_outline = Line3DCollection(verts, colors="k")
    else:
        if alpha is not None:
            surf = Poly3DCollection(verts, alpha=alpha)
        else:
            surf = Poly3DCollection(verts)
        surf.set_facecolor(facecolour)
        surf_outline = Line3DCollection(verts, colors="k")
    # Add to axes
    if ax != None:
        ax.add_collection3d(surf_outline)
        if facecolour is not None:
            ax.add_collection3d(surf)


def plot_zone(geo_file, ax=None, show_roof=True):
    """Plot zone from surfaces
    
    Example:

    fig = plt.figure()
    ax = fig.gca(projection='3d')
    ax.set_aspect('equal')         # important!

    espy.plot_zone(...)

    set_axes_equal(ax)             # important!
    plt.show()

    """
    geo = get.geometry(geo_file)
    vertices = geo["vertices"]
    edges = geo["edges"]

    for i, surface in enumerate(edges):
        # Translate vertex no. to vertex x,y,z pos.
        vs = []
        for vertex in surface:
            vs.append(vertices[vertex - 1])
        # Plot surface from vertex coordinates
        if (geo["props"][i][1] == "CEIL" or geo["props"][i][1] == "SLOP") and not show_roof:
            print("not showing roof")
        else:
            if geo["props"][i][6] == "OPAQUE" and geo["props"][i][7] == "EXTERIOR":
                if "DOOR" in geo["props"][i][3] or "FRAME" in geo["props"][i][3]:
                    # door or frame
                    plot_zone_surface(vs, ax=ax, facecolour="#c19a6b", alpha=None)
                else:
                    # default grey surface
                    plot_zone_surface(vs, ax=ax, facecolour="#afacac", alpha=None)
            elif geo["props"][i][6] == "OPAQUE" and geo["props"][i][7] == "ANOTHER":
                if "DOOR" in geo["props"][i][3]:
                    # door
                    plot_zone_surface(vs, ax=ax, facecolour="#f5f2d0", alpha=None)
                else:
                    # default 25% lighter surface
                    plot_zone_surface(vs, ax=ax, facecolour="#ffffff", alpha=None)
            elif geo["props"][i][6] == "OPAQUE" and geo["props"][i][7] == "SIMILAR":
                # opaque, similar
                plot_zone_surface(vs, ax=ax, facecolour="#d8e4bc", alpha=None)
            elif geo["props"][i][6] == "OPAQUE" and geo["props"][i][7] == "GROUND":
                plot_zone_surface(vs, ax=ax, facecolour="#654321", alpha=None)
            else:
                # Transparent surfaces
                plot_zone_surface(vs, ax=ax, facecolour="#008db0")
