# -*- coding: utf-8 -*-
"""
Created on Tue May 14 13:10:01 2019

@author: lau05219
"""

import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection, Line3DCollection


def set_axes_equal(ax):
    '''Make axes of 3D plot have equal scale so that spheres appear as spheres,
    cubes as cubes, etc..  This is one possible solution to Matplotlib's
    ax.set_aspect('equal') and ax.axis('equal') not working for 3D.

    Input
      ax: a matplotlib axis, e.g., as output from plt.gca().
    '''

    x_limits = ax.get_xlim3d()
    y_limits = ax.get_ylim3d()
    z_limits = ax.get_zlim3d()

    x_range = abs(x_limits[1] - x_limits[0])
    x_middle = np.mean(x_limits)
    y_range = abs(y_limits[1] - y_limits[0])
    y_middle = np.mean(y_limits)
    z_range = abs(z_limits[1] - z_limits[0])
    z_middle = np.mean(z_limits)

    # The plot bounding box is a sphere in the sense of the infinity
    # norm, hence I call half the max range the plot radius.
    plot_radius = 0.5 * max([x_range, y_range, z_range])

    ax.set_xlim3d([x_middle - plot_radius, x_middle + plot_radius])
    ax.set_ylim3d([y_middle - plot_radius, y_middle + plot_radius])
    ax.set_zlim3d([z_middle - plot_radius, z_middle + plot_radius])


def cuboid_data(o, size=(1,1,1)):
    # code taken from
    # https://stackoverflow.com/a/35978146/4124317
    # suppose axis direction: x: to left; y: to inside; z: to upper
    # get the length, width, and height
    l, w, h = size
    
    areas = [l*w, l*h, w*h]
    idx_max = np.argmax(areas)
    if idx_max == 0:
        area_cross_vertices = [[o[0], o[1], o[2]+h/2], [o[0] + l, o[1], o[2]+h/2], [o[0] + l, o[1]+w, o[2]+h/2], [o[0], o[1]+w, o[2]+h/2]]
    elif idx_max == 1:
        area_cross_vertices = [[o[0], o[1] + w/2, o[2]], [o[0]+l, o[1]+w/2, o[2]], [o[0]+l, o[1]+w/2, o[2]+h], [o[0], o[1]+w/2, o[2]+h]]
    elif idx_max == 2:
        area_cross_vertices = [[o[0]+l/2, o[1]+w, o[2]], [o[0]+l/2, o[1], o[2]], [o[0]+l/2, o[1], o[2]+h], [o[0]+l/2, o[1]+w, o[2]+h]]
    else:
        print("Cannot find cross-section of cuboid")
    
    # Thickness of construction
    d = l*w*h/np.max(areas)
    
    x = [[o[0], o[0] + l, o[0] + l, o[0], o[0]],  
         [o[0], o[0] + l, o[0] + l, o[0], o[0]],  
         [o[0], o[0] + l, o[0] + l, o[0], o[0]],  
         [o[0], o[0] + l, o[0] + l, o[0], o[0]]]  
    y = [[o[1], o[1], o[1] + w, o[1] + w, o[1]],  
         [o[1], o[1], o[1] + w, o[1] + w, o[1]],  
         [o[1], o[1], o[1], o[1], o[1]],          
         [o[1] + w, o[1] + w, o[1] + w, o[1] + w, o[1] + w]]   
    z = [[o[2], o[2], o[2], o[2], o[2]],                       
         [o[2] + h, o[2] + h, o[2] + h, o[2] + h, o[2] + h],   
         [o[2], o[2], o[2] + h, o[2] + h, o[2]],               
         [o[2], o[2], o[2] + h, o[2] + h, o[2]]]               
    return np.array(x), np.array(y), np.array(z), area_cross_vertices,l*w*h,d


def plot_cuboid(pos=(0,0,0), size=(1,1,1), ax=None,**kwargs):
    # Plotting a cube element at position pos
    if ax !=None:
        X, Y, Z, _, _, _ = cuboid_data( pos, size )
        ax.plot_surface(X, Y, Z, rstride=1, cstride=1, **kwargs)


def plot_predef_ents(vis, vertices):
    '''Plot visual entities and mass geometry'''

    fig = plt.figure()
    axis = fig.gca(projection="3d")
    axis.set_aspect("equal")
    for i, ent in enumerate(vis):
        plot_cuboid(pos=ent[0:3], size=ent[3:6], ax=axis, color="crimson", alpha=0.2)
        plot_zone_surface(vertices[i], ax=axis)
    set_axes_equal(axis)
    plt.axis('off')
    plt.grid(b=None)
    plt.show()


def plot_zone_surface(vertices, ax=None, facecolour=None, alpha=0.2):
    '''Plots a surface on the current axes from a list of vertices
    '''
    # Close path
    vertices = vertices + [vertices[0]]
    # Extract x,y,z
    x = [vertex[0] for vertex in vertices]
    y = [vertex[1] for vertex in vertices]
    z = [vertex[2] for vertex in vertices]
    verts = [list(zip(x, y, z))]
    if facecolour is None:
        surf_outline = Line3DCollection(verts, colors='k')
    else:
        if alpha is not None:
            surf = Poly3DCollection(verts, alpha=alpha)
        else:
            surf = Poly3DCollection(verts)
        surf.set_facecolor(facecolour)
        surf_outline = Line3DCollection(verts, colors='k')
    # Add to axes
    if ax != None:
        ax.add_collection3d(surf_outline)
        if facecolour is not None:
            ax.add_collection3d(surf)