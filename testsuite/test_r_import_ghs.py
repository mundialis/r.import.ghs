#!/usr/bin/env python3
############################################################################
#
# MODULE:       r.import.ghs test
# AUTHOR(S):    Guido Riembauer
# PURPOSE:      Tests r.import.ghs using actinia-test-assets.
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

import os

from grass.gunittest.case import TestCase
from grass.gunittest.main import test
from grass.gunittest.gmodules import SimpleModule
import grass.script as grass


class TestRImportGHS(TestCase):
    pid_str = str(os.getpid())
    old_region = "saved_region_{}".format(pid_str)
    ref_map_small = "landclass96"
    ref_map_large = "boundary_county_500m"
    ghs_built_map = "ghs_built_map"
    ghs_built_s1_map = "ghs_built_s1_map"
    ghs_built_s2_map = "ghs_built_s2_map"

    @classmethod
    def setUpClass(self):
        """Ensures expected computational region and generated data"""
        grass.run_command("g.region", save=self.old_region)

    @classmethod
    def tearDownClass(self):
        """Remove the temporary region and generated data"""
        grass.run_command("g.region", region=self.old_region)

    def tearDown(self):
        """Remove the outputs created
        This is executed after each test run.
        """
        for rast in [self.ghs_built_map, self.ghs_built_s1_map, self.ghs_built_s2_map]:
            self.runModule("g.remove", type="raster", name=rast, flags="f")

    def test_single_tile_ghs_built_import(self):
        """Test if ghs_built/ghs_built_s2 are imported
        successfully for a small area (= single tile)"""
        grass.run_command("g.region", raster=self.ref_map_small)
        ghs_built = SimpleModule(
            "r.import.ghs",
            ghs_built=self.ghs_built_map,
            ghs_built_s2=self.ghs_built_s2_map,
        )
        self.assertModule(ghs_built)
        self.assertRasterExists(self.ghs_built_map)
        self.assertRasterExists(self.ghs_built_s2_map)
        # test that the output has certain statistics
        stats1 = grass.parse_command("r.univar", map=self.ghs_built_map, flags="g")
        stats2 = grass.parse_command("r.univar", map=self.ghs_built_s2_map, flags="g")
        ref_dict1 = {
            "min": "1",
            "n": "249324",
            "null_cells": "0",
            "cells": "249324",
            "max": "6",
            "range": "5",
            "mean": "3.05373730567454",
            "mean_of_abs": "3.05373730567454",
            "stddev": "1.57039503131324",
            "variance": "2.46614055437331",
            "coeff_var": "51.4253478318219",
            "sum": "761370",
        }
        ref_dict2 = {
            "n": "249324",
            "null_cells": "0",
            "cells": "249324",
            "min": "0",
            "max": "99",
            "range": "99",
            "mean": "15.1718446679822",
            "mean_of_abs": "15.1718446679822",
            "stddev": "24.3404721662376",
            "variance": "592.458585275386",
            "coeff_var": "160.431857159758",
            "sum": "3782705",
        }
        self.assertEqual(
            stats1,
            ref_dict1,
            (
                "The imported raster statistics of {}" "do not match the reference"
            ).format(self.ghs_built_map),
        )
        self.assertEqual(
            stats2,
            ref_dict2,
            (
                "The imported raster statistics of {}" "do not match the reference"
            ).format(self.ghs_built_s2_map),
        )

    def test_multi_tiles_ghs_built_import(self):
        """Test if ghs_built/ghs_built_s2 are imported
        successfully for a large area (=download of several tiles)"""
        grass.run_command("g.region", raster=self.ref_map_large, res=10, grow=-10000)
        ghs_built = SimpleModule(
            "r.import.ghs",
            ghs_built=self.ghs_built_map,
            ghs_built_s2=self.ghs_built_s2_map,
        )
        self.assertModule(ghs_built)
        self.assertRasterExists(self.ghs_built_map)
        self.assertRasterExists(self.ghs_built_s2_map)
        # test that the output has certain statistics
        stats1 = grass.parse_command("r.univar", map=self.ghs_built_map, flags="g")
        stats2 = grass.parse_command("r.univar", map=self.ghs_built_s2_map, flags="g")
        ref_dict1 = {
            "n": "859455000",
            "null_cells": "0",
            "cells": "859455000",
            "min": "1",
            "max": "6",
            "range": "5",
            "mean": "2.0401230198207",
            "mean_of_abs": "2.0401230198207",
            "stddev": "0.627220695511104",
            "variance": "0.393405800877433",
            "coeff_var": "30.7442585284013",
            "sum": "1753393930",
        }
        ref_dict2 = {
            "n": "859454984",
            "null_cells": "16",
            "cells": "859455000",
            "min": "0",
            "max": "99",
            "range": "99",
            "mean": "2.71231884205351",
            "mean_of_abs": "2.71231884205351",
            "stddev": "11.2512767336379",
            "variance": "126.591228136901",
            "coeff_var": "414.821316697393",
            "sum": "2331115947",
        }
        self.assertEqual(
            stats1,
            ref_dict1,
            (
                "The imported raster statistics of {}" "do not match the reference"
            ).format(self.ghs_built_map),
        )
        self.assertEqual(
            stats2,
            ref_dict2,
            (
                "The imported raster statistics of {}" "do not match the reference"
            ).format(self.ghs_built_s2_map),
        )

    def test_ghs_built_s1_import(self):
        """Test if ghs_built_s1 is imported successfully. There is just one
        file to download (2.5 GB) which may take some time"""
        grass.run_command("g.region", raster=self.ref_map_small)
        ghs_built_s1 = SimpleModule("r.import.ghs", ghs_built_s1=self.ghs_built_s1_map)
        self.assertModule(ghs_built_s1)
        self.assertRasterExists(self.ghs_built_s1_map)
        # test that the output has certain statistics
        stats = grass.parse_command("r.univar", map=self.ghs_built_s1_map, flags="g")
        ref_dict = {
            "n": "62265",
            "null_cells": "187059",
            "cells": "249324",
            "min": "1",
            "max": "1",
            "range": "0",
            "mean": "1",
            "mean_of_abs": "1",
            "stddev": "0",
            "variance": "0",
            "coeff_var": "0",
            "sum": "62265",
        }
        self.assertEqual(
            stats,
            ref_dict,
            (
                "The imported raster statistics of {}" "do not match the reference"
            ).format(self.ghs_built_s1_map),
        )


if __name__ == "__main__":
    test()
