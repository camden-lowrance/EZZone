__author__ = 'camden'
from shapely.geometry import MultiPolygon, JOIN_STYLE
from shapely.ops import cascaded_union
import math
import numpy as np

def small_polys(multip, area, multip2):
    """
    Helper function for simplify_polys
    :param multip:
    :param area:
    :param multip2:
    :return:
    """
    small_p = []
    try:
        for p in multip:
            if p.area < area and p.intersects(multip2):
                try:
                    for p2 in multip2:
                        if p2.area > area and p.intersects(p2):
                            small_p.append(p)
                except TypeError:
                    if multip2.area > area:
                        small_p.append(p)
    except TypeError:
        if multip.area < area and multip.intersects(multip2):
            try:
                for p2 in multip2:
                    if p2.area > area and multip.intersects(p2):
                        small_p.append(multip)
            except TypeError:
                if multip2.area > area:
                    small_p.append(multip)
    return MultiPolygon(small_p)


def simplify_polys_up(polys, spacing):
    # input list of polygons/multipolygons and spacing attribute used to produce polygons
    # area
    area = math.floor(spacing ** 2)
    med = np.median([i for i,p in enumerate(polys)])
    for idx, multip in enumerate(polys):
        if idx <= med:
            # identify polygons in j that are below the area threshold and intersect with the next multipolygon
            try:
                area_inters = small_polys(multip, area, polys[idx + 1])
            except IndexError:
                break
            if area_inters.area > 0:
                polys[idx] = polys[idx].difference(area_inters)
                polys[idx + 1] = cascaded_union([polys[idx + 1], area_inters])
        else:
            break
    return polys

def simplify_polys_up_two(polys, spacing):
    # input list of polygons/multipolygons and spacing attribute used to produce polygons
    # area
    area = math.floor(spacing ** 2)
    med = np.median([i for i,p in enumerate(polys)])
    for idx, multip in enumerate(polys):
        if idx <= med:
            # identify polygons in j that are below the area threshold and intersect with the next multipolygon
            try:
                area_inters = small_polys(multip, area, polys[idx + 2])
            except IndexError:
                break
            if area_inters.area > 0:
                polys[idx] = polys[idx].difference(area_inters)
                polys[idx + 2] = cascaded_union([polys[idx + 2], area_inters])
        else:
            break
    return polys


def simplify_polys_down(polys, spacing):
    # input list of polygons/multipolygons and spacing attribute used to produce polygons
    # area
    area = math.floor(spacing ** 2)
    med = np.median([i for i,p in enumerate(polys)])
    for idx, multip in reversed(list(enumerate(polys))):
        if idx >= med:
            # identify polygons in j that are below the area threshold and intersect with the next multipolygon
            try:
                area_inters = small_polys(multip, area, polys[idx - 1])
            except IndexError:
                break
            if area_inters.area > 0:
                polys[idx] = polys[idx].difference(area_inters)
                polys[idx - 1] = cascaded_union([polys[idx - 1], area_inters])
        else:
            break
    return polys

def simplify_polys_down_two(polys, spacing):
    # input list of polygons/multipolygons and spacing attribute used to produce polygons
    # area
    area = math.floor(spacing ** 2)
    med = np.median([i for i,p in enumerate(polys)])
    for idx, multip in reversed(list(enumerate(polys))):
        if idx >= med:
            # identify polygons in j that are below the area threshold and intersect with the next multipolygon
            try:
                area_inters = small_polys(multip, area, polys[idx - 2])
            except IndexError:
                break
            if area_inters.area > 0:
                polys[idx] = polys[idx].difference(area_inters)
                polys[idx - 2] = cascaded_union([polys[idx - 2], area_inters])
    return polys

def remove_sliver(poly):
    eps = .001
    return poly.buffer(eps, 1, join_style=JOIN_STYLE.mitre).buffer(-eps, 1, join_style=JOIN_STYLE.mitre)

def simplify_polys(polys, spacing, smooth):
    for sm in range(1, smooth + 1):
        polys = simplify_polys_up(polys, (sm * spacing))
        polys = simplify_polys_down(polys, (sm * spacing))
    for sm in range(1, smooth + 1):
        polys = simplify_polys_up_two(polys, (sm * spacing))
        polys = simplify_polys_down_two(polys, (sm * spacing))
    polys = [remove_sliver(poly) for poly in polys]
    return polys