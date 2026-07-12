## DESCRIPTION

*r.import.ghs* downloads and imports Global Human Settlement (GHS) data
representing built-up area from the
[JRC-GHS](https://ghsl.jrc.ec.europa.eu/download.php?ds=bu) website.
Data will only be imported for the current computational region. Three
datasets are currently supported for download and import:

- [GHS-BUILT](https://ghsl.jrc.ec.europa.eu/ghs_bu2019.php), built-up
  areas derived from Landsat data, 30m resolution
- [GHS-BUILT-S1](https://jeodpp.jrc.ec.europa.eu/ftp/jrc-opendata/GHSL/GHS_BUILT_S1NODSM_GLOBE_R2018A/GHS_BUILT_S1NODSM_GLOBE_R2018A_3857_20/V1-0/),
  built-up areas derived from Sentinel-1 data, 10m resolution
- [GHS-BUILT-S2](https://ghsl.jrc.ec.europa.eu/ghs_bu_s2_2018.php),
  built-up area probability map derived from Sentinel-2 data, 10m
  resolution

See also the [GHSL Data Package 2019
report](https://ghsl.jrc.ec.europa.eu/documents/GHSL_Data_Package_2019.pdf?t=1478q532234372)
for further information on the datasets.

## REQUIREMENTS

### wget from Python3

```sh
pip3 install wget
```

## EXAMPLES

### Import the GHS-BUILT-S2 dataset for the current computational region:

```sh
r.import.ghs ghs_built_s2=ghs_built_s2_map directory=some_tempdir
```

### Import all datasets for the current computational region:

```sh
r.import.ghs ghs_built=ghs_built_map ghs_built_s1=ghs_built_s1_map ghs_built_s2=ghs_built_s2_map directory=some_tempdir
```

## SEE ALSO

*[r.import](https://grass.osgeo.org/grass-stable/manuals/r.import.html),
[v.select](https://grass.osgeo.org/grass-stable/manuals/v.select.html),
[v.in.region](https://grass.osgeo.org/grass-stable/manuals/v.in.region.html)*

## REFERENCES

- [download source](https://ghsl.jrc.ec.europa.eu/download.php?ds=buS2)
- [GHSL Data Package 2019
  report](https://ghsl.jrc.ec.europa.eu/documents/GHSL_Data_Package_2019.pdf?t=1478q532234372)

## AUTHOR

Guido Riembauer, [mundialis](https://www.mundialis.de/), Germany
