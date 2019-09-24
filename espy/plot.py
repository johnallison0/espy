# -*- coding: utf-8 -*-
"""
Created on Tue May 14 13:10:01 2019

@author: lau05219
"""

import itertools
import matplotlib.pyplot as plt
import numpy as np
from mpl_toolkits.mplot3d.art3d import Line3DCollection, Poly3DCollection
from wand.image import Image

from espy import get

# pylint: disable-msg=C0103


def set_axes_radius(ax, origin, radius):
    """Set axes radius."""
    ax.set_xlim3d([origin[0] - radius, origin[0] + radius])
    ax.set_ylim3d([origin[1] - radius, origin[1] + radius])
    ax.set_zlim3d([origin[2] - radius, origin[2] + radius])


def set_axes_equal(ax):
    """Make axes of 3D plot have equal scale so that spheres appear as spheres,
    cubes as cubes, etc..  This is one possible solution to Matplotlib's
    ax.set_aspect('equal') and ax.axis('equal') not working for 3D.

    Input
      ax: a matplotlib axis, e.g., as output from plt.gca().
    """

    limits = np.array([ax.get_xlim3d(), ax.get_ylim3d(), ax.get_zlim3d()])

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
    """Plotting a cube element at position pos."""
    if ax is not None:
        X, Y, Z, _, _, _ = cuboid_data(pos, size)
        ax.plot_surface(X, Y, Z, rstride=1, cstride=1, **kwargs)


def plot_predef_ents(vis, vertices):
    """Plot visual entities and mass geometry"""

    fig = plt.figure()
    axis = fig.gca(projection="3d")
    axis.set_aspect("equal")

    for ent in vis:
        plot_cuboid(pos=ent[0:3], size=ent[3:6], ax=axis, color="crimson", alpha=0.2)

    for vertices_i in vertices:
        plot_zone_surface(vertices_i, ax=axis)

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
    if ax is not None:
        ax.add_collection3d(surf_outline)
        if facecolour is not None:
            ax.add_collection3d(surf)


def plot_zone(geo_file, ax=None, show_roof=True):
    """Plot zone from surfaces

    Example:

    fig = plt.figure()
    ax = fig.gca(projection='3d')
    ax.set_aspect('equal')
    plot.plot_zone(geo_file, ax=ax)
    plot.set_axes_equal(ax)
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
        # Plot surface from vertex coordinates)
        if (geo["props"][i][1] == "CEIL" or geo["props"][i][1] == "SLOP") and not show_roof:
            print("not showing roof")
        else:
            if geo["props"][i][6] == "OPAQUE" and geo["props"][i][7] == "EXTERIOR":
                if "DOOR" in geo["props"][i][3] or "FRAME" in geo["props"][i][3]:
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


def plot_construction(con_data, vertices_surf, ax=None):
    """Plot 3D construction on matplotlib surface."""
    con_data.reverse()
    thickness = [x[3] for x in con_data]
    normal = get.calculate_normal(vertices_surf)
    start = 0
    for i, _ in enumerate(con_data):
        a4 = vertices_surf + [vertices_surf[0]]

        X = [
            # [v[0] for v in a1],
            # [v[0] for v in a2],
            [v[0] + (start + thickness[i]) * normal[0] for v in a4],
            [v[0] + start * normal[0] for v in a4],
        ]

        Y = [
            # [v[1] for v in a1],
            # [v[1] for v in a2],
            [v[1] + (start + thickness[i]) * normal[1] for v in a4],
            [v[1] + start * normal[1] for v in a4],
        ]

        Z = [
            # [v[2] for v in a1],
            # [v[2] for v in a2],
            [v[2] + (start + thickness[i]) * normal[2] for v in a4],
            [v[2] + start * normal[2] for v in a4],
        ]

        ax.plot_surface(np.array(X), np.array(Y), np.array(Z), rstride=1, cstride=1)

        start += thickness[i]


def construction_schematics(con_file, geo_file, figsize=(3.54, 2.655), savefig=False):
    """Plot 2D construction schematic.
    
    Args:
        con_file: ESP-r construction file.
        geo_file: ESP-r geometry file.
        figsize: Tuple (length, height) of figure in inches.
        savefig: boolean. If True exports figures to png files.
            Note that this calls ImageMagick to trim the whitespace
            from the image.
    """
    # TODO(j.allison): colour layers according to material type.
    #     This will be hard as the material name is not stored in any model file.
    #     Will have to look up the construction in the constr.db and extract the
    #     names. With the name extracted, will then have to look up the category
    #     in the material.db.
    geo = get.geometry(geo_file)
    con = get.constructions(con_file, geo_file)
    con_names = [x[5] for x in geo["props"]]
    thick_tot = [
        round(sum([x[3] for x in constr]), 3) for constr in con["layer_therm_props"]
    ]
    unique_cons = list(sorted(set(con_names)))
    y_constr = 500
    for constr in unique_cons:
        loc_con = con_names.index(constr)
        con_data_i = con["layer_therm_props"][loc_con]
        air_gap_props_i = con["air_gap_props"][loc_con]
        if air_gap_props_i is not None:
            idx_air_gaps_i = air_gap_props_i[0::2]
        else:
            idx_air_gaps_i = []
        dx = [0] + [x[3] for x in con_data_i]
        x_dat = [x * 1000 for x in list(itertools.accumulate(dx))]

        # plt.style.use('grayscale')
        fig, ax = plt.subplots(figsize=figsize, dpi=220)
        fig.canvas.set_window_title(constr)
        ax.vlines(x_dat, 0, y_constr, linewidth=0.5)
        for i, _ in enumerate(x_dat[0:-1]):
            layer = i + 1
            if i == 0:
                name = "Ext"
            elif i == len(con_data_i) - 1:
                name = "Int"
            else:
                name = i + 1
            ax.text(x_dat[i], y_constr + 10, name)
            if layer in idx_air_gaps_i:
                continue
            else:
                ax.fill_betweenx((0, y_constr), x_dat[i], x_dat[i + 1], alpha=0.4, color="grey")
        ax.set_aspect("equal")
        ax.set_xticks([0, max(x_dat)])
        ax.set_xlim(0 - 10, 1000 * max(thick_tot) + 10)
        ax.set_ylim(0, y_constr + 10)
        ax.yaxis.set_visible(False)
        ax.spines["left"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["top"].set_visible(False)
        ax.spines["bottom"].set_visible(False)
        plt.tight_layout()
        if savefig:
            plt.savefig(f"{constr}.png", bbox_inches="tight", pad_inches=0, dpi=220)
            with Image(filename=f"{constr}.png") as img:
                img.trim(color=None, fuzz=0)
                img.save(filename=f"{constr}.png")


def plot_zone_constructions(con_file, geo_file, ax=None):
    """Plot all zone constructions."""
    zone_geometry = get.geometry(geo_file)
    con = get.constructions(con_file, geo_file)
    layer_therm_props = con["layer_therm_props"]

    for i, _ in enumerate(zone_geometry["edges"]):
        con_data = layer_therm_props[i]
        surface = zone_geometry["edges"][i]
        # map vertex indices in edges list to x,y,z vertices
        vertices_surf_i = []
        for vertex in surface:
            vertices_surf_i.append(zone_geometry["vertices"][vertex - 1])
        plot_construction(con_data, vertices_surf_i, ax=ax)


def plot_building_component(geo_file, con_file, idx_surface, ax=None, show_roof=True):
    """Plot generic 3D building component.

    This function plots a 3D building component (wall, floor, roof etc.)
    from its surface geometry and construction data.

    The inside surface is plotted as white, while the external surface colour
    is dependent on the surface properties from the geometry file.

    vertices    list of x,y,z position vertices of the inside (zone-facing) surface
    """

    # TODO(j.allison): Create new figure and axes if none are provided

    # Read geometry file
    zone_geometry = get.geometry(geo_file)
    surface_props = zone_geometry["props"][idx_surface]

    # Get vertex numbers that comprise surface
    surface_edges = zone_geometry["edges"][idx_surface]

    # Get vertex positions that comprise surface
    vertices_surf = get.pos_from_vert_num_list(zone_geometry["vertices"], surface_edges)

    # Plot inside (zone-facing) surface
    if (surface_props[1] == "CEIL" or surface_props[1] == "SLOP") and not show_roof:
        pass
    else:
        if surface_props[6] == "OPAQUE":
            plot_zone_surface(vertices_surf, ax=ax, facecolour="w", alpha=None)
        else:
            plot_zone_surface(vertices_surf, ax=ax, facecolour="#008db0")

    # Plot construction layers
    con = get.constructions(con_file, geo_file)
    layer_therm_props = con["layer_therm_props"]
    con_data = layer_therm_props[idx_surface]
    if (surface_props[1] == "CEIL" or surface_props[1] == "SLOP") and not show_roof:
        pass
    else:
        plot_construction(con_data, vertices_surf, ax=ax)

    # -------------------------------------
    # Plot outer surface
    # -------------------------------------
    normal = get.calculate_normal(vertices_surf)
    # vertices_surf += [vertices_surf[0]]
    total_thickness = sum([x[3] for x in con_data])
    # Extend vertex position along surface normal by the total thickness
    x_pos = [v[0] + total_thickness * normal[0] for v in vertices_surf]
    y_pos = [v[1] + total_thickness * normal[1] for v in vertices_surf]
    z_pos = [v[2] + total_thickness * normal[2] for v in vertices_surf]
    # Restructure to surface vertices
    # Can probably do this in a zip list comprehension...
    vertices_surf_outer = []
    for i, _ in enumerate(vertices_surf):
        vertices_surf_outer.append([x_pos[i], y_pos[i], z_pos[i]])
    if (surface_props[1] == "CEIL" or surface_props[1] == "SLOP") and not show_roof:
        pass
    else:
        if surface_props[6] == "OPAQUE" and surface_props[7] == "EXTERIOR":
            if "DOOR" in surface_props[3] or "FRAME" in surface_props[3]:
                # door or frame
                plot_zone_surface(vertices_surf_outer, ax=ax, facecolour="#c19a6b", alpha=None)
            else:
                # default grey surface
                plot_zone_surface(vertices_surf_outer, ax=ax, facecolour="#afacac", alpha=None)
        elif surface_props[6] == "OPAQUE" and surface_props[7] == "ANOTHER":
            if "DOOR" in surface_props[3]:
                # door
                plot_zone_surface(vertices_surf_outer, ax=ax, facecolour="#f5f2d0", alpha=None)
            else:
                # default 25% lighter surface
                plot_zone_surface(vertices_surf_outer, ax=ax, facecolour="#ffffff", alpha=None)
        elif surface_props[6] == "OPAQUE" and surface_props[7] == "SIMILAR":
            plot_zone_surface(vertices_surf_outer, ax=ax, facecolour="#d8e4bc", alpha=None)
        elif surface_props[6] == "OPAQUE" and surface_props[7] == "GROUND":
            plot_zone_surface(vertices_surf_outer, ax=ax, facecolour="#654321", alpha=None)
        else:
            # Transparent surfaces
            plot_zone_surface(vertices_surf_outer, ax=ax, facecolour="#008db0")
