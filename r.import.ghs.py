#!/usr/bin/env python3
############################################################################
#
# MODULE:       r.import.ghs
# AUTHOR(S):    Guido Riembauer
# PURPOSE:      Downloads and imports Global Human Settlement data (provided by the JRC, European Commission)
#
# COPYRIGHT:    (C) 2021-2022 by mundialis GmbH & Co. KG and the GRASS Development Team
#
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
############################################################################

# %module
# % description: Downloads and imports Global Human Settlement data (provided by the JRC, European Commission).
# % keyword: raster
# % keyword: import
# % keyword: land cover
# % keyword: classification
# %end

# %option G_OPT_R_OUTPUT
# % key: ghs_built
# % required: no
# % label: Output raster map name for GHS-BUILT map
# %end

# %option G_OPT_R_OUTPUT
# % key: ghs_built_s1
# % required: no
# % label: Output raster map name for GHS-BUILT-S1 map
# %end

# %option G_OPT_R_OUTPUT
# % key: ghs_built_s2
# % required: no
# % label: Output raster map name for GHS-BUILT-S2 map
# %end

# %option G_OPT_M_DIR
# % key: directory
# % required: no
# % multiple: no
# % label: Directory path where to download and temporarily store the data. If not set the data will be downloaded to a temporary directory. The downloaded data will be removed after the import
# %end

# %option G_OPT_MEMORYMB
# %end

# %flag
# % key: r
# % description: Use region resolution instead of input resolution
# %end

# %rules
# % required: ghs_built,ghs_built_s1,ghs_built_s2
# %end

import atexit
import os
import psutil
import shutil
import sys
from urllib.parse import urlparse
import wget
from zipfile import ZipFile
import grass.script as grass

rm_files = []
rm_folders = []
rm_rasters = []
rm_vectors = []
TMPLOC = None
SRCGISRC = None
TGTGISRC = None
GISDBASE = None

sys.path.insert(1, os.path.join(os.path.dirname(sys.path[0]), "etc", "r.import.ghs"))


def cleanup():
    grass.message(_("Cleaning up..."))
    nuldev = open(os.devnull, "w")
    kwargs = {"flags": "f", "quiet": True, "stderr": nuldev}
    if TGTGISRC:
        os.environ["GISRC"] = str(TGTGISRC)
    # remove temp location
    if TMPLOC:
        grass.try_rmdir(os.path.join(GISDBASE, TMPLOC))
    if SRCGISRC:
        grass.try_remove(SRCGISRC)
    for rmv in rm_vectors:
        if grass.find_file(name=rmv, element="vector")["file"]:
            grass.run_command("g.remove", type="vector", name=rmv, **kwargs)
    for rmrast in rm_rasters:
        if grass.find_file(name=rmrast, element="raster")["file"]:
            grass.run_command("g.remove", type="raster", name=rmrast, **kwargs)
    for rmfile in rm_files:
        try:
            os.remove(rmfile)
        except Exception as e:
            grass.warning(_("Cannot remove file <%s>: %s" % (rmfile, e)))
    for folder in rm_folders:
        if os.path.isdir(folder):
            try:
                shutil.rmtree(folder)
            except Exception as e:
                grass.warning(_("Cannot remove dir <%s>: %s" % (folder, e)))


def freeRAM(unit, percent=100):
    """The function gives the amount of the percentages of the installed RAM.
    Args:
        unit(string): 'GB' or 'MB'
        percent(int): number of percent which shoud be used of the free RAM
                      default 100%
    Returns:
        memory_MB_percent/memory_GB_percent(int): percent of the free RAM in
                                                  MB or GB

    """
    # use psutil cause of alpine busybox free version for RAM/SWAP usage
    mem_available = psutil.virtual_memory().available
    swap_free = psutil.swap_memory().free
    memory_GB = (mem_available + swap_free) / 1024.0 ** 3
    memory_MB = (mem_available + swap_free) / 1024.0 ** 2

    if unit == "MB":
        memory_MB_percent = memory_MB * percent / 100.0
        return int(round(memory_MB_percent))
    elif unit == "GB":
        memory_GB_percent = memory_GB * percent / 100.0
        return int(round(memory_GB_percent))
    else:
        grass.fatal(_("Memory unit <%s> not supported" % unit))


def test_memory():
    # check memory
    memory = int(options["memory"])
    free_ram = freeRAM("MB", 100)
    if free_ram < memory:
        grass.warning(_("Using %d MB but only %d MB RAM available." % (memory, free_ram)))
        options["memory"] = free_ram
        grass.warning("Set used memory to %d MB." % (options["memory"]))


def createTMPlocation(epsg=4326):
    global TMPLOC, SRCGISRC
    SRCGISRC = grass.tempfile()
    TMPLOC = "temp_import_location_" + str(os.getpid())
    f = open(SRCGISRC, "w")
    f.write("MAPSET: PERMANENT\n")
    f.write("GISDBASE: %s\n" % GISDBASE)
    f.write("LOCATION_NAME: %s\n" % TMPLOC)
    f.write("GUI: text\n")
    f.close()

    proj_test = grass.parse_command("g.proj", flags="g")
    if "epsg" in proj_test:
        epsg_arg = {"epsg": epsg}
    else:
        epsg_arg = {"srid": "EPSG:{}".format(epsg)}
    # create temp location from input without import
    grass.verbose(_("Creating temporary location with EPSG:%d...") % epsg)
    grass.run_command("g.proj", flags="c", location=TMPLOC, quiet=True, **epsg_arg)

    # switch to temp location
    os.environ["GISRC"] = str(SRCGISRC)
    proj = grass.parse_command("g.proj", flags="g")
    if "epsg" in proj:
        new_epsg = proj["epsg"]
    else:
        new_epsg = proj["srid"].split("EPSG:")[1]
    if new_epsg != str(epsg):
        grass.fatal(_("Creation of temporary location failed!"))


def get_actual_location():
    global TGTGISRC, GISDBASE
    # get actual location, mapset, ...
    grassenv = grass.gisenv()
    tgtloc = grassenv["LOCATION_NAME"]
    tgtmapset = grassenv["MAPSET"]
    GISDBASE = grassenv["GISDBASE"]
    TGTGISRC = os.environ["GISRC"]
    return tgtloc, tgtmapset


def get_region_vect(num):
    region_vect = "tmp_region_vect_{}_{}".format(num, os.getpid())
    rm_vectors.append(region_vect)
    grass.run_command("v.in.region", output=region_vect, quiet=True)
    return region_vect


def get_tiles(grid_vect, region_vect):
    selected_tmp = "selected_tiles_{}".format(os.getpid())
    rm_vectors.append(selected_tmp)
    grass.run_command(
        "v.select",
        ainput=grid_vect,
        binput=region_vect,
        output=selected_tmp,
        operator="overlap",
        quiet=True,
    )
    resulting_tiles = list(
        grass.parse_command(
            "v.db.select", map=selected_tmp, separator="pipe", quiet=True
        ).keys()
    )
    urls = [item.split("|")[-1] for item in resulting_tiles[1:]]
    return urls


def get_tiles_ghs_s2(dir):
    global rm_files, rm_vectors
    # download tilegrid
    grass.message(_("\nDownloading GHS-S2 tilegrid..."))
    grid_url = (
        "https://ghsl.jrc.ec.europa.eu/documents/"
        "GHS_BUILT_S2comp2018_GLOBE_R2020A_tile_schema.zip"
    )
    localshp = download_onefile(grid_url, dir, format="shp")
    grid_tmp = "tmp_ghs_s2_grid_{}".format(os.getpid())
    rm_vectors.append(grid_tmp)
    grass.run_command(
        "v.import", input=localshp, output=grid_tmp, extent="region", quiet=True
    )
    region_vect = get_region_vect(1)
    urls = get_tiles(grid_tmp, region_vect)
    return urls


def get_tiles_ghs_built(dir):
    # since the tiling here is in 3857 where reprojection can run into issues,
    # instead we reproject the current region to 3857 and check overlap in
    # a temp location
    from tindex_ghs_built_geojson import tindex_str

    # get actual location, mapset, ...
    tgtloc, tgtmapset = get_actual_location()
    region_vect = get_region_vect(2)
    # create temporary location with epsg:3857
    createTMPlocation(3857)
    # import the tile index
    index_vectmap = "tindex_vectmap_{}".format(os.getpid())
    grass.run_command(
        "v.in.geojson", input=tindex_str, output=index_vectmap, quiet=True
    )
    # get the saved region
    grass.run_command(
        "v.proj",
        location=tgtloc,
        mapset=tgtmapset,
        input=region_vect,
        output=region_vect,
        quiet=True,
    )
    tiles = get_tiles(index_vectmap, region_vect)
    # switch to target location
    os.environ["GISRC"] = str(TGTGISRC)
    return tiles


def download_wget(url, local_path):
    try:
        wget.download(url, local_path)
        return 0
    except Exception as e:
        grass.fatal(_("There was a problem downloading {}: {}").format(url, e))


def download_onefile(url, dir, format="tif"):
    global rm_folders, rm_files
    basepath = urlparse(url).path
    zip_name = os.path.basename(basepath)
    base_filename = os.path.splitext(zip_name)[0]
    ext_name = "{}.{}".format(base_filename, format)
    local_path_zip = os.path.join(dir, zip_name)
    rm_files.append(local_path_zip)
    download_wget(url, local_path_zip)
    local_path_unzipped = os.path.join(dir, "{}_unzipped".format(base_filename))
    rm_folders.append(local_path_unzipped)
    with ZipFile(local_path_zip, "r") as zipObj:
        zipObj.extractall(local_path_unzipped)
    return os.path.join(local_path_unzipped, ext_name)


def main():

    global rm_rasters, rm_folders, rm_files

    if options["directory"]:
        download_dir = options["directory"]
        if not os.path.isdir(download_dir):
            os.makedirs(download_dir)
    else:
        download_dir = grass.tempdir()
        rm_folders.append(download_dir)

    if options["ghs_built"]:
        if not grass.find_program("v.in.geojson", "--help"):
            grass.fatal(
                _(
                    "The 'v.in.geojson' module was not found, install"
                    "it first: \n g.extension v.in.geojson url="
                    "path/to/addon"
                )
            )

    downloaded_files = []
    if options["ghs_built_s1"]:
        # just one file exists
        grass.message(
            _(
                "\nDownloading GHS built-up grid derived from"
                "Sentinel-1 (GHS-BUILT-S1)"
            )
        )
        ghs_built_s1_url = (
            "https://jeodpp.jrc.ec.europa.eu/ftp/jrc-opendata/"
            "GHSL/GHS_BUILT_S1NODSM_GLOBE_R2018A/GHS_BUILT_"
            "S1NODSM_GLOBE_R2018A_3857_20/V1-0/GHS_BUILT"
            "_S1NODSM_GLOBE_R2018A_3857_20_V1_0.zip"
        )
        # special case, filepath for this file is different:
        ghs_built_s1_path_1 = download_onefile(ghs_built_s1_url, download_dir)
        unzipped_dir_ghs_s1 = ghs_built_s1_path_1.split(
            os.path.basename(ghs_built_s1_path_1)
        )[0]
        remaining_path = (
            "GHS_BUILT_S1NODSM_GLOBE_R2018A/GHS_BUILT_S1NODSM"
            "_GLOBE_R2018A_3857_20/V1-0/GHS_BUILT_S1NODSM_GLOBE"
            "_R2018A_3857_20_V1_0.vrt"
        )
        ghs_built_s1_path = os.path.join(unzipped_dir_ghs_s1, remaining_path)
        downloaded_files.append((ghs_built_s1_path, options["ghs_built_s1"]))

    s2_tiles = []
    if options["ghs_built_s2"]:
        # tiling exists and is used
        s2_urls = get_tiles_ghs_s2(download_dir)
        for idx, s2_url in enumerate(s2_urls):
            grass.message(
                _(
                    "\nDownloading {} of {} required tiles of"
                    " Sentinel-2 derived GHS built-up grid"
                ).format(idx + 1, len(s2_urls))
            )
            filename = "tmp_s2_tile_{}_{}.tif".format(os.getpid(), idx)
            local_filepath = os.path.join(download_dir, filename)
            rm_files.append(local_filepath)
            download_wget(s2_url, local_filepath)
            downloaded_files.append((local_filepath, options["ghs_built_s2"]))
            s2_tiles.append(local_filepath)

    ghs_tiles = []
    if options["ghs_built"]:
        # tiling exists and is used
        ghs_built_tiles = get_tiles_ghs_built(download_dir)
        base_url = (
            "https://jeodpp.jrc.ec.europa.eu/ftp/jrc-opendata/GHSL/"
            "GHS_BUILT_LDSMT_GLOBE_R2018A/GHS_BUILT_LDSMT_GLOBE_R2018A"
            "_3857_30/V2-0/tiles/"
        )
        for idx, tile in enumerate(ghs_built_tiles):
            grass.message(
                _(
                    "\nDownloading {} of {} required tiles of "
                    "Landsat derived GHS built-up grid"
                ).format(idx + 1, len(ghs_built_tiles))
            )
            ghs_url = os.path.join(base_url, "{}.zip".format(tile))
            ghs_built_path = download_onefile(ghs_url, download_dir)
            downloaded_files.append((ghs_built_path, options["ghs_built"]))
            ghs_tiles.append(ghs_built_path)

    # import all
    grass.message(_("\nImporting..."))
    test_memory()
    patch_s2 = True if len(s2_tiles) > 1 else False
    patch_built = True if len(ghs_tiles) > 1 else False
    maps_to_patch_s2 = []
    maps_to_patch_built = []
    for idx, file in enumerate(downloaded_files):
        if file[0] in s2_tiles and patch_s2 is True:
            grassname = "tmp_ghs_raster_{}_{}".format(os.getpid(), idx + 1)
            rm_rasters.append(grassname)
            maps_to_patch_s2.append(grassname)
        elif file[0] in ghs_tiles and patch_built is True:
            grassname = "tmp_ghs_raster_{}_{}".format(os.getpid(), idx + 1)
            rm_rasters.append(grassname)
            maps_to_patch_built.append(grassname)
        else:
            grassname = file[1]
        import_kwargs = {
            "input": file[0],
            "output": grassname,
            "memory": options["memory"],
            "extent": "region",
        }
        if flags["r"]:
            import_kwargs["resolution"] = "region"
            import_kwargs["resample"] = "nearest"
        grass.run_command("r.import", **import_kwargs, quiet=True)
    if patch_s2:
        grass.run_command(
            "r.patch",
            input=maps_to_patch_s2,
            output=options["ghs_built_s2"],
            quiet=True,
        )
    if patch_built:
        grass.run_command(
            "r.patch",
            input=maps_to_patch_built,
            output=options["ghs_built"],
            quiet=True,
        )
    return 0


if __name__ == "__main__":
    options, flags = grass.parser()
    atexit.register(cleanup)
    sys.exit(main())
