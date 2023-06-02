-- This wraps `topology.ST_ChangeEdgeGeom`
-- with a retry-different-tolerance
CREATE OR REPLACE FUNCTION SimplifyEdgeGeom(atopo varchar, anedge int, maxtolerance float8)
RETURNS float8 AS $$
DECLARE
  tol float8;
  sql varchar;
BEGIN
  tol := maxtolerance;
  LOOP
    sql := 'SELECT topology.ST_ChangeEdgeGeom(' || quote_literal(atopo) || ', ' || anedge
      || ', ST_Simplify(geom, ' || tol || ')) FROM '
      || quote_ident(atopo) || '.edge WHERE edge_id = ' || anedge;
    BEGIN
      RAISE DEBUG 'Running %', sql;
      EXECUTE sql;
      RETURN tol;
    EXCEPTION
     WHEN OTHERS THEN
      RAISE WARNING 'Simplification of edge % with tolerance % failed: %', anedge, tol, SQLERRM;
      tol := round( (tol/2.0) * 1e8 ) / 1e8; -- round to get to zero quicker
      IF tol = 0 THEN raise
     --EXCEPTION 
     notice '%', SQLERRM; END IF;
    END;
  END LOOP;
end
$$ LANGUAGE 'plpgsql' STABLE STRICT;

SELECT topology.CreateTopology('topo', 32751);
drop table if exists admin_area_topology;
CREATE TABLE if not exists admin_area_topology(admin_area_pcode int);
-- The layer ID here should be 1
SELECT topology.AddTopoGeometryColumn('topo', 'public', 'admin_area_topology', 'topo', 'POLYGON');

-- This should work if your postgis version is 3.2+

INSERT INTO admin_area_topology (admin_area_pcode, topo)
		select
			admin_area_pcode,
			topology.toTopoGeom(ST_Transform(geom, 32751), 'topo', 1) from timor_locations_suco


-- This is simplification
-- select SUM(SimplifyEdgeGeom('topo', edge_id, 200)) from topo.edge;
-- drop table if exists topology_rainfall_200;
-- create table topology_rainfall_200 as select area_id, rainfall, topo::geometry from admin_area_topology;


-- Replace the rainfallforarea records with the simplified ones
truncate location_profile_rainfallforarea;
insert into location_profile_rainfallforarea (rainfall, geom, area_id)
select rainfall, (ST_DUMP(ST_TRANSFORM(topo, 32751))).geom, area_id from topology_rainfall_200;
-- We no longer need this table
truncate location_profile_rainfall;
-- This zeroes out decimal points. No effect on table size on server, but 
-- reduces size for on-disk representation.
update location_profile_rainfallforarea set geom = ST_QuantizeCoordinates(geom, 3);



-- Clean up

--select topology.DropTopology('topo');