SELECT ST_DISTANCE(
ST_GEOGFROMTEXT('POINT(-74.04447010745835 40.68924450077543)'),
ST_GEOGFROMTEXT('POINT(-0.12418551935155021 51.50086274661804)')
) AS result